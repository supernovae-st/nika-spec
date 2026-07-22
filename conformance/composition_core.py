# SPDX-License-Identifier: Apache-2.0
#
# The composition lane of the reference model (spec 14-composition.md ·
# W-COMP). The STATIC laws, judged from the parent doc + the resolved
# child files (a fixture-dir reader threads the base_dir):
#
#   NIKA-COMP-001  the workflow: target is not statically resolvable
#                  (templated · malformed · unpinned registry ·
#                  unreadable/unparseable child)
#   NIKA-COMP-002  the child's effect boundary exceeds the parent
#                  (coarse effect classes · exec/net/write/tools · the
#                  same table policy_errors reads · child needs an
#                  effect the parent's permits: do not grant ·
#                  NEP-0003: containment = parent ∩ child-declared, an
#                  absent block on either side is the zero wall)
#   NIKA-COMP-003  the static call graph is not acyclic (self-launch ·
#                  cycle · cap the depth fail-closed)
#   NIKA-COMP-004  the typed call does not compose (parent args ⋢ child
#                  inputs · child outputs ⋢ parent returns · the one
#                  type core, composed)
#
# Cross-file laws (002/003/004) need the child; when no base_dir is
# available (an example, no siblings) only the single-doc law (001)
# runs — the reference judges exactly what a reader-less consumer can.

from __future__ import annotations

import re

import yaml

from type_core import assignable, parse_type

EXPR = re.compile(r"(?<!\\)\$\{\{")
REGISTRY = re.compile(r"^registry:[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*@[^@\s]+$")
MAX_DEPTH = 64

# the coarse effect table — one voice with deep_static.policy_errors
NET_TOOLS = {"nika:fetch", "nika:notify"}
WRITE_TOOLS = {"nika:write", "nika:edit"}


def _tasks(doc: dict):
    t = doc.get("tasks")
    return list(t.items()) if isinstance(t, dict) else []


def _workflow_target(task: dict):
    inv = task.get("invoke")
    if isinstance(inv, dict) and isinstance(inv.get("workflow"), str):
        return inv["workflow"], inv.get("args")
    return None, None


def _err(code: str, detail: str) -> dict:
    cat = "security_error" if code == "NIKA-COMP-002" else "validation_error"
    return {"code": code, "namespace": "NIKA-COMP", "category": cat, "detail": detail}


def _effect_classes(doc: dict) -> set[str]:
    """The coarse effect classes a whole workflow carries (spec 14 law
    3/4 · exec · net · write · tools) — inferred from its task bodies,
    the child's contract DERIVED, never annotated."""
    out: set[str] = set()
    for _tid, t in _tasks(doc):
        if not isinstance(t, dict):
            continue
        if "exec" in t:
            out.add("exec")
        inv = t.get("invoke")
        if isinstance(inv, dict) and isinstance(inv.get("tool"), str):
            out.add("tools")
            tool = inv["tool"]
            if tool in NET_TOOLS:
                out.add("net")
            if tool in WRITE_TOOLS:
                out.add("write")
    return out


def _declared_grants(doc: dict) -> set[str]:
    """The effect classes a permits: block grants. NEP-0003 /
    LAW-AUTH-0324: an ABSENT block declares zero authority
    (DeclaredPermits := ∅ · the zero wall) — never the ambient floor."""
    permits = doc.get("permits")
    if not isinstance(permits, dict):
        return set()  # absent or null · zero authority (NEP-0003)
    granted: set[str] = set()
    ex = permits.get("exec")
    if ex is True or isinstance(ex, list):
        granted.add("exec")
    net = permits.get("net")
    if isinstance(net, dict) and net.get("http"):
        granted.add("net")
    fs = permits.get("fs")
    if isinstance(fs, dict) and fs.get("write"):
        granted.add("write")
    if isinstance(permits.get("tools"), list):
        granted.add("tools")
    return granted


def _load_child(base_dir, target: str):
    """(child_doc, resolved_path) or (None, None) when unreadable."""
    if base_dir is None:
        return None, None
    path = (base_dir / target).resolve()
    if not path.is_file():
        return None, None
    try:
        return yaml.safe_load(path.read_text()), path
    except yaml.YAMLError:
        return None, None


