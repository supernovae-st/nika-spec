# SPDX-License-Identifier: Apache-2.0
#
# Deep-static conformance layer · the checks the regex layer cannot make.
#
# The base runner resolves `${{ }}` ROOTS by regex — it never parses the
# expression. `a == b == c` (non-associative violation), `size(x, y)`
# (arity), unbalanced parens and bare-non-boolean `when:` all pass it.
# This layer closes that class deterministically, straight from the
# normative sources ·
#
#   CEL-PARSE     recursive-descent parser of the EXACT v0.1 EBNF
#                 (spec/03-dag.md §Formal grammar · cel-subset/0.1) ·
#                 every `${{ }}` body must parse · `when:` roots must be
#                 boolean-shaped (03-dag §when: MUST be a CEL boolean)
#   JQ-COMPILE    every jq expression (output: bindings · nika:jq
#                 expression · nika:fetch jq arg) must COMPILE · uses the
#                 system `jq` (exit 3 = compile error · runtime errors
#                 accepted) · skipped gracefully when jq is absent
#   DURATION      every static Go-duration string (timeout: · nika:wait
#                 duration/timeout args) must match the spec format
#                 (03-dag §timeout · quoted · positive · ≤24h units)
#   SCHEMA-META   every `schema:` block (infer/agent · nika:validate arg)
#                 must itself be a VALID JSON Schema (Draft 2020-12
#                 check_schema)
#   WHEN-FORM     `when:` must be a `${{ }}` CEL string OR a YAML boolean
#                 (03-dag §when: shape rules) · a bare non-${{ }} string
#                 is silently-never-an-expression · rejected
#   OUTPUT-PURE   `output:` binding values are pure jq · `${{ }}` never
#                 appears inside them (04 §binding rules)
#   BUILTIN-SHAPE nika:write requires `content:` (a write with nothing to
#                 write is an authoring bug) · nika:done is valid only
#                 inside an agent tools whitelist · never a standalone
#                 invoke (02 §loop semantics · NIKA-BUILTIN-DONE-001)
#   PERMITS-FIT   when a permits: block is present, the body must FIT it
#                 (01 §permits · default-deny once present) · statically
#                 checkable surface: invoke tools + agent whitelists vs
#                 permits.tools globs · exec: presence/argv-program vs
#                 permits.exec · static fetch hosts vs permits.net.http
#   ABSENT-PERMITS when the block is ABSENT, DeclaredPermits := ∅
#                 (NEP-0003 · LAW-AUTH-0324) · any statically visible
#                 effect is NIKA-AUTH-006 before any token · pure compute
#                 passes · the null spelling is refused prescriptively ·
#                 computed resources defer to the runtime NIKA-SEC-004
#
# Emitted errors reuse the canonical namespaces (NIKA-VAR for expression
# surface · NIKA-PARSE for shape rules · runner-protocol.md matching).

from __future__ import annotations
import re
import shutil
import subprocess
import sys

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

EXPR_BODY = re.compile(r"(?<!\\)\$\{\{(.*?)\}\}", re.DOTALL)

# The NIKA duration string is STRICTER than Go's ParseDuration (03-dag §timeout
# lines 466-468): positive (> 0) and units combined in strictly DESCENDING
# order without repeats (`1h30m` ✓ · `30m1h` ✗ · `5s5s` ✗). Go accepts `0` and
# any order; the language does not. The JSON Schema `timeout` pattern only
# proves SHAPE (a `${{ }}` template may stand in for a literal), so these
# well-formedness rules are proven HERE — a shape-only regex was a false green
# on `0s` and `30m1h`.
#
# The spec's "Maximum · 24h" is NOT enforced here: it is scoped to task-level
# `timeout:` (its heading + rationale "tasks needing longer should split into a
# workflow chain"), yet this same check also governs `nika:wait` holds — and
# the spec itself uses `48h` as a VALID example one line below the cap (line
# 468). That inconsistency + the task-only scope means a blanket 24h reject
# would false-RED a legitimate 48h release hold. Flagged for the operator to
# resolve in the prose; the oracle stays on the unambiguous rules.
_DUR_SHAPE = re.compile(r"^([0-9]+(\.[0-9]+)?(ns|us|µs|ms|s|m|h))+$")
_DUR_TOKEN = re.compile(r"([0-9]+(?:\.[0-9]+)?)(ns|us|µs|ms|s|m|h)")
_DUR_RANK = {"ns": 0, "us": 1, "µs": 1, "ms": 2, "s": 3, "m": 4, "h": 5}



def iter_tasks(doc):
    """W1 'the map': tasks is an ordered MAP keyed by task id. Returns
    [(tid, task_dict)] pairs - the single accessor every rule reads through."""
    tasks = doc.get("tasks")
    if not isinstance(tasks, dict):
        return []
    return [(k, v) for k, v in tasks.items() if isinstance(v, dict)]


def _valid_duration(v: str) -> bool:
    """A well-formed NIKA duration string: positive, units strictly descending
    without repeats (03-dag §timeout · the well-formedness half of
    NIKA-PARSE-010 · the 24h cap is task-scoped prose, see note above)."""
    if not _DUR_SHAPE.match(v):
        return False
    had_token = False
    last_rank = 99  # each unit's rank must be strictly < the previous (descend)
    for num, unit in _DUR_TOKEN.findall(v):
        rank = _DUR_RANK[unit]
        if rank >= last_rank:  # a repeat or an ascending unit → 30m1h ✗ · 5s5s ✗
            return False
        last_rank = rank
        if float(num) > 0:
            had_token = True
    return had_token  # positive · at least one non-zero component


JQ_BIN = shutil.which("jq")

# ---------------------------------------------------------------- CEL parser
# Tokens per the EBNF terminals (03-dag · cel-subset/0.1).
_TOKEN = re.compile(r"""
    (?P<ws>\s+)
  | (?P<float>-?[0-9]+\.[0-9]+)
  | (?P<int>-?[0-9]+)
  | (?P<string>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")
  | (?P<op>\|\||&&|==|!=|<=|>=|[<>!.\[\](),?:])
  | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
""", re.VERBOSE)

RESERVED = {"true", "false", "null", "in"}


class CelError(Exception):
    pass


def _tokenize(src: str) -> list[tuple[str, str]]:
    out, pos = [], 0
    while pos < len(src):
        m = _TOKEN.match(src, pos)
        if not m:
            raise CelError(f"unexpected character {src[pos]!r} at {pos}")
        pos = m.end()
        kind = m.lastgroup
        if kind != "ws":
            out.append((kind, m.group()))
    out.append(("eof", ""))
    return out


