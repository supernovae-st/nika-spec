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
#
# Emitted errors reuse the canonical namespaces (NIKA-VAR for expression
# surface · NIKA-PARSE for shape rules · runner-protocol.md matching).

from __future__ import annotations
import re
import shutil
import subprocess

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

EXPR_BODY = re.compile(r"(?<!\\)\$\{\{(.*?)\}\}", re.DOTALL)
DURATION_RE = re.compile(r"^([0-9]+(\.[0-9]+)?(ns|us|µs|ms|s|m|h))+$")
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


def deep_static_errors(doc: dict) -> list[dict]:
    errs: list[dict] = []
    if not isinstance(doc, dict):
        return errs
    tasks = doc.get("tasks") or []
    if not isinstance(tasks, list):
        return errs

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
    for t in tasks:
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
        out = t.get("output")
        if isinstance(out, dict):
            for name, expr in out.items():
                if isinstance(expr, str) and _is_static(expr):
                    jq_exprs.append((f"task '{tid}' output.{name}", expr))
        inv = t.get("invoke")
        if isinstance(inv, dict):
            args = inv.get("args") or {}
            if inv.get("tool") == "nika:jq" and isinstance(args.get("expression"), str) \
                    and _is_static(args["expression"]):
                jq_exprs.append((f"task '{tid}' nika:jq", args["expression"]))
            if inv.get("tool") == "nika:fetch" and isinstance(args.get("jq"), str) \
                    and _is_static(args["jq"]):
                jq_exprs.append((f"task '{tid}' fetch.jq", args["jq"]))
    if JQ_BIN:
        for where, expr in jq_exprs:
            r = subprocess.run([JQ_BIN, expr], input="null", capture_output=True, text=True)
            if r.returncode == 3:  # compile error · runtime errors (5) accepted
                msg = (r.stderr.strip().splitlines() or ["jq compile error"])[0]
                errs.append({"namespace": "NIKA-VAR", "category": "validation_error",
                             "detail": f"{where} · jq does not compile · {msg[:90]}"})

    # DURATION · task timeout · nika:wait duration/timeout
    def check_duration(where: str, v):
        if not isinstance(v, str) or not _is_static(v):
            return
        if not DURATION_RE.match(v):
            errs.append({"namespace": "NIKA-PARSE", "category": "validation_error",
                         "detail": f"{where} · invalid Go-duration {v!r} "
                                   "(03-dag §timeout · e.g. \"30s\" · \"1h30m\")"})

    for t in tasks:
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
        check_duration(f"task '{tid}' timeout", t.get("timeout"))
        inv = t.get("invoke")
        if isinstance(inv, dict) and inv.get("tool") == "nika:wait":
            args = inv.get("args") or {}
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

    for t in tasks:
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
        for verb in ("infer", "agent"):
            body = t.get(verb)
            if isinstance(body, dict):
                check_schema(f"task '{tid}' {verb}.schema", body.get("schema"))
        inv = t.get("invoke")
        if isinstance(inv, dict) and inv.get("tool") == "nika:validate":
            check_schema(f"task '{tid}' validate.schema", (inv.get("args") or {}).get("schema"))

    # WHEN-FORM · ${{ }} string or YAML boolean · a bare string is never an expression
    def check_when(where: str, w):
        if w is None or isinstance(w, bool):
            return
        if isinstance(w, str) and not EXPR_BODY.search(w):
            errs.append({"namespace": "NIKA-VAR", "category": "validation_error",
                         "detail": f"{where} · when: must be a ${{{{ }}}} CEL expression "
                                   f"or the YAML boolean true/false · bare string {w[:40]!r} "
                                   "is never evaluated (03-dag §when: shape rules)"})

    for t in tasks:
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
        check_when(f"task '{tid}'", t.get("when"))
        for i, step in enumerate(t.get("on_finally") or []):
            if isinstance(step, dict):
                check_when(f"task '{tid}' on_finally[{i}]", step.get("when"))

    # OUTPUT-PURE · binding values are pure jq over the task's own raw output
    for t in tasks:
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
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
    for t in tasks:
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
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
    for t in tasks:
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
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

    # PERMITS-FIT · the declared boundary must contain the body (01 §permits)
    permits = doc.get("permits")
    if isinstance(permits, dict):
        import fnmatch
        import urllib.parse

        def tool_permitted(tool: str) -> bool:
            pats = permits.get("tools")
            if not isinstance(pats, list):
                return False  # tools omitted → no invoke at all
            return any(fnmatch.fnmatchcase(tool, pat) for pat in pats
                       if isinstance(pat, str) and not pat.startswith("!"))

        exec_rule = permits.get("exec", False)
        net = permits.get("net") if isinstance(permits.get("net"), dict) else {}
        hosts = net.get("http") if isinstance(net.get("http"), list) else None

        for t in tasks:
            if not isinstance(t, dict):
                continue
            tid = t.get("id")
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
                    url = (inv.get("args") or {}).get("url")
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
