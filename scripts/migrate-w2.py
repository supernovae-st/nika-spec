#!/usr/bin/env python3
"""W2 « the flow » migrator — depends_on → with/after (TEMPORARY tool).

Equivalence-or-stop (the W2 law): a rewrite is applied ONLY when the
observable behavior {edges · waves · outputs · outcomes} is provably
unchanged. Every ambiguous case prints a diagnostic with the candidate
rewrites and their semantic deltas, and the file is left untouched (exit 3)
— the codemod never guesses. Comment-preserving and idempotent, like
migrate-w1.py. Dies with the window once the corpus is migrated (the
lasting user-facing teaching lives in the engine's `check --fix` per G6).

GO rules (mechanically equivalence-preserving):
  R1  a body/for_each `${{ tasks.X… }}` reference hoists into `with:`
      (the binding IS the edge) and X leaves `depends_on` —
      · bare projections (.output / .status / .error / .duration_ms /
        .started_at / .ended_at / a named binding) never error at eval
        (defined-null law) → always safe;
      · a DEEPER path (tasks.X.output.title) or a composite expression
        moves its eval from body-stage (on_error-recoverable) to
        boundary-stage (not recoverable) → safe ONLY when the task has
        no on_error: armor, else STOP;
      · a status-family-only referenced dep (terminal-observation
        pass-set ⊋ the old gate) keeps the old tightness ONLY with a
        value edge or a success predicate → STOP to choose.
  R2  a bare (unreferenced) dep whose producer provably CANNOT skip
      (no when: · no on_error.skip · no for_each) → after: {d: success}
      — {success,skipped} ≡ {success} when skipped is unreachable.
  R3  a dep already referenced through with: (value-role) is redundant →
      it just leaves depends_on.

STOP classes (human decision · the diagnostic names the deltas):
  S1  skippable producer on a bare dep (W2-Q1: success cancels where the
      old gate ran · terminal runs where the old gate cancelled · a value
      binding preserves the pass-set but imports data)
  S2  when: references tasks.* (pre-W2 when REPLACED the gate: any
      mechanical mapping changes skipped-vs-cancelled observability)
  S3  status-family-only reference backing a dep (no predicate spells the
      old {success,skipped} without data)
  S4  eval-fallible reference (deep path / composite) on a task with
      on_error: (the armor no longer covers the boundary)
  S5  on_finally references a NON-parent task (the W2 confinement closes
      a read race — pick: hoist the value into the parent, or accept the
      parent-only read)

usage:
  migrate-w2.py FILE...            rewrite in place (only when fully GO)
  migrate-w2.py --check FILE...    exit 1 if any file WOULD change (or STOP)
  migrate-w2.py --md FILE...       migrate fenced ```yaml blocks in markdown
  migrate-w2.py --stops FILE...    list STOP diagnostics only (no writes)
"""

from __future__ import annotations

import re
import sys

import yaml

REF = re.compile(r"\$\{\{\s*tasks\.([a-z][a-z0-9_]*)((?:\.[A-Za-z0-9_]+|\[[^\]]*\])*)\s*\}\}")
REF_ANY = re.compile(r"tasks\.([a-z][a-z0-9_]*)")
ISLAND = re.compile(r"\$\{\{(.*?)\}\}", re.S)
BARE_PROJ = {"output", "status", "error", "duration_ms", "started_at", "ended_at"}
STATUS_FAMILY = {"status", "duration_ms", "started_at", "ended_at"}


class Stop(Exception):
    def __init__(self, cls: str, task: str, detail: str):
        super().__init__(f"[{cls}] task {task!r}: {detail}")
        self.cls = cls


def _load(text: str):
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        return None


def _refs_in(value) -> list[tuple[str, str]]:
    """Every ${{ tasks.X<path> }} in a value tree → [(task, path)]."""
    out: list[tuple[str, str]] = []
    if isinstance(value, str):
        out.extend(REF.findall(value))
    elif isinstance(value, dict):
        for v in value.values():
            out.extend(_refs_in(v))
    elif isinstance(value, list):
        for v in value:
            out.extend(_refs_in(v))
    return out