def _typed_call(parent_task: dict, args, child: dict, where: str) -> list[dict]:
    """COMP-004 · parent args fit child inputs · child outputs fit
    parent returns — the assignable relation of spec 09, composed. The child's
    caller contract is its `inputs:` block (R3a · the E-split · the typed half
    of the dead `vars:` · `const:` literals are internal, never caller-supplied)."""
    errs: list[dict] = []
    child_inputs = child.get("inputs") if isinstance(child.get("inputs"), dict) else {}
    args = args if isinstance(args, dict) else {}
    for name, decl in child_inputs.items():
        required = isinstance(decl, dict) and decl.get("required") is True
        if required and name not in args and not (isinstance(decl, dict) and "default" in decl):
            errs.append(_err("NIKA-COMP-004",
                             f"{where} · required child input {name!r} is not "
                             "supplied by args (spec 14 law 2)"))
    for name, val in args.items():
        decl = child_inputs.get(name)
        if not isinstance(decl, dict) or "type" not in decl:
            continue
        try:
            ct = parse_type(decl["type"], set(), f"{where}.args.{name}")
        except Exception:  # noqa: BLE001 — a bad child type surfaces elsewhere
            continue
        lit = _literal_type(val)
        if lit is not None and not assignable(lit, ct, {}):
            errs.append(_err("NIKA-COMP-004",
                             f"{where} · arg {name!r} does not fit the child "
                             f"input type (spec 14 law 2)"))
    ret = parent_task.get("returns")
    outs = child.get("outputs") if isinstance(child.get("outputs"), dict) else None
    if ret is not None and outs is not None:
        try:
            rt = parse_type(ret, set(), f"{where}.returns")
        except Exception:  # noqa: BLE001
            rt = None
        if rt is not None and rt.get("object") is not None:
            for field, ftype in rt["object"].items():
                od = outs.get(field)
                if od is None:
                    continue
                if isinstance(od, dict) and "type" in od:
                    try:
                        ot = parse_type(od["type"], set(), f"{where}.out.{field}")
                    except Exception:  # noqa: BLE001
                        continue
                    if not assignable(ot, ftype["ty"] if "ty" in ftype else ftype, {}):
                        errs.append(_err("NIKA-COMP-004",
                                         f"{where} · child output {field!r} does not "
                                         "fit the parent returns: (spec 14 law 2)"))
    return errs


def _literal_type(v):
    if isinstance(v, bool):
        return {"prim": "bool"}
    if isinstance(v, int):
        return {"prim": "integer"}
    if isinstance(v, float):
        return {"prim": "number"}
    if isinstance(v, str):
        return None if EXPR.search(v) else {"prim": "string"}
    return None


def _acyclic(base_dir, start: str, doc: dict) -> list[dict]:
    """COMP-003 · resolve the static call graph from `start`, refuse a
    self-launch or a cycle · cap depth fail-closed."""
    if base_dir is None:
        return []
    start_path = (base_dir / start).resolve()
    seen: set[str] = set()
    stack = [(start_path, doc, 0)]
    while stack:
        path, d, depth = stack.pop()
        if depth > MAX_DEPTH:
            return [_err("NIKA-COMP-003",
                         f"call graph deeper than {MAX_DEPTH} — refused fail-closed")]
        key = str(path)
        if key in seen:
            return [_err("NIKA-COMP-003",
                         f"static call graph is not acyclic — {path.name} recurs "
                         "(self-launch or cycle · spec 14 law 7)")]
        seen.add(key)
        if not isinstance(d, dict):
            continue
        for _tid, t in _tasks(d):
            tgt, _ = _workflow_target(t) if isinstance(t, dict) else (None, None)
            if tgt is None or EXPR.search(tgt) or tgt.startswith("registry:"):
                continue
            child, cpath = _load_child(path.parent, tgt)
            if cpath is not None:
                stack.append((cpath, child, depth + 1))
    return []


def composition_errors(doc: dict, base_dir=None) -> list[dict]:
    """The static composition laws (spec 14)."""
    if not isinstance(doc, dict):
        return []
    errs: list[dict] = []
    parent_granted = _declared_grants(doc)
    for tid, task in _tasks(doc):
        if not isinstance(task, dict):
            continue
        target, args = _workflow_target(task)
        if target is None:
            continue
        where = f"tasks.{tid}"
        # COMP-001 · static resolvability
        if EXPR.search(target):
            errs.append(_err("NIKA-COMP-001",
                             f"{where} · workflow: target is templated — a call "
                             "graph you cannot draw before the run cannot be "
                             "bounded (spec 14)"))
            continue
        if target.startswith("registry:"):
            if not REGISTRY.match(target):
                errs.append(_err("NIKA-COMP-001",
                                 f"{where} · registry target must be pinned "
                                 "registry:owner/name@version (spec 14)"))
            continue
        child, cpath = _load_child(base_dir, target)
        if base_dir is not None and cpath is None:
            errs.append(_err("NIKA-COMP-001",
                             f"{where} · workflow: target {target!r} is not a "
                             "readable/parseable child (spec 14)"))
            continue
        if child is None:
            continue  # no reader available · single-doc laws only
        # COMP-003 · acyclic (walk DOWN from the child, its own doc)
        errs.extend(_acyclic(base_dir, target, child))
        # COMP-004 · typed call
        errs.extend(_typed_call(task, args, child, where))
        # COMP-002 · effect containment (coarse · child needs ⊆ parent ∩
        # child-declared · NEP-0003 law 6: the parent's grants never flow
        # down implicitly — a child that touches the world declares it)
        child_needs = _effect_classes(child)
        exceeds = child_needs - (parent_granted & _declared_grants(child))
        if exceeds:
            errs.append(_err("NIKA-COMP-002",
                             f"{where} · child needs effect(s) {sorted(exceeds)} the "
                             "boundary does not grant (Authority(child) ⊆ parent ∩ "
                             "child-declared · absent block = ∅ · NEP-0003 · "
                             "spec 14 laws 3/4)"))
    # de-dup (a cycle can be reported once per entry)
    seen, out = set(), []
    for e in errs:
        k = (e["code"], e["detail"])
        if k not in seen:
            seen.add(k)
            out.append(e)
    return out