class _Parser:
    """Recursive descent over the normative EBNF · returns the root shape
    ('rel' · 'bool' · 'not' · 'ref' · 'lit' · 'list' · 'call') so callers
    can enforce the when:-boolean side-constraint."""

    def __init__(self, tokens):
        self.toks = tokens
        self.i = 0

    def peek(self):
        return self.toks[self.i]

    def take(self, value=None, kind=None):
        k, v = self.toks[self.i]
        if (value is not None and v != value) or (kind is not None and k != kind):
            raise CelError(f"expected {value or kind} · got {v!r}")
        self.i += 1
        return v

    def parse(self) -> str:
        shape = self.expr()
        if self.peek()[0] != "eof":
            raise CelError(f"trailing input from {self.peek()[1]!r}")
        return shape

    def expr(self):
        return self.ternary()

    def ternary(self):
        shape = self.or_()
        if self.peek()[1] == "?":
            self.take("?")
            self.expr()          # then-branch · any value
            self.take(":")
            self.ternary()       # else-branch · right-associative
            # value-selection · commonly boolean · accepted as a when:-shape
            # (a non-boolean result is caught at runtime · NIKA-VAR-006)
            return "bool"
        return shape

    def or_(self):
        shape = self.and_()
        while self.peek()[1] == "||":
            self.take("||")
            self.and_()
            shape = "bool"
        return shape

    def and_(self):
        shape = self.rel()
        while self.peek()[1] == "&&":
            self.take("&&")
            self.rel()
            shape = "bool"
        return shape

    def rel(self):
        shape = self.unary()
        k, v = self.peek()
        if v in ("==", "!=", "<", "<=", ">", ">=") or (k == "ident" and v == "in"):
            self.take(v)
            self.unary()
            # non-associative · a second relop is a parse error (EBNF rel)
            k2, v2 = self.peek()
            if v2 in ("==", "!=", "<", "<=", ">", ">=") or (k2 == "ident" and v2 == "in"):
                raise CelError("relations do not chain (a == b == c) · parenthesize")
            return "rel"
        return shape

    def unary(self):
        if self.peek()[1] == "!":
            self.take("!")
            self.unary()
            return "not"
        return self.postfix()

    def postfix(self):
        shape = self.primary()
        while True:
            k, v = self.peek()
            if v == ".":
                self.take(".")
                name = self.take(kind="ident")
                if name in RESERVED:
                    raise CelError(f"reserved word {name!r} as member")
                if self.peek()[1] == "(":
                    # method form · size() (0-arg) · contains/startsWith/
                    # endsWith (1-arg string predicates) · cel-subset/0.1
                    self.take("(")
                    if name == "size":
                        self.take(")")
                    elif name in ("contains", "startsWith", "endsWith"):
                        self.expr()
                        if self.peek()[1] == ",":
                            raise CelError(f".{name}() takes exactly 1 argument")
                        self.take(")")
                    else:
                        raise CelError(f"unknown method .{name}() · cel-subset/0.1")
                    shape = "call"
                else:
                    shape = "ref" if shape in ("ref", "call") else shape
            elif v == "[":
                self.take("[")
                self.expr()
                self.take("]")
            else:
                return shape

    def primary(self):
        k, v = self.peek()
        if k in ("int", "float", "string"):
            self.take(kind=k)
            return "lit"
        if v == "(":
            self.take("(")
            shape = self.expr()
            self.take(")")
            return shape
        if v == "[":
            self.take("[")
            if self.peek()[1] != "]":
                self.expr()
                while self.peek()[1] == ",":
                    self.take(",")
                    self.expr()
            self.take("]")
            return "list"
        if k == "ident":
            if v in ("true", "false"):
                self.take(v)
                return "bool"
            if v == "null":
                self.take(v)
                return "lit"
            if v == "in":
                raise CelError("reserved word 'in' as identifier")
            self.take(kind="ident")
            if self.peek()[1] == "(":
                if v not in ("size", "has"):
                    raise CelError(f"the only free calls are size/has · got {v}()")
                self.take("(")
                self.expr()
                if self.peek()[1] == ",":
                    raise CelError(f"{v}() takes exactly 1 argument")
                self.take(")")
                return "call"
            return "ref"
        raise CelError(f"unexpected token {v!r}")


def parse_cel(body: str) -> str:
    """Parse one `${{ }}` body · returns the root shape · raises CelError."""
    return _Parser(_tokenize(body.strip())).parse()


# ---------------------------------------------------------------- walkers
def _walk(value, path=""):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _walk(v, f"{path}[{i}]")
    elif isinstance(value, str):
        yield path, value


def _is_static(s: str) -> bool:
    return not EXPR_BODY.search(s)


def _as_dict(value) -> dict:
    """`value` when it is a dict, else `{}`. The oracle inspects untrusted,
    possibly schema-invalid workflows (it runs BEFORE + regardless of schema
    validation), so `args:`/`exec:` may be a list, string, or int. The old
    `inv.get("args") or {}` idiom crashed on a NON-EMPTY list/string (truthy →
    `.get` on a non-dict → AttributeError), turning a malformed workflow into a
    traceback instead of a verdict — a crash-on-input DoS on the trust root a
    registry runs over untrusted submissions. This makes every `.get` access
    total: a non-dict shape simply carries no fields to check here, and the
    schema layer still reports the type error."""
    return value if isinstance(value, dict) else {}


# ── ABSENT-PERMITS tables (NEP-0003 · LAW-AUTH-0324) ─────────────────────
# One voice with canon/builtins.yaml capability_classification (LAW-AUTH-0311):
# pure/internal builtins carry ZERO required effects — a file invoking only
# them is pure compute and passes under an absent block (law 4).
_PURE_INTERNAL_TOOLS = {
    "nika:assert", "nika:compose", "nika:convert", "nika:date",
    "nika:decide", "nika:done", "nika:emit", "nika:hash", "nika:inspect",
    "nika:jq", "nika:json_diff", "nika:json_merge_patch", "nika:log",
    "nika:prompt", "nika:uuid", "nika:validate", "nika:wait",
}
# The external builtin's effect class is judged on its RESOURCE arg, exactly
# like PERMITS-FIT: a static url/path/program is a check-time refusal
# (NIKA-AUTH-006) · a computed one is the runtime boundary's (NIKA-SEC-004 ·
# law 3 · « the static judge cannot see a host computed at run time »).
_ABSENT_NET_TOOLS = {"nika:fetch", "nika:notify"}
_ABSENT_FS_READ_TOOLS = {"nika:read", "nika:glob", "nika:grep"}
_ABSENT_FS_WRITE_TOOLS = {"nika:write", "nika:edit"}


def _static_str(v) -> str | None:
    return v if isinstance(v, str) and _is_static(v) else None