def _islands_with_tasks(value) -> bool:
    if isinstance(value, str):
        return any("tasks." in i for i in ISLAND.findall(value))
    if isinstance(value, dict):
        return any(_islands_with_tasks(v) for v in value.values())
    if isinstance(value, list):
        return any(_islands_with_tasks(v) for v in value)
    return False


def _can_skip(task: dict) -> bool:
    if "when" in task:
        return True
    if "for_each" in task:
        return True
    on_error = task.get("on_error") or {}
    return isinstance(on_error, dict) and on_error.get("skip") is True


def _binding_name(task_id: str, path: str, taken: set[str]) -> str:
    segs = [s for s in re.split(r"\.|\[|\]", path) if s and not s.isdigit()]
    if segs and segs[0] == "output":
        segs = segs[1:]
    name = "_".join([task_id] + segs) if segs else task_id
    name = re.sub(r"[^a-z0-9_]", "_", name.lower()).strip("_") or task_id
    base, n = name, 2
    while name in taken:
        name = f"{base}_{n}"
        n += 1
    taken.add(name)
    return name


def _role(path: str) -> str:
    head = path.lstrip(".").split(".")[0].split("[")[0] if path else ""
    if head == "error":
        return "failure-observation"
    if head in STATUS_FAMILY:
        return "terminal-observation"
    return "value"  # .output, deep paths through it, or a named binding


def _is_bare(path: str) -> bool:
    p = path.lstrip(".")
    return p in BARE_PROJ or (p and "." not in p and "[" not in p)


VERB_KEYS = ("infer", "exec", "invoke", "agent")


def plan(doc: dict) -> dict[str, dict]:
    """Per-task migration plan (or Stop). Returns {task: {drop_deps, after,
    hoists: [(site_kind, task, path, binding)], set_for_each}}."""
    tasks = doc.get("tasks")
    if not isinstance(tasks, dict):
        return {}
    plans: dict[str, dict] = {}
    for tid, t in tasks.items():
        if not isinstance(t, dict):
            continue
        deps = t.get("depends_on")
        body_refs: list[tuple[str, str]] = []  # (task, path) from verb+for_each
        # when: any tasks.* → S2
        when = t.get("when")
        if when is not None and _islands_with_tasks(when):
            raise Stop(
                "S2",
                tid,
                "when: references tasks.* — pre-W2 it REPLACED the gate; "
                "candidates: (a) after:{X: success} if the intent was the "
                "strict success gate · (b) after:{X: terminal} + a .status "
                "observation binding if it was the always/branch pattern · "
                "(c) hoist the value into with: when the condition reads "
                "data — each changes skipped-vs-cancelled observability "
                "differently; a human picks.",
            )
        has_armor = isinstance(t.get("on_error"), dict)
        # collect body refs (verb fields) + for_each
        for vk in VERB_KEYS:
            if vk in t:
                body_refs.extend(_refs_in(t[vk]))
                if _islands_with_tasks(t[vk]) and not _refs_in(t[vk]):
                    raise Stop(
                        "S4", tid, f"a composite tasks.* island in {vk}: is not a "
                        "plain reference — hoist it by hand (the eval stage moves).")
        fe = t.get("for_each")
        fe_refs = _refs_in(fe) if isinstance(fe, str) else []
        body_refs.extend(fe_refs)
        # eval-fallible refs under armor → S4
        for rt, path in body_refs:
            if has_armor and not _is_bare(path):
                raise Stop(
                    "S4",
                    tid,
                    f"deep reference tasks.{rt}{path} sits under on_error: — "
                    "hoisting moves its evaluation outside the armor "
                    "(boundary errors are not recoverable); split the read "
                    "or accept the new error path by hand.",
                )
        with_block = t.get("with") if isinstance(t.get("with"), dict) else {}
        with_refs = _refs_in(with_block)
        referenced: dict[str, set[str]] = {}
        for rt, path in body_refs + with_refs:
            referenced.setdefault(rt, set()).add(_role(path))
        # deps analysis
        drop: list[str] = []
        after: dict[str, str] = {}
        dep_list = deps if isinstance(deps, list) else []
        if any(not isinstance(d, str) for d in dep_list):
            raise Stop("S7", tid, "malformed depends_on entries — a negative "
                       "fixture whose scenario needs a hand rewrite.")
        for d in dep_list:
            roles = referenced.get(d, set())
            if roles and "value" in roles:
                drop.append(d)  # R1/R3: the value edge carries the old pass-set
            elif roles:
                raise Stop(
                    "S3",
                    tid,
                    f"dep {d!r} is backed only by a {sorted(roles)} reference — "
                    "the observation edge admits on MORE states than the old "
                    "gate; pick: keep tightness via after:{" + d + ": success} "
                    "(cancels where the old gate cancelled AND on skipped) or "
                    "accept the wider admission by hand.",
                )
            else:
                prod = tasks.get(d)
                if isinstance(prod, dict) and _can_skip(prod):
                    raise Stop(
                        "S1",
                        tid,
                        f"bare dep {d!r} on a producer that may SKIP — the old "
                        "gate ran on skipped; after:{" + d + ": success} would "
                        "cancel there · after:{" + d + ": terminal} would also "
                        "run on failure · a value binding keeps {success,"
                        "skipped} but imports data; a human picks (W2-Q1).",
                    )
                after[d] = "success"  # R2
                drop.append(d)
        # hoists: body refs (value/obs/whatever role) move into with
        taken = set(with_block.keys())
        hoists: list[tuple[str, str, str]] = []  # (full_ref_src, binding, island_expr)
        for rt, path in body_refs:
            src = f"tasks.{rt}{path}"
            existing = next((h for h in hoists if h[0] == src), None)
            if existing:
                continue
            hoists.append((src, _binding_name(rt, path, taken), ""))
        # on_finally: non-parent refs → S5
        fin = t.get("on_finally")
        if fin is not None:
            for rt, _p in _refs_in(fin):
                if rt != tid:
                    raise Stop(
                        "S5",
                        tid,
                        f"on_finally references tasks.{rt} (not the parent) — "
                        "the W2 confinement closes this read race; hoist the "
                        "value into the parent's with: or drop the read.",
                    )
        if drop or hoists or (deps is not None and not dep_list):
            plans[tid] = {
                "drop_deps": drop,
                "after": after,
                "hoists": hoists,
                "had_deps": deps is not None,
            }
    return plans


