# SPDX-License-Identifier: Apache-2.0
"""NEP-0002 · the lethal-trifecta lane (`NIKA-SEC-009`) — the reference judge.

Three legs, read off the DECLARED boundary and the task graph
(NEP-0002 §Specification · v2.0 realized-flow):

- ① private-data · `permits.fs.read` is non-empty.
- ② untrusted ingress · the `tools:` grant admits an ingress-capable tool
  (`nika:fetch` covered by a glob · any `mcp:*` server) AND the graph
  REALIZES a source: a fetch invoked · an `mcp:*` invoked (server content
  is untrusted by construction · fail-closed) · an `agent:` whose
  whitelist admits ingress. Content propagates through `with:` bindings,
  `for_each` items, `tasks.*.output` reads and `on_error.recover` reads;
  `infer:`/`agent:` outputs CARRY it when their prompt sees it (the
  integrity direction — the verbatim-echo carve-out is confidentiality-
  only and does not apply); an `exec:` is tainted when a tainted data
  ancestor feeds it OR a tainted WRITER ran earlier under a declared
  `fs.read` (the file-mediated channel a static argv scan cannot see).
- ③ external egress · `permits.net.http` non-empty, OR a declared
  `fs.write` glob escapes the workspace (absolute · `~` · a preserved
  leading `..` after lexical normalization), OR `permits.exec` enabled.

When ①∧②∧③ hold, every egress-capable task the untrusted content
REACHES must be dominated by a blocking human gate — an
`invoke: nika:prompt` carrying NO `default:` arg (a default answers
without a human). Dominance, not ancestry: a gate a sibling branch
bypasses mitigates nothing. One violation per ungated tainted egress
task, in declaration order, the message opening with the NEP's verbatim
« lethal trifecta complete · human gate required » and naming which
disjunct satisfied leg ③ (NEP-0002 v2.1 §over-approximation posture:
the finding names its approximation instead of hiding it).

The lane is gated on a DECLARED `permits:` block and an analyzable
graph — an unknown `after:`/`tasks.*` id or a cycle yields NO claim
(skipped, never wrong). This is an independent implementation of the
same law the engine checks — zero shared code, per the two-oracle
doctrine of `scripts/oracle-differential.py`.

Granularity (effect-field level, the corpus-proven grain): taint
reaches a task only through the fields of its VERB block — a `with:`
binding that only a `when:` gate reads taints nothing (« a gate
decides, it does not transmit » · the config-drift-sentinel pattern:
the alert carries the FACT, never the payload), and `on_error.recover`
reads taint the task's OUTPUT (the substitution), never its effect.
"""
from __future__ import annotations

import posixpath
import re
from fnmatch import fnmatchcase

EXPR_BODY = re.compile(r"\$\{\{(.*?)\}\}", re.S)
TASK_REF = re.compile(r"\btasks\.([a-z][a-z0-9_]*)")
WITH_REF = re.compile(r"\bwith\.([a-z][a-z0-9_]*)")
ITEM_REF = re.compile(r"\bitem\b")

NET_BUILTINS = {"nika:fetch", "nika:notify"}
FS_WRITE_BUILTINS = {"nika:write", "nika:edit"}
INGRESS_BUILTIN = "nika:fetch"
GATE_TOOL = "nika:prompt"
VERBS = ("infer", "exec", "invoke", "agent")
_ROOT = -1


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def _refs(value) -> list[str]:
    """`tasks.<id>` ids inside `${{ }}` expressions · first-seen order."""
    out: list[str] = []
    for s in _strings(value):
        for body in EXPR_BODY.findall(s):
            for r in TASK_REF.findall(body):
                if r not in out:
                    out.append(r)
    return out


def _typed_refs(value) -> list[tuple[str, str]]:
    """(`tasks`|`with`|`item`, name) refs inside `${{ }}` · in order."""
    out: list[tuple[str, str]] = []
    for s in _strings(value):
        for body in EXPR_BODY.findall(s):
            for r in TASK_REF.findall(body):
                out.append(("tasks", r))
            for r in WITH_REF.findall(body):
                out.append(("with", r))
            if ITEM_REF.search(body):
                out.append(("item", ""))
    return out


def _after_ids(task: dict) -> list[str]:
    after = task.get("after")
    if isinstance(after, dict):
        return [k for k in after if isinstance(k, str)]
    if isinstance(after, list):
        return [k for k in after if isinstance(k, str)]
    if isinstance(after, str):
        return [after]
    return []


def _write_glob_escapes(glob: str) -> bool:
    """Leg ③'s write variant: absolute · home-anchored · a leading `..`
    preserved by lexical normalization (a relative escape stays visible)."""
    if glob.startswith(("/", "~")):
        return True
    return posixpath.normpath(glob).startswith("..")