def _task_required_absent(t: dict) -> set[str]:
    """The effect classes a task STATICALLY requires (NEP-0003 law 1 ·
    Required ⊆ Declared judged with Declared := ∅). Only statically visible
    resources count — a computed host/path/program defers to the runtime
    refusal (law 3). Pure/internal builtins and pure agents require nothing."""
    req: set[str] = set()
    if "exec" in t:
        cmd = _as_dict(t.get("exec")).get("command")
        prog = cmd[0] if isinstance(cmd, list) and cmd else None
        if _static_str(prog) is not None:
            req.add("exec")
    inv = t.get("invoke")
    if isinstance(inv, dict):
        tool = _static_str(inv.get("tool"))
        if tool is not None and tool not in _PURE_INTERNAL_TOOLS:
            args = _as_dict(inv.get("args"))
            if tool in _ABSENT_NET_TOOLS:
                if _static_str(args.get("url")) is not None:
                    req.add("net")
            elif tool in _ABSENT_FS_READ_TOOLS or tool in _ABSENT_FS_WRITE_TOOLS:
                if _static_str(args.get("path")) is not None:
                    req.add("fs")
            else:
                req.add("tools")  # chart · image_* · tts · mcp:* · unknown
    ag = t.get("agent")
    if isinstance(ag, dict):
        for w in ag.get("tools") or []:
            if _static_str(w) is not None and not w.startswith("!") \
                    and w not in _PURE_INTERNAL_TOOLS:
                req.add("tools")
    return req


def _infer_permits_block(tasks: list) -> dict:
    """The minimal permits: block that re-checks clean — the repair the
    NIKA-AUTH-006 detail carries inline (NEP-0003 law 2 · paste-able). The
    tools list names every statically-invoked tool (pure included ·
    PERMITS-FIT default-denies any omitted tool once a block exists)."""
    tools: list[str] = []
    programs: list[str] = []
    hosts: list[str] = []
    reads: list[str] = []
    writes: list[str] = []

    def keep(lst: list, v: str | None) -> None:
        if v is not None and v not in lst:
            lst.append(v)

    for _tid, t in tasks:
        if "exec" in t:
            cmd = _as_dict(t.get("exec")).get("command")
            prog = cmd[0] if isinstance(cmd, list) and cmd else None
            keep(programs, _static_str(prog))
        inv = t.get("invoke")
        if isinstance(inv, dict):
            tool = _static_str(inv.get("tool"))
            if tool is not None:
                keep(tools, tool)
                args = _as_dict(inv.get("args"))
                if tool in _ABSENT_NET_TOOLS:
                    import urllib.parse
                    url = _static_str(args.get("url"))
                    if url is not None:
                        keep(hosts, urllib.parse.urlparse(url).hostname or url)
                elif tool in _ABSENT_FS_READ_TOOLS:
                    keep(reads, _static_str(args.get("path")))
                elif tool in _ABSENT_FS_WRITE_TOOLS:
                    keep(writes, _static_str(args.get("path")))
        ag = t.get("agent")
        if isinstance(ag, dict):
            for w in ag.get("tools") or []:
                if isinstance(w, str) and not w.startswith("!"):
                    keep(tools, _static_str(w))
    block: dict = {}
    if tools:
        block["tools"] = sorted(tools)
    if programs:
        block["exec"] = sorted(programs)
    if hosts:
        block["net"] = {"http": sorted(hosts)}
    fs: dict = {}
    if reads:
        fs["read"] = sorted(reads)
    if writes:
        fs["write"] = sorted(writes)
    if fs:
        block["fs"] = fs
    return block


def _flow_yaml(obj: dict) -> str:
    import yaml
    return yaml.safe_dump(obj, default_flow_style=True, sort_keys=False,
                          width=10 ** 6).strip()


def absent_permits_errors(doc: dict, tasks: list) -> list[dict]:
    """NEP-0003 / LAW-AUTH-0324 · an ABSENT permits: block declares zero
    authority (DeclaredPermits := ∅, provenance: absent). Any non-empty
    static Required is a check refusal NIKA-AUTH-006 before any token
    (laws 1-2 · the detail carries the inferred block, ready to paste).
    The null spelling is refused outright, prescriptively (one obvious
    way). Pure compute (Required := ∅) passes (law 4). A PRESENT block is
    PERMITS-FIT's, below — untouched."""
    if "permits" not in doc:
        inferred = _infer_permits_block(tasks)
        errs: list[dict] = []
        for tid, t in tasks:
            req = _task_required_absent(t)
            if req:
                errs.append({
                    "code": "NIKA-AUTH-006", "namespace": "NIKA-AUTH",
                    "category": "security_error",
                    "detail": f"task '{tid}' requires {', '.join(sorted(req))} "
                              "outside the declared boundary · this file has no "
                              "permits: block · absent means zero authority "
                              "(NEP-0003) · add the inferred boundary (re-checks "
                              f"clean): permits: {_flow_yaml(inferred)}"})
        return errs
    if doc["permits"] is None:
        return [{"code": "NIKA-AUTH-006", "namespace": "NIKA-AUTH",
                 "category": "security_error",
                 "detail": "permits: is null · the null spelling is refused "
                           "(NEP-0003 · one obvious way) · write permits: {} "
                           "for declared-zero authority, or name the boundary "
                           "your effects need"}]
    return []


# ── PERMIT-TAINT tables (NEP-0004 · LAW-AUTH-0325) ──────────────────────
# The fit (PERMITS-FIT below) proves Required ⊆ Declared on CATEGORIES;
# this law binds the VALUES flowing under a present block. Integ=untrusted
# at check: inputs.* (caller-supplied) and config.* (deployment-supplied) —
# the two roots resolvable at check via their declared defaults. Fetch/tool
# results, with:/tasks.* derivations, and every default-less ref DEFER to
# the run-time re-gate (law 4 · NIKA-SEC-004), never a check error.
_TAINT_FS_READ_TOOLS = {"nika:read", "nika:glob", "nika:grep"}
_TAINT_FS_WRITE_TOOLS = {"nika:write", "nika:edit"}
_TAINT_NET_TOOLS = {"nika:fetch", "nika:notify"}
# The exec re-entry class (10 §the permit-parameterization taint): a token
# that re-enters a command interpreter is never covered by a program
# allowlist unless the permit lists the token itself.
_TAINT_REENTRY_TOKENS = {"--exec", "--execdir", "-exec", "-execdir", "-c", "eval"}
_TAINT_UNTRUSTED_ROOTS = ("inputs", "config")


class _DeferRegate(Exception):
    """A reference stays dynamic at check (no default · declassified ·
    trusted root) → NEP-0004 law 4 DEFERs to the run-time re-gate."""


def _taint_declassified(t: dict) -> set[str]:
    """The bindings a task-level declassify: raises to trusted (law 5 · the
    only door). Shape enforcement is the schema's; the oracle reads the
    `from` set tolerantly (a malformed entry is the schema's finding)."""
    out: set[str] = set()
    entries = t.get("declassify")
    if isinstance(entries, list):
        for e in entries:
            if isinstance(e, dict) and isinstance(e.get("from"), str):
                out.add(e["from"])
    return out