# ---------------------------------------------------------------- surgery

TASK_KEY = re.compile(r"^(  )([a-z][a-z0-9_]*):\s*(#.*)?$")
DEP_LINE = re.compile(r"^(\s+)depends_on:\s*(\[[^\]]*\])?\s*(#.*)?$")
DEP_ITEM = re.compile(r"^\s+- [a-z][a-z0-9_]*\s*(#.*)?$")


def migrate_yaml(text: str) -> str:
    doc = _load(text)
    if not isinstance(doc, dict) or not isinstance(doc.get("tasks"), dict):
        return text
    if "depends_on" not in text and not plan_has_hoists(doc):
        return text
    plans = plan(doc)
    if not plans:
        return text
    lines = text.split("\n")
    out: list[str] = []
    cur: str | None = None
    in_tasks = False
    i = 0
    inserted_for: set[str] = set()

    def indent_of(line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    while i < len(lines):
        l = lines[i]
        if re.match(r"^[a-z_]+:", l):
            in_tasks = l.startswith("tasks:")
            cur = None
        m = TASK_KEY.match(l) if in_tasks else None
        if m:
            cur = m.group(2)
            out.append(l)
            i += 1
            # insertion point: right after the task key line
            p = plans.get(cur)
            if p and cur not in inserted_for:
                inserted_for.add(cur)
                if p["hoists"]:
                    shape = _task_has_with(lines, i)
                    if shape == "flow":
                        raise Stop(
                            "S6", cur,
                            "hoist needed but with: is flow-style — merge by hand "
                            "(the codemod does not rewrite flow maps).")
                    if shape == "block":
                        p["has_with_merge"] = True  # merge at the with: line
                    else:
                        out.append("    with:")
                        for src, binding, _ in p["hoists"]:
                            out.append(f"      {binding}: ${{{{ {src} }}}}")
                if p["after"]:
                    out.append("    after:")
                    for d, pred in p["after"].items():
                        out.append(f"      {d}: {pred}")
            continue
        p = plans.get(cur) if cur else None
        if p:
            dm = DEP_LINE.match(l)
            if dm:
                # drop the depends_on line (flow) or the whole block (list)
                if dm.group(2) is None:
                    i += 1
                    while i < len(lines) and DEP_ITEM.match(lines[i]):
                        i += 1
                    continue
                i += 1
                continue
            if re.match(r"^    with:\s*(#.*)?$", l) and _pending_merge(p):
                out.append(l)
                for src, binding, _ in p["hoists"]:
                    out.append(f"      {binding}: ${{{{ {src} }}}}")
                p["hoists_merged"] = True
                i += 1
                continue
        out.append(l)
        i += 1
    text2 = "\n".join(out)
    # rewrite the hoisted islands in body positions
    for tid, p in plans.items():
        for src, binding, _ in p["hoists"]:
            island = re.compile(r"\$\{\{\s*" + re.escape(src) + r"\s*\}\}")
            text2 = _replace_outside_with(text2, tid, island, f"${{{{ with.{binding} }}}}")
    return text2


def _pending_merge(p: dict) -> bool:
    return bool(p["hoists"]) and not p.get("hoists_merged") and p.get("has_with_merge")


def _task_has_with(lines: list[str], start: int) -> str | None:
    for j in range(start, len(lines)):
        l = lines[j]
        if TASK_KEY.match(l) or (l and not l.startswith(" ")):
            return None
        if re.match(r"^    with:\s*(#.*)?$", l):
            return "block"
        if re.match(r"^    with:\s*\{", l):
            return "flow"
    return None


def _replace_outside_with(text: str, tid: str, island: re.Pattern, repl: str) -> str:
    """Replace the island everywhere in tid's body EXCEPT inside its with:
    block (where the hoisted binding legitimately keeps the tasks.* ref)."""
    lines = text.split("\n")
    out = []
    cur = None
    in_tasks = False
    in_with = False
    with_indent = 0
    for l in lines:
        if re.match(r"^[a-z_]+:", l):
            in_tasks = l.startswith("tasks:")
            cur = None
            in_with = False
        m = TASK_KEY.match(l) if in_tasks else None
        if m:
            cur = m.group(2)
            in_with = False
        if cur == tid:
            ind = len(l) - len(l.lstrip(" "))
            if re.match(r"^\s+with:\s*(#.*)?$", l):
                in_with = True
                with_indent = ind
            elif in_with and l.strip() and ind <= with_indent:
                in_with = False
            if not in_with:
                l = island.sub(repl, l)
        out.append(l)
    return "\n".join(out)


def plan_has_hoists(doc: dict) -> bool:
    tasks = doc.get("tasks")
    if not isinstance(tasks, dict):
        return False
    for t in tasks.values():
        if not isinstance(t, dict):
            continue
        for vk in VERB_KEYS:
            if vk in t and _refs_in(t.get(vk)):
                return True
        if isinstance(t.get("for_each"), str) and _refs_in(t.get("for_each")):
            return True
    return False


FENCE = re.compile(r"(```ya?ml\n)(.*?)(```)", re.S)


def migrate_md(text: str) -> str:
    def sub(m: re.Match) -> str:
        block = m.group(2)
        if "depends_on" not in block and "tasks." not in block:
            return m.group(0)
        if "nika: v1" not in block and "tasks:" not in block:
            return m.group(0)
        try:
            return m.group(1) + migrate_yaml(block) + m.group(3)
        except Stop:
            raise

    return FENCE.sub(sub, text)


def main() -> int:
    args = sys.argv[1:]
    check = "--check" in args
    md = "--md" in args
    stops_only = "--stops" in args
    files = [a for a in args if not a.startswith("--")]
    would = 0
    stops = 0
    for path in files:
        with open(path, encoding="utf-8") as f:
            before = f.read()
        try:
            after = migrate_md(before) if md else migrate_yaml(before)
        except Stop as s:
            stops += 1
            print(f"STOP {path} · {s}")
            continue
        if stops_only:
            continue
        if after != before:
            would += 1
            if check:
                print(f"WOULD-CHANGE {path}")
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(after)
                print(f"migrated {path}")
    if stops:
        print(f"{stops} file(s) need a human decision (equivalence-or-stop)")
        return 3
    if check and would:
        print(f"{would} file(s) still carry the old flow")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