def _grant_admits_ingress(grant) -> bool:
    """A `tools:` entry admits untrusted ingress: `nika:fetch` (glob-
    covered) or any `mcp:*` server. A negated entry admits nothing."""
    return (isinstance(grant, str) and not grant.startswith("!")
            and (grant.startswith("mcp:") or fnmatchcase(INGRESS_BUILTIN, grant)))


def _whitelist_admits(tools, targets: set[str]) -> bool:
    """An agent whitelist admits any of `targets` (glob-aware) or `mcp:*`."""
    if not isinstance(tools, list):
        return False
    for g in tools:
        if not isinstance(g, str) or g.startswith("!"):
            continue
        if g.startswith("mcp:"):
            return True
        if any(fnmatchcase(t, g) for t in targets):
            return True
    return False


def _verb_of(task: dict):
    for v in VERBS:
        if v in task:
            return v, task.get(v)
    return None, None


def _invoke_tool(action):
    if isinstance(action, dict):
        t = action.get("tool")
        if isinstance(t, str):
            return t
    return None


def _classify(task: dict):
    """(verb, action, ingress_source, egress_capable, human_gate, writer).

    Egress-capable = `exec:` · `invoke:` of a net or fs-write builtin ·
    `mcp:*` (server-side effects · fail-closed) · an `agent:` whose
    whitelist admits an egress-effecting tool. `infer:` is not egress; a
    child `workflow:` call is spec 14's (`NIKA-COMP-002`), never judged
    here. Writer = a task capable of writing the filesystem (an fs-write
    builtin or an `exec:`) — the exec-opacity channel's first half.
    """
    verb, action = _verb_of(task)
    ingress = egress = gate = writer = False
    if verb == "exec":
        egress = True
        writer = True
    elif verb == "agent":
        tools = action.get("tools") if isinstance(action, dict) else None
        ingress = _whitelist_admits(tools, {INGRESS_BUILTIN})
        egress = _whitelist_admits(tools, NET_BUILTINS | FS_WRITE_BUILTINS)
    elif verb == "invoke":
        tool = _invoke_tool(action)
        if tool is None:
            pass  # `invoke: workflow:` — the composition chapter owns it
        elif tool.startswith("mcp:"):
            ingress = True
            egress = True
        else:
            ingress = tool == INGRESS_BUILTIN
            egress = tool in NET_BUILTINS or tool in FS_WRITE_BUILTINS
            writer = tool in FS_WRITE_BUILTINS
            if tool == GATE_TOOL:
                args = action.get("args") if isinstance(action, dict) else None
                gate = not (isinstance(args, dict) and "default" in args)
    return verb, action, ingress, egress, gate, writer