def _resolve_untrusted(s: str, inputs: dict, config: dict,
                       declassified: set) -> tuple:
    """Resolve the UNTRUSTED ${{ }} references of a verb-argument string at
    check. Returns (resolved, taint_paths) when ≥1 untrusted ref resolves
    and no reference stays dynamic · (None, []) when nothing untrusted
    appears (a trusted string — the plain fit judges it, never this law)
    or when any reference defers (law 4 · the run-time re-gate is
    mandatory). Substituting only the untrusted defaults keeps the honest
    file green: literal/const/secrets references never reach this law."""
    paths: list[str] = []

    def sub(m) -> str:
        body = m.group(1).strip()
        root, _, rest = body.partition(".")
        name = re.split(r"[.\[]", rest, maxsplit=1)[0] if rest else ""
        if root not in _TAINT_UNTRUSTED_ROOTS or not name:
            raise _DeferRegate  # trusted root (const · secrets) or dynamic
        binding = f"{root}.{name}"
        if binding in declassified:
            raise _DeferRegate  # the declassify: door · trusted here
        decl = (inputs if root == "inputs" else config).get(name)
        default = decl.get("default") if isinstance(decl, dict) else None
        if not isinstance(default, str):
            raise _DeferRegate  # no default → caller-supplied at launch
        paths.append(binding)
        return default

    try:
        resolved = EXPR_BODY.sub(sub, s)
    except _DeferRegate:
        return None, []
    return (resolved, paths) if paths else (None, [])


def _taint_canonical_path(p: str) -> str:
    """The fs canonical form (10 §canonical form) · lexical normalization
    against the run base: `.`/`..` resolved, separators collapsed. A
    leading `..` escapes the base lexically and can never re-enter a
    declared glob — the comparison is the canonical string against the
    glob, never a raw prefix (`datasets/../datasets/q3.csv` IS inside
    `datasets/**`; `../../etc/passwd` is not)."""
    import posixpath
    return posixpath.normpath(p)


def _taint_canonical_host(url: str):
    """The net canonical form · lowercase, IDNA→punycode, trailing dot
    stripped (ports never participate in permits · 01 §permits)."""
    import urllib.parse
    host = urllib.parse.urlparse(url).hostname
    if not host:
        return None
    host = host.lower().rstrip(".")
    try:
        host = host.encode("idna").decode("ascii")
    except (UnicodeError, ValueError):
        pass
    return host


def _taint_globbed(value: str, globs) -> bool:
    """Match against the LITERAL bounds only — an interpolated bound is law
    1's refusal (NIKA-AUTH-007), never something to match against."""
    import fnmatch
    return any(isinstance(g, str) and not EXPR_BODY.search(g)
               and fnmatch.fnmatchcase(value, g) for g in globs or [])


def permit_taint_errors(doc: dict, tasks: list) -> list[dict]:
    """NEP-0004 / LAW-AUTH-0325 · the permit-parameterization taint. Law 1:
    an interpolation reaching a permit BOUND is a hard refusal
    (NIKA-AUTH-007 · the bound MUST be a literal, the boundary would be
    self-serve). Law 2: an untrusted value (inputs.* · config.*) reaching a
    permitted verb's ARGUMENT is re-gated on its canonical RESOLVED form
    against the STEP's permit (NIKA-AUTH-008 · the detail carries the taint
    path source-first, the canonical form, and the escaped bound). Law 4:
    the unresolvable DEFERs to the run-time re-gate (NIKA-SEC-004) — never
    a check error. Runs only under a PRESENT block (absent/null is
    NEP-0003's ground, judged above)."""
    permits = doc.get("permits")
    if not isinstance(permits, dict):
        return []
    errs: list[dict] = []

    # Law 1 · bound literality (the wall is declared, never interpolated)
    for path, s in _walk(permits):
        if EXPR_BODY.search(s):
            errs.append({"code": "NIKA-AUTH-007", "namespace": "NIKA-AUTH",
                         "category": "security_error",
                         "detail": f"permit bound 'permits.{path}' is interpolated, not "
                                   "literal · a bound is the wall itself (NEP-0004 law 1) · "
                                   "declare the host/glob/program and gate the value in the "
                                   "body (the NIKA-AUTH-008 re-gate checks it there)"})

    # Law 2 · the re-gate (canonicalize the RESOLVED value first)
    inputs = _as_dict(doc.get("inputs"))
    config = _as_dict(doc.get("config"))
    fs = permits.get("fs") if isinstance(permits.get("fs"), dict) else {}
    read_globs = fs.get("read") if isinstance(fs.get("read"), list) else []
    write_globs = fs.get("write") if isinstance(fs.get("write"), list) else []
    net = permits.get("net") if isinstance(permits.get("net"), dict) else {}
    host_globs = net.get("http") if isinstance(net.get("http"), list) else []
    exec_rule = permits.get("exec", False)

    def regate(tid, paths, argname, resolved, canonical, covered, bound_desc):
        if covered:
            return
        errs.append({"code": "NIKA-AUTH-008", "namespace": "NIKA-AUTH",
                     "category": "security_error",
                     "detail": f"task '{tid}' passes an untrusted value that escapes the "
                               f"step permit (NEP-0004 law 2) · taint path: "
                               f"{' , '.join(paths)} -> {argname} · resolved (default): "
                               f"{resolved!r} -> canonical {canonical!r} ∉ {bound_desc} · "
                               "fix: keep the value inside the boundary · or declare "
                               "declassify: on the task (the only door)"})

    for tid, t in tasks:
        declassified = _taint_declassified(t)
        inv = t.get("invoke")
        if isinstance(inv, dict):
            tool = inv.get("tool")
            args = _as_dict(inv.get("args"))
            if tool in _TAINT_FS_READ_TOOLS or tool in _TAINT_FS_WRITE_TOOLS:
                is_read = tool in _TAINT_FS_READ_TOOLS
                globs = read_globs if is_read else write_globs
                v = args.get("path")
                if isinstance(v, str) and EXPR_BODY.search(v):
                    resolved, paths = _resolve_untrusted(v, inputs, config, declassified)
                    if resolved is not None:
                        canon = _taint_canonical_path(resolved)
                        regate(tid, paths, f"args.path ({tool})", resolved, canon,
                               _taint_globbed(canon, globs),
                               f"fs.{'read' if is_read else 'write'} {globs}")
            elif tool in _TAINT_NET_TOOLS:
                v = args.get("url")
                if isinstance(v, str) and EXPR_BODY.search(v):
                    resolved, paths = _resolve_untrusted(v, inputs, config, declassified)
                    if resolved is not None:
                        host = _taint_canonical_host(resolved)
                        if host is not None:
                            regate(tid, paths, f"args.url ({tool})", resolved, host,
                                   _taint_globbed(host, host_globs),
                                   f"net.http {host_globs}")
        if "exec" in t and isinstance(exec_rule, list):
            body = t.get("exec")
            cmd = body.get("command") if isinstance(body, dict) else None
            if isinstance(cmd, list):
                for i, el in enumerate(cmd):
                    if not isinstance(el, str) or not EXPR_BODY.search(el):
                        continue
                    resolved, paths = _resolve_untrusted(el, inputs, config, declassified)
                    if resolved is None:
                        continue
                    if i == 0:
                        # the program itself is data → re-gate against the allowlist
                        regate(tid, paths, "argv[0] (exec)", resolved, resolved,
                               resolved in exec_rule, f"exec {exec_rule}")
                    elif resolved in _TAINT_REENTRY_TOKENS and resolved not in exec_rule:
                        errs.append({"code": "NIKA-AUTH-008", "namespace": "NIKA-AUTH",
                                     "category": "security_error",
                                     "detail": f"task '{tid}' passes an untrusted value that "
                                               f"escapes the step permit (NEP-0004 law 2) · "
                                               f"taint path: {' , '.join(paths)} -> argv[{i}] (exec) "
                                               f"· resolved (default): {resolved!r} is the re-entry "
                                               f"class, never covered unless listed ∉ exec "
                                               f"{exec_rule} · fix: drop the token · or declare "
                                               "declassify: on the task (the only door)"})
    return errs


# NEP-0005 / LAW-AUTH-0326 · the environment permit. The dangerous-name
# floor an engine strips unconditionally · the reference mirrors the
# engine's canonical `DANGEROUS_ENV_VARS` list (nika-kernel-core
# io/process.rs · 31 names, mechanically extracted at the F-O4 lane) ·
# the engine/reference differential (LAW-AUTH-0319) keeps the two lists
# honest. Bound literality for `env:` entries (law 4 · NIKA-AUTH-007)
# rides the generic permit-bound walk in permit_taint_errors.
_ENV_DANGEROUS_NAMES = frozenset({
    "LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT", "GCONV_PATH",
    "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH",
    "DYLD_FALLBACK_LIBRARY_PATH", "DYLD_FALLBACK_FRAMEWORK_PATH",
    "BASH_ENV", "ENV", "GIT_SSH_COMMAND", "GIT_SSH", "GIT_EXTERNAL_DIFF",
    "GIT_PAGER", "GIT_PROXY_COMMAND", "GIT_CONFIG_GLOBAL",
    "GIT_CONFIG_SYSTEM", "GIT_TEMPLATE_DIR", "LESSOPEN", "HOSTALIASES",
    "TERMINFO", "TERMINFO_DIRS", "TERMCAP", "PYTHONSTARTUP", "PYTHONPATH",
    "PERL5OPT", "PERL5LIB", "RUBYOPT", "NODE_OPTIONS", "IFS",
})


def env_dead_grant_errors(doc: dict) -> list[dict]:
    """NEP-0005 / LAW-AUTH-0326 law 3 · a permits env: entry naming a
    dangerous-floor variable is an inert dead grant (the engine strips
    the name unconditionally, the grant can never take effect) ·
    NIKA-AUTH-009 at check. An interpolated entry is law 4's ground
    (NIKA-AUTH-007 · the generic bound walk), never judged here."""
    permits = doc.get("permits")
    if not isinstance(permits, dict):
        return []
    entries = permits.get("env")
    if not isinstance(entries, list):
        return []
    errs: list[dict] = []
    for i, name in enumerate(entries):
        if isinstance(name, str) and name in _ENV_DANGEROUS_NAMES:
            errs.append({"code": "NIKA-AUTH-009", "namespace": "NIKA-AUTH",
                         "category": "security_error",
                         "detail": f"permit entry 'permits.env[{i}]' names the "
                                   f"dangerous-floor variable {name!r} · the engine strips "
                                   "this name unconditionally, the grant can never take "
                                   "effect (an inert dead grant · NEP-0005 law 3) · remove "
                                   "the entry: pass authored data through the task env: map, "
                                   "or a non-dangerous engine variable by its exact name"})
    return errs


# NEP-0006 / LAW-AUTH-0327 · the data-as-code sink. The v1 code-bearing
# classes are CLOSED and normative (the exact list ships in the NEP · only
# a NEP amends it) · the reference mirrors the engine's list and the
# per-class fixtures keep the two honest (LAW-AUTH-0319 differential).
_CODE_BEARING_CLASSES = {
    "serialized-executable": {
        ".pkl", ".pickle", ".dill", ".joblib", ".pt", ".pth", ".ckpt",
    },
    "script/interpreter": {
        ".py", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".rb",
        ".pl", ".php", ".js", ".mjs", ".ipynb",
    },
    "executable binary/module": {
        ".exe", ".dll", ".so", ".dylib", ".wasm", ".jar",
    },
}


def _code_bearing_class(url: str):
    """The (class, extension) of a code-bearing URL path, or None. The
    classification reads the PATH only (query/fragment carry no verdict ·
    NEP-0006 law 4), case-insensitively on the final extension."""
    import urllib.parse
    import posixpath
    path = urllib.parse.urlparse(url).path
    ext = posixpath.splitext(path)[1].lower()
    if not ext:
        return None
    for cls, exts in _CODE_BEARING_CLASSES.items():
        if ext in exts:
            return cls, ext
    return None


def _resolve_static_url(v: str, doc: dict):
    """Resolve a fetch url at check when every island is const.* or an
    inputs.*/config.* entry carrying a declared default (the NEP-0004
    resolution rules extended to the trusted const root · the SINK law
    classifies the artifact, trust is not the question here). Returns the
    resolved string, or None when any island stays dynamic (law 3 · the
    run twin owns it)."""
    if "${{" not in v:
        return v
    inputs = _as_dict(doc.get("inputs"))
    config = _as_dict(doc.get("config"))
    consts = _as_dict(doc.get("const"))

    class _Dyn(Exception):
        pass

    def sub(m) -> str:
        body = m.group(1).strip()
        root, _, rest = body.partition(".")
        name = re.split(r"[.\[]", rest, maxsplit=1)[0] if rest else ""
        if not name:
            raise _Dyn
        if root == "const":
            decl = consts.get(name)
            if isinstance(decl, str):
                return decl
            if isinstance(decl, dict) and isinstance(decl.get("value"), str):
                return decl["value"]
            raise _Dyn
        if root in ("inputs", "config"):
            decl = (inputs if root == "inputs" else config).get(name)
            default = decl.get("default") if isinstance(decl, dict) else None
            if isinstance(default, str):
                return default
            raise _Dyn
        raise _Dyn

    try:
        return EXPR_BODY.sub(sub, v)
    except _Dyn:
        return None