def trifecta_errors(doc) -> list[dict]:
    """The NEP-0002 verdict · [] unless the realized trifecta escapes a
    dominating gate. Total: defensive on every shape, raises never."""
    if not isinstance(doc, dict):
        return []
    permits = doc.get("permits")
    if not isinstance(permits, dict):
        return []  # no declared boundary → the legs are not decidable → no claim
    tasks_map = doc.get("tasks")
    if not isinstance(tasks_map, dict) or not tasks_map:
        return []
    order = [(k, v) for k, v in tasks_map.items()
             if isinstance(k, str) and isinstance(v, dict)]
    if len(order) != len(tasks_map):
        return []  # unanalyzable task shapes → no claim
    idx = {tid: i for i, (tid, _) in enumerate(order)}
    n = len(order)

    # ── the projected rows + the derived graph (control AND data edges) ──
    verbs, actions, ingress, egress, gates, writers = [], [], [], [], [], []
    graph_parents: list[set[int]] = []
    for tid, task in order:
        verb, action, ing, egr, gat, wri = _classify(task)
        verbs.append(verb)
        actions.append(action)
        ingress.append(ing)
        egress.append(egr)
        gates.append(gat)
        writers.append(wri)
        refs = _refs([task.get("with"), action, task.get("for_each"),
                      task.get("on_error"), task.get("when")])
        afters = _after_ids(task)
        for r in refs + afters:
            if r not in idx:
                return []  # unknown id → unanalyzable graph → no claim
        graph_parents.append({idx[r] for r in refs} | {idx[a] for a in afters})

    # ── Kahn waves (a cycle → no order → no claim) ──
    indeg = [len(graph_parents[i]) for i in range(n)]
    children: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        for p in graph_parents[i]:
            children[p].append(i)
    waves: list[list[int]] = []
    frontier = sorted(i for i in range(n) if indeg[i] == 0)
    seen = 0
    while frontier:
        waves.append(frontier)
        seen += len(frontier)
        nxt: set[int] = set()
        for i in frontier:
            for c in children[i]:
                indeg[c] -= 1
                if indeg[c] == 0:
                    nxt.add(c)
        frontier = sorted(nxt)
    if seen != n:
        return []  # cycle → skipped, never wrong

    # ── the three legs off the declared boundary ──
    fs = permits.get("fs") if isinstance(permits.get("fs"), dict) else {}
    read = fs.get("read") if isinstance(fs.get("read"), list) else []
    leg1 = bool(read)
    tools_grant = permits.get("tools")
    grant_ok = (isinstance(tools_grant, list)
                and any(_grant_admits_ingress(g) for g in tools_grant))
    leg2 = grant_ok and any(ingress)
    net = permits.get("net") if isinstance(permits.get("net"), dict) else {}
    http = net.get("http") if isinstance(net.get("http"), list) else []
    writes = fs.get("write") if isinstance(fs.get("write"), list) else []
    escapes = any(_write_glob_escapes(g) for g in writes if isinstance(g, str))
    allows_exec = bool(permits.get("exec"))
    leg3 = bool(http) or escapes or allows_exec
    if not (leg1 and leg2 and leg3):
        return []
    disjunct = ("`net.http` non-empty" if http
                else "a declared `fs.write` glob escapes the workspace"
                if escapes else "`exec` enabled")

    # ── the content-taint sweep (effect-field grain · least fixpoint) ──
    # Taint reaches a task's EFFECT only through its verb block's fields —
    # `with.K` resolves to that binding's own source, `item` to the
    # `for_each` source. A `when:` read DECIDES, it does not transmit (a
    # binding only a gate reads taints nothing — the config-drift-sentinel
    # pattern: the alert carries the fact, never the payload). An
    # `on_error.recover` read substitutes the OUTPUT, never the effect.
    out_origin: list[str | None] = [None] * n
    eff_origin: list[str | None] = [None] * n
    writer_origin: str | None = None

    def _origin_of(kind: str, name: str, with_src: dict, item_src):
        if kind == "tasks":
            j = idx.get(name)
            return out_origin[j] if j is not None else None
        if kind == "with":
            return with_src.get(name)
        return item_src

    for wave in waves:
        for i in wave:
            tid, task = order[i]
            item_src = next(
                (out_origin[idx[r]] for r in _refs(task.get("for_each"))
                 if out_origin[idx[r]] is not None), None)
            with_map = (task.get("with")
                        if isinstance(task.get("with"), dict) else {})
            with_src: dict[str, str] = {}
            for key, val in with_map.items():
                if not isinstance(key, str):
                    continue
                for kind, name in _typed_refs(val):
                    origin = _origin_of(kind, name, {}, item_src)
                    if origin is not None:
                        with_src[key] = origin
                        break
            eff = next(
                (o for kind, name in _typed_refs(actions[i])
                 if (o := _origin_of(kind, name, with_src, item_src))
                 is not None), None)
            if (verbs[i] == "exec" and eff is None and leg1
                    and writer_origin is not None):
                eff = writer_origin  # the file channel argv cannot see
            recover = None
            on_err = task.get("on_error")
            if isinstance(on_err, dict):
                recover = next(
                    (o for kind, name in _typed_refs(on_err.get("recover"))
                     if (o := _origin_of(kind, name, with_src, item_src))
                     is not None), None)
            eff_origin[i] = eff
            out_origin[i] = (tid if ingress[i]
                             else (eff if eff is not None else recover))
            if writers[i] and eff is not None and writer_origin is None:
                writer_origin = eff

    # ── dominators over the derived DAG (virtual root · one topo pass) ──
    dom: list[set[int]] = [set() for _ in range(n)]
    for wave in waves:
        for i in wave:
            ps = graph_parents[i]
            if not ps:
                d = {_ROOT}
            else:
                acc: set[int] | None = None
                for p in ps:
                    acc = set(dom[p]) if acc is None else acc & dom[p]
                d = acc if acc is not None else {_ROOT}
            d = set(d)
            d.add(i)
            dom[i] = d

    # ── one violation per ungated tainted egress task · declaration order ──
    errs: list[dict] = []
    for i, (tid, _) in enumerate(order):
        if not egress[i] or eff_origin[i] is None:
            continue
        if any(g >= 0 and g != i and gates[g] for g in dom[i]):
            continue
        src = eff_origin[i]
        errs.append({
            "code": "NIKA-SEC-009", "namespace": "NIKA-SEC",
            "category": "security_error", "task": tid, "source": src,
            "detail": (
                f"lethal trifecta complete · human gate required — untrusted "
                f"content from `{src}` reaches egress task `{tid}` while "
                f"① private read (`fs.read` non-empty) ∧ ② untrusted ingress "
                f"(realized by `{src}`) ∧ ③ external egress ({disjunct}) are "
                f"all permitted, and no blocking `invoke: nika:prompt` (no "
                f"`default:`) dominates every path to it · fix: gate the "
                f"egress path behind a human prompt, or drop the unused leg "
                f"(NEP-0002 · the Rule of Two as a check)")})
    return errs