def data_as_code_errors(doc: dict, tasks: list) -> list[dict]:
    """NEP-0006 / LAW-AUTH-0327 · a nika:fetch whose resolved URL path
    names a code-bearing class is refused (NIKA-SEC-008) unless the task
    declares the inert: door (non-empty · the shape gate is the schema's).
    The unresolvable defers to the run twin (NIKA-SEC-004 · law 3)."""
    errs: list[dict] = []
    for tid, t in tasks:
        inv = t.get("invoke")
        if not isinstance(inv, dict) or inv.get("tool") != "nika:fetch":
            continue
        door = t.get("inert")
        if isinstance(door, str) and door:
            continue  # the declared door · law 2 (empty = the schema's refusal)
        args = _as_dict(inv.get("args"))
        v = args.get("url")
        if not isinstance(v, str):
            continue
        resolved = _resolve_static_url(v, doc)
        if resolved is None:
            continue  # dynamic · the run twin owns it (law 3)
        hit = _code_bearing_class(resolved)
        if hit is None:
            continue
        cls, ext = hit
        errs.append({"code": "NIKA-SEC-008", "namespace": "NIKA-SEC",
                     "category": "security_error",
                     "detail": f"task '{tid}' fetches a code-bearing artifact ({cls} class "
                               f"· `{ext}`) · {resolved} is a program, not data: the read "
                               "hides an execution sink (NEP-0006 law 1) · fix: model the "
                               "acquisition as the exec it feeds (exec: + a program permit) "
                               "· or declare the read inert on the task (inert: \"<because>\")"})
    return errs


def deep_static_errors(doc: dict) -> list[dict]:
    errs: list[dict] = []
    if not isinstance(doc, dict):
        return errs
    tasks = iter_tasks(doc)

    # CEL-PARSE · every expression body everywhere · boolean shape on when:
    for path, s in _walk(doc):
        for m in EXPR_BODY.finditer(s):
            body = m.group(1)
            try:
                shape = parse_cel(body)
            except CelError as e:
                errs.append({"namespace": "NIKA-VAR", "category": "validation_error",
                             "detail": f"{path} · CEL parse error · {e} · in {body.strip()[:60]!r}"})
                continue
            leaf = path.rsplit(".", 1)[-1]
            if leaf == "when" and shape not in ("rel", "bool", "not", "call"):
                # 03-dag §when: MUST be boolean · bare refs/literals rejected
                errs.append({"namespace": "NIKA-VAR", "category": "validation_error",
                             "detail": f"{path} · when: must be boolean-shaped CEL "
                                       f"(comparison · && · || · !) · bare {shape} rejected"})

    # JQ-COMPILE · output: bindings + nika:jq expression + nika:fetch jq arg
    jq_exprs: list[tuple[str, str]] = []
    for tid, t in tasks:
        out = t.get("output")
        if isinstance(out, dict):
            for name, expr in out.items():
                if isinstance(expr, str) and _is_static(expr):
                    jq_exprs.append((f"task '{tid}' output.{name}", expr))
        inv = t.get("invoke")
        if isinstance(inv, dict):
            args = _as_dict(inv.get("args"))
            if inv.get("tool") == "nika:jq" and isinstance(args.get("expression"), str) \
                    and _is_static(args["expression"]):
                jq_exprs.append((f"task '{tid}' nika:jq", args["expression"]))
            if inv.get("tool") == "nika:fetch" and isinstance(args.get("jq"), str) \
                    and _is_static(args["jq"]):
                jq_exprs.append((f"task '{tid}' fetch.jq", args["jq"]))
    if JQ_BIN:
        for where, expr in jq_exprs:
            # `--` ends jq's option parsing so a leading-dash "expression" is
            # the PROGRAM, not a flag: bare `jq '-n'` is silently `--null-input`
            # and a non-compiling expression slipped through as a valid flag
            # (verified). `timeout=` bounds a workflow-supplied program that
            # compiles then runs forever (`repeat(.)` would hang the trust
            # root's CI); a timeout means it got PAST compilation, so it is
            # NOT a compile error and is left accepted (same as runtime errs).
            try:
                r = subprocess.run([JQ_BIN, "--", expr], input="null",
                                   capture_output=True, text=True, timeout=5)
            except subprocess.TimeoutExpired:
                continue
            if r.returncode == 3:  # compile error · runtime errors (5) accepted
                msg = (r.stderr.strip().splitlines() or ["jq compile error"])[0]
                errs.append({"namespace": "NIKA-VAR", "category": "validation_error",
                             "detail": f"{where} · jq does not compile · {msg[:90]}"})
    elif jq_exprs:
        # jq absent, but the workflow carries jq to prove. A silent skip is an
        # environment-dependent false green — surface it so a mis-provisioned
        # CI is visible (the spec CI installs jq before running the oracle).
        print(f"warning: jq not on PATH — {len(jq_exprs)} jq expression(s) left "
              "UNVERIFIED (install jq to close this gap)", file=sys.stderr)

    # DURATION · task timeout · nika:wait duration/timeout
    def check_duration(where: str, v):
        if not isinstance(v, str) or not _is_static(v):
            return
        if not _valid_duration(v):
            errs.append({"namespace": "NIKA-PARSE", "category": "validation_error",
                         "detail": f"{where} · invalid Go-duration {v!r} · must be "
                                   "positive · units descending "
                                   "(03-dag §timeout · e.g. \"30s\" · \"1h30m\")"})

    for tid, t in tasks:
        check_duration(f"task '{tid}' timeout", t.get("timeout"))
        inv = t.get("invoke")
        if isinstance(inv, dict) and inv.get("tool") == "nika:wait":
            args = _as_dict(inv.get("args"))
            check_duration(f"task '{tid}' wait.duration", args.get("duration"))
            check_duration(f"task '{tid}' wait.timeout", args.get("timeout"))
        for step in (t.get("on_finally") or []):
            if isinstance(step, dict):
                check_duration(f"task '{tid}' on_finally.timeout", step.get("timeout"))

    # SCHEMA-META · every schema: must itself be a valid JSON Schema
    def check_schema(where: str, schema):
        if not isinstance(schema, dict):
            return
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as e:
            errs.append({"namespace": "NIKA-PARSE", "category": "validation_error",
                         "detail": f"{where} · schema: is not a valid JSON Schema · "
                                   f"{e.message[:90]}"})

    for tid, t in tasks:
        for verb in ("infer", "agent"):
            body = t.get(verb)
            if isinstance(body, dict):
                check_schema(f"task '{tid}' {verb}.schema", body.get("schema"))
        inv = t.get("invoke")
        if isinstance(inv, dict) and inv.get("tool") == "nika:validate":
            check_schema(f"task '{tid}' validate.schema", _as_dict(inv.get("args")).get("schema"))

    # WHEN-FORM · ${{ }} string or YAML boolean · a bare string is never an expression
    def check_when(where: str, w):
        if w is None or isinstance(w, bool):
            return
        if isinstance(w, str) and not EXPR_BODY.search(w):
            errs.append({"namespace": "NIKA-VAR", "category": "validation_error",
                         "detail": f"{where} · when: must be a ${{{{ }}}} CEL expression "
                                   f"or the YAML boolean true/false · bare string {w[:40]!r} "
                                   "is never evaluated (03-dag §when: shape rules)"})

    for tid, t in tasks:
        check_when(f"task '{tid}'", t.get("when"))
        for i, step in enumerate(t.get("on_finally") or []):
            if isinstance(step, dict):
                check_when(f"task '{tid}' on_finally[{i}]", step.get("when"))

    # OUTPUT-PURE · binding values are pure jq over the task's own raw output
    for tid, t in tasks:
        out = t.get("output")
        if isinstance(out, dict):
            for name, expr in out.items():
                if isinstance(expr, str) and EXPR_BODY.search(expr):
                    errs.append({"namespace": "NIKA-VAR", "category": "validation_error",
                                 "detail": f"task '{tid}' output.{name} · ${{{{ }}}} never "
                                           "appears inside an output: binding · bindings are "
                                           "pure jq over the task's own raw output · shape the "
                                           "verb's INPUT with ${{ }} instead (04 §binding rules)"})

    # BUILTIN-SHAPE · jq arg is `expression` · wait is duration XOR until
    for tid, t in tasks:
        inv = t.get("invoke")
        if not isinstance(inv, dict):
            continue
        args = inv.get("args")
        if inv.get("tool") == "nika:jq" and isinstance(args, dict):
            if "expression" not in args:
                wrong = next((k for k in ("query", "expr", "program", "filter") if k in args), None)
                hint = f" (found '{wrong}' — the arg is 'expression')" if wrong else ""
                errs.append({"namespace": "NIKA-BUILTIN", "category": "validation_error",
                             "detail": f"task '{tid}' · nika:jq requires expression:{hint} "
                                       "(builtins-v0.1.md · one name everywhere)"})
        if inv.get("tool") == "nika:wait" and isinstance(args, dict):
            has_d, has_u = "duration" in args, "until" in args
            if has_d == has_u:  # both or neither
                errs.append({"namespace": "NIKA-BUILTIN", "category": "validation_error",
                             "detail": f"task '{tid}' · nika:wait takes duration: XOR until: "
                                       "(exactly one · builtins-v0.1.md)"})

    # BUILTIN-SHAPE · write needs content · done never stands alone
    for tid, t in tasks:
        inv = t.get("invoke")
        if not isinstance(inv, dict):
            continue
        tool = inv.get("tool")
        args = inv.get("args")
        if tool == "nika:write" and isinstance(args, dict) and "content" not in args:
            errs.append({"namespace": "NIKA-BUILTIN", "category": "validation_error",
                         "detail": f"task '{tid}' · nika:write requires a content: arg "
                                   "(a write with nothing to write · builtins-v0.1.md)"})
        if tool == "nika:done":
            errs.append({"code": "NIKA-BUILTIN-DONE-001", "namespace": "NIKA-BUILTIN",
                         "category": "validation_error",
                         "detail": f"task '{tid}' · nika:done is the agent-loop completion "
                                   "sentinel · valid ONLY inside an agent: tools whitelist · "
                                   "never a standalone invoke (02 §loop semantics)"})

    # ABSENT-PERMITS · NEP-0003 (LAW-AUTH-0324) · absent block = zero
    # authority · judged BEFORE the fit (a present block is PERMITS-FIT's)
    errs.extend(absent_permits_errors(doc, tasks))

    # PERMIT-TAINT · NEP-0004 (LAW-AUTH-0325) · bound literality + the
    # untrusted-argument re-gate under a PRESENT block
    errs.extend(permit_taint_errors(doc, tasks))

    # ENV-DEAD-GRANT · NEP-0005 (LAW-AUTH-0326) · a dangerous-floor name
    # in permits.env: is an inert dead grant (NIKA-AUTH-009)
    errs.extend(env_dead_grant_errors(doc))

    # DATA-AS-CODE · NEP-0006 (LAW-AUTH-0327) · a code-bearing fetch is
    # refused unless the task declares the inert: door (NIKA-SEC-008)
    errs.extend(data_as_code_errors(doc, tasks))

    # PERMITS-FIT · the declared boundary must contain the body (01 §permits)
    permits = doc.get("permits")
    if isinstance(permits, dict):
        import fnmatch
        import urllib.parse

        def tool_permitted(tool: str) -> bool:
            pats = permits.get("tools")
            if not isinstance(pats, list):
                return False  # tools omitted → no invoke at all
            strs = [p for p in pats if isinstance(p, str)]
            # Negation (`!prefix`) is a spec feature (02-verbs §permits · e.g.
            # `["mcp:browser/*", "!mcp:browser/navigate"]`): a tool is permitted
            # iff it matches an allow pattern AND matches no `!`-deny pattern.
            # The deny was previously filtered out and never applied — an
            # author's explicit `!nika:write` was silently ignored (false green).
            allowed = any(fnmatch.fnmatchcase(tool, p) for p in strs if not p.startswith("!"))
            denied = any(fnmatch.fnmatchcase(tool, p[1:]) for p in strs if p.startswith("!"))
            return allowed and not denied

        exec_rule = permits.get("exec", False)
        net = permits.get("net") if isinstance(permits.get("net"), dict) else {}
        hosts = net.get("http") if isinstance(net.get("http"), list) else None

        for tid, t in tasks:
            if "exec" in t:
                body = t.get("exec") or {}
                cmd = body.get("command") if isinstance(body, dict) else None
                if exec_rule is False or exec_rule is None:
                    errs.append({"code": "NIKA-SEC-004", "namespace": "NIKA-SEC",
                                 "category": "security_error",
                                 "detail": f"task '{tid}' · exec: but permits.exec is "
                                           "false/omitted (01 §permits · default-deny)"})
                elif isinstance(exec_rule, list) and isinstance(cmd, list) and cmd \
                        and isinstance(cmd[0], str) and not EXPR_BODY.search(cmd[0]) \
                        and cmd[0] not in exec_rule:
                    errs.append({"code": "NIKA-SEC-004", "namespace": "NIKA-SEC",
                                 "category": "security_error",
                                 "detail": f"task '{tid}' · argv program '{cmd[0]}' not in "
                                           f"permits.exec allowlist {exec_rule}"})
            inv = t.get("invoke")
            if isinstance(inv, dict):
                tool = inv.get("tool")
                if isinstance(tool, str) and not EXPR_BODY.search(tool) \
                        and not tool_permitted(tool):
                    errs.append({"code": "NIKA-SEC-004", "namespace": "NIKA-SEC",
                                 "category": "security_error",
                                 "detail": f"task '{tid}' · invoke {tool} outside "
                                           "permits.tools (01 §permits)"})
                if tool == "nika:fetch" and hosts is not None:
                    url = _as_dict(inv.get("args")).get("url")
                    if isinstance(url, str) and not EXPR_BODY.search(url):
                        host = urllib.parse.urlparse(url).hostname or ""
                        if not any(fnmatch.fnmatchcase(host, h) for h in hosts
                                   if isinstance(h, str)):
                            errs.append({"code": "NIKA-SEC-004", "namespace": "NIKA-SEC",
                                         "category": "security_error",
                                         "detail": f"task '{tid}' · fetch host '{host}' not in "
                                                   "permits.net.http allowlist"})
            ag = t.get("agent")
            if isinstance(ag, dict):
                for w in (ag.get("tools") or []):
                    if isinstance(w, str) and not w.startswith("!") \
                            and not tool_permitted(w):
                        errs.append({"code": "NIKA-SEC-004", "namespace": "NIKA-SEC",
                                     "category": "security_error",
                                     "detail": f"task '{tid}' · agent whitelist '{w}' outside "
                                               "permits.tools (the agent cannot exceed the file)"})

    return errs

# ── POLICY · the hard families judged on the graph (spec 10-authority) ──

# The effect-class table for policy rules — the COARSE projection of the
# builtin classification (10 §the effect vocabulary · one voice with the
# engine's builtin_effect table · fs split at its grain of harm: write).
_POLICY_NET_TOOLS = {"nika:fetch", "nika:notify"}
_POLICY_WRITE_TOOLS = {"nika:write", "nika:edit"}
_HUMAN_GATE_TOOL = "nika:prompt"


def _task_tool(t: dict) -> str | None:
    inv = t.get("invoke")
    if isinstance(inv, dict) and isinstance(inv.get("tool"), str):
        return inv["tool"]
    return None


def _task_effect_classes(t: dict) -> set[str]:
    """The policy effect classes a task carries (exec · write · net · tools)."""
    out: set[str] = set()
    if "exec" in t:
        out.add("exec")
    tool = _task_tool(t)
    if tool is not None:
        out.add("tools")
        if tool in _POLICY_NET_TOOLS:
            out.add("net")
        if tool in _POLICY_WRITE_TOOLS:
            out.add("write")
    return out


def _policy_graph(tasks: list) -> dict[str, set[str]]:
    """tid → direct ancestor tids (E_d via with: refs ∪ E_c via after: keys) —
    the same derived graph every judge reads (03 · with/after are the two
    doors · a boundary-crossing ref outside them is NIKA-VAR-021 upstream)."""
    import json as _json
    ids = {tid for tid, _ in tasks}
    up: dict[str, set[str]] = {tid: set() for tid, _ in tasks}
    for tid, t in tasks:
        refs: set[str] = set()
        w = t.get("with")
        if w is not None:
            for body in EXPR_BODY.findall(_json.dumps(w)):
                for m in re.finditer(r"tasks\.([a-z][a-z0-9_]*)", body):
                    refs.add(m.group(1))
        after = t.get("after")
        if isinstance(after, dict):
            refs.update(k for k in after if isinstance(k, str))
        up[tid] = refs & ids
    return up


def _ancestors(up: dict[str, set[str]], tid: str) -> set[str]:
    seen: set[str] = set()
    stack = list(up.get(tid, ()))
    while stack:
        a = stack.pop()
        if a in seen:
            continue
        seen.add(a)
        stack.extend(up.get(a, ()))
    return seen


def policy_errors(doc: dict) -> list[dict]:
    """The hard policy: families (spec 10) · require.human_gate_before ·
    forbid.exec_after · allow.providers · limits.max_tasks. Soft families
    (prefer/optimize) are recorded, never judged — no rule here reads them."""
    pol = doc.get("policy")
    if not isinstance(pol, dict):
        return []
    errs: list[dict] = []
    tasks = iter_tasks(doc)
    up = _policy_graph(tasks)
    classes = {tid: _task_effect_classes(t) for tid, t in tasks}

    def violation(detail: str) -> None:
        errs.append({"code": "NIKA-POLICY-001", "namespace": "NIKA-POLICY",
                     "category": "security_error", "detail": detail})

    require = pol.get("require") if isinstance(pol.get("require"), dict) else {}
    gated = require.get("human_gate_before")
    if isinstance(gated, list):
        gate_ids = {tid for tid, t in tasks if _task_tool(t) == _HUMAN_GATE_TOOL}
        for tid, _t in tasks:
            hit = classes[tid] & set(gated)
            if hit and not (_ancestors(up, tid) & gate_ids):
                violation(f"task '{tid}' · require.human_gate_before: "
                          f"{sorted(hit)} — no {_HUMAN_GATE_TOOL} ancestor "
                          "(the pause IS the consent · 10 §policy)")

    forbid = pol.get("forbid") if isinstance(pol.get("forbid"), dict) else {}
    upstream_classes = forbid.get("exec_after")
    if isinstance(upstream_classes, list):
        wanted = set(upstream_classes)
        for tid, _t in tasks:
            if "exec" not in classes[tid]:
                continue
            tainted = [a for a in _ancestors(up, tid) if classes[a] & wanted]
            if tainted:
                path = " → ".join(sorted(tainted)) + f" → {tid}"
                violation(f"task '{tid}' · forbid.exec_after: "
                          f"{sorted(wanted)} — the path is the witness: {path} "
                          "(order law · 10 §policy)")

    allow = pol.get("allow") if isinstance(pol.get("allow"), dict) else {}
    providers = allow.get("providers")
    if isinstance(providers, list):
        root_model = doc.get("model") if isinstance(doc.get("model"), str) else None
        for tid, t in tasks:
            body = t.get("infer") if isinstance(t.get("infer"), dict) else                 t.get("agent") if isinstance(t.get("agent"), dict) else None
            if body is None:
                continue
            model = body.get("model") if isinstance(body.get("model"), str)                 else root_model
            if model is None or EXPR_BODY.search(model):
                violation(f"task '{tid}' · allow.providers — the provider is "
                          "not statically determinable (templated or absent "
                          "model:) · fail-closed: pin the literal (10 §policy)")
                continue
            provider = model.split("/", 1)[0]
            if provider not in providers:
                violation(f"task '{tid}' · allow.providers — '{provider}' is "
                          f"not in {providers} (10 §policy)")

    limits = pol.get("limits") if isinstance(pol.get("limits"), dict) else {}
    max_tasks = limits.get("max_tasks")
    if isinstance(max_tasks, int) and not isinstance(max_tasks, bool)             and len(tasks) > max_tasks:
        violation(f"limits.max_tasks: {max_tasks} — the workflow declares "
                  f"{len(tasks)} tasks (10 §policy)")

    return errs
