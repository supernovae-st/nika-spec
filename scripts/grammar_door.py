#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
#
# grammar_door.py — the served-grammar door · wnew → w2 · text-level.
#
# The pack (examples/ · templates/) is authored in the RATIFIED grammar
# (post-C2 · workflow map · task map · inputs/const). The binary a reader
# has installed still speaks W2 (workflow scalar · task list · vars). The
# door downcasts AT PROJECTION TIME so what a reader copies runs on THEIR
# nika — the same copy-paste invariant the website's serve-time door
# (src/lib/w1-to-w2.ts) protects, mirrored for baked surfaces (docs).
# Retires at the release train, when the released binary speaks the
# ratified grammar and this projection flips to identity.
#
# Text-level and comment-preserving BY DESIGN — comments teach, layout is
# curated; a parse/re-dump would destroy both. Five transforms:
#   1 · workflow: {id, description} → `workflow: <id>` + promoted
#       top-level `description:` (the W2 envelope)
#   2 · inputs: / const: → ONE merged `vars:` block · entries verbatim
#       (W2 vars accepts both literal defaults and typed declarations)
#   3 · tasks: map → list · `  <id>:` becomes `  - id: <id>` · bodies
#       verbatim (the 2-space discipline makes the indent invariant)
#   4 · ${{ inputs.X }} / ${{ const.X }} → ${{ vars.X }}
#   5 · STOP-list · any construct with no W2 twin (config:/types:/policy:
#       · workflow children beyond id/description · flow-bodied task
#       keys) REFUSES loudly — a surface that cannot be served pre-train
#       waits for the train, it never ships broken.
#
# Idempotent · a W2 document (scalar workflow · list tasks · vars) passes
# through byte-identical.
#
# TARGETS · `downcast_w2` serves the 0.104-era dialect (all five transforms).
# `downcast_w105` serves the RELEASED 0.105 dialect (measured on the release
# binary 2026-07-20 · map envelope + task map + after: already speak) — only
# two transforms remain: inputs/const → one vars block (+ ref rewrite) and
# the ratified predicate names fold to the released set (success→succeeded ·
# failure→failed). `types:`/`policy:` pass through (0.105 schema carries
# them) · `config:` stays on the STOP-list (no released twin yet).

from __future__ import annotations

import re
import sys

STOP_TOP_KEYS = ("config", "types", "policy")

TOP_KEY = re.compile(r"^([A-Za-z0-9_-]+):(.*)$")
WF_CHILD = re.compile(r"^  (id|description):\s?(.*)$")
TASK_KEY = re.compile(r"^  ([a-z][a-z0-9_-]*):\s*(#.*)?$")
TASK_KEY_FLOW = re.compile(r"^  ([a-z][a-z0-9_-]*):\s*\S")
TEMPLATE_REF = re.compile(r"\$\{\{.*?\}\}", re.DOTALL)
COMMENT_OR_BLANK = re.compile(r"^(\s*#.*)?$")


class DoorRefusal(RuntimeError):
    """A construct with no W2 twin — the STOP-list fired."""


def _refuse(name: str, line_no: int, why: str) -> None:
    raise DoorRefusal(f"grammar-door · {name}:{line_no + 1} · {why}")


def _block_ranges(lines: list[str]) -> list[tuple[str, str, int, int]]:
    """[(key, rest, start, end_exclusive)] for every top-level key.
    Trailing blank/comment lines that directly precede the NEXT top-level
    key are excluded from a block (they document what follows, not what
    precedes — the projector's banner convention)."""
    tops = [
        (m.group(1), m.group(2), i)
        for i, line in enumerate(lines)
        if (m := TOP_KEY.match(line))
    ]
    out = []
    for n, (key, rest, start) in enumerate(tops):
        end = tops[n + 1][2] if n + 1 < len(tops) else len(lines)
        while end - 1 > start and COMMENT_OR_BLANK.match(lines[end - 1]):
            end -= 1
        out.append((key, rest, start, end))
    return out


def downcast_w2(text: str, name: str = "<inline>") -> str:
    """wnew → w2, text-level. Raises DoorRefusal on the STOP-list."""
    lines = text.splitlines()
    blocks = _block_ranges(lines)

    for key, _rest, start, _end in blocks:
        if key in STOP_TOP_KEYS:
            _refuse(name, start, f"`{key}:` has no W2 twin (STOP-list)")

    drop: set[int] = set()          # line indices to remove
    replace: dict[int, list[str]] = {}  # line index → replacement lines

    # ── 1 · the envelope · workflow map → scalar + promoted description ──
    wf = next((b for b in blocks if b[0] == "workflow"), None)
    if wf is not None and wf[1].strip() == "":
        _, _, start, end = wf
        wf_id, wf_desc, extras = None, None, []
        for i in range(start + 1, end):
            line = lines[i]
            if COMMENT_OR_BLANK.match(line):
                extras.append(line)
                continue
            m = WF_CHILD.match(line)
            if not m:
                _refuse(name, i, f"workflow child has no W2 twin: {line.strip()!r}")
            if m.group(1) == "id":
                wf_id = m.group(2).strip()
            else:
                wf_desc = m.group(2)
        if wf_id is None:
            _refuse(name, start, "workflow map without `id:`")
        promoted = [f"workflow: {wf_id}"]
        if wf_desc is not None:
            promoted.append(f"description: {wf_desc}")
        promoted += [e for e in extras if e.strip()]
        replace[start] = promoted
        for i in range(start + 1, end):
            drop.add(i)

    # ── 2 · inputs + const → one merged vars block ────────────────────
    value_blocks = [b for b in blocks if b[0] in ("inputs", "const")]
    if value_blocks:
        first = value_blocks[0]
        merged: list[str] = ["vars:"]
        for _key, rest, start, end in value_blocks:
            if rest.strip():
                _refuse(name, start, f"flow-style `{_key}:` block")
            merged.extend(lines[start + 1 : end])
        replace[first[2]] = merged
        for i in range(first[2] + 1, first[3]):
            drop.add(i)
        for _key, _rest, start, end in value_blocks[1:]:
            for i in range(start, end):
                drop.add(i)
            # the separator blank ABOVE a removed block collapses with it
            j = start - 1
            if j >= 0 and not lines[j].strip() and j not in replace:
                drop.add(j)

    # ── 3 · tasks map → list · after: folds · edges synthesized ──────
    # W2 is declarative (NIKA-DAG-003): every `${{ tasks.X }}` reference
    # must be a declared `depends_on` edge. wnew implies edges from refs
    # and gates with task-level `after:` (keys carry the edge; the state
    # qualifier collapses to W2 default depends_on semantics — the same
    # fold the website door ships, proven by `nika check` downstream).
    tasks = next((b for b in blocks if b[0] == "tasks"), None)
    if tasks is not None and tasks[1].strip() == "":
        _, _, start, end = tasks
        keys = [
            (i, m.group(1), m.group(2))
            for i in range(start + 1, end)
            if (m := TASK_KEY.match(lines[i]))
        ]
        known = {tid for _i, tid, _c in keys}
        for i in range(start + 1, end):
            if (
                TASK_KEY_FLOW.match(lines[i])
                and not TASK_KEY.match(lines[i])
                and not lines[i].lstrip().startswith("#")
                and not lines[i].startswith("  - ")
            ):
                _refuse(name, i, f"flow-bodied task key: {lines[i].strip()!r}")
        for n, (kline, tid, comment) in enumerate(keys):
            bend = keys[n + 1][0] if n + 1 < len(keys) else end
            deps: list[str] = []

            def _add(d: str) -> None:
                if d in known and d != tid and d not in deps:
                    deps.append(d)

            # task-level after: (indent 4 exactly · deeper = tool args)
            after_line, after_children = None, []
            has_depends = False
            for j in range(kline + 1, bend):
                body = lines[j]
                if re.match(r"^    depends_on:", body):
                    has_depends = True
                am = re.match(r"^    after:\s*(.*?)\s*(?:#.*)?$", body)
                if am is not None:
                    after_line = j
                    rest = am.group(1)
                    if rest.startswith("["):
                        for tok in rest.strip("[]").split(","):
                            _add(tok.strip().strip("\"'"))
                    elif rest.startswith("{"):
                        for pair in rest.strip("{}").split(","):
                            _add(pair.split(":", 1)[0].strip().strip("\"'"))
                    elif rest:
                        _add(rest.strip("\"'"))
                    else:
                        k = j + 1
                        while k < bend and (
                            re.match(r"^      \S", lines[k]) or not lines[k].strip()
                        ):
                            cm = re.match(r"^      ([A-Za-z0-9_-]+)\s*:", lines[k])
                            if cm:
                                _add(cm.group(1))
                            elif lines[k].strip() and not lines[k].lstrip().startswith("#"):
                                _refuse(name, k, f"after: child not a map key: {lines[k].strip()!r}")
                            after_children.append(k)
                            k += 1
            # value edges · every ${{ … tasks.X … }} in the body
            body_text = "\n".join(lines[kline + 1 : bend])
            for tm in TEMPLATE_REF.finditer(body_text):
                for rm in re.finditer(r"\btasks\.([a-z][a-z0-9_-]*)\b", tm.group(0)):
                    _add(rm.group(1))

            trail = f"  {comment}" if comment else ""
            id_lines = [f"  - id: {tid}{trail}"]
            if has_depends:
                if after_line is not None:
                    _refuse(name, after_line, "task carries both after: and depends_on:")
            elif deps:
                dep_line = f"    depends_on: [{', '.join(deps)}]"
                if after_line is not None:
                    replace[after_line] = [dep_line]
                    for k in after_children:
                        drop.add(k)
                else:
                    id_lines.append(dep_line)
            replace[kline] = id_lines
        # already-W2 lists (`  - id:` lines) match no task key → untouched

    # ── assemble ──────────────────────────────────────────────────────
    out: list[str] = []
    for i, line in enumerate(lines):
        if i in replace:
            out.extend(replace[i])
        elif i not in drop:
            out.append(line)

    # ── 4 · reference rewrite · inside ${{ }} only ────────────────────
    def _rewrite(m: re.Match[str]) -> str:
        return re.sub(r"\b(inputs|const)\.", "vars.", m.group(0))

    return TEMPLATE_REF.sub(_rewrite, "\n".join(out).rstrip() + "\n")


PREDICATES_RATIFIED_TO_RELEASED = {"success": "succeeded", "failure": "failed"}

W105_STOP_TOP_KEYS = ("config",)

AFTER_INLINE = re.compile(r"^(\s{4}after:\s*\{)([^}]*)(\}.*)$")
AFTER_CHILD = re.compile(r"^(\s{6}[A-Za-z0-9_-]+:\s*)([a-z]+)(\s*(?:#.*)?)$")


def _fold_predicates(lines: list[str]) -> list[str]:
    """Rewrite ratified predicate names to the released set — ONLY inside
    task-level `after:` blocks (map children at indent 6 · inline flow map)."""
    out: list[str] = []
    in_after = False
    for line in lines:
        m = AFTER_INLINE.match(line)
        if m:
            body = re.sub(
                r"\b(success|failure)\b",
                lambda w: PREDICATES_RATIFIED_TO_RELEASED[w.group(0)],
                m.group(2),
            )
            out.append(m.group(1) + body + m.group(3))
            in_after = False
            continue
        if re.match(r"^\s{4}after:\s*(#.*)?$", line):
            in_after = True
            out.append(line)
            continue
        if in_after:
            c = AFTER_CHILD.match(line)
            if c and c.group(2) in PREDICATES_RATIFIED_TO_RELEASED:
                out.append(c.group(1) + PREDICATES_RATIFIED_TO_RELEASED[c.group(2)] + c.group(3))
                continue
            if not c and line.strip() and not line.lstrip().startswith("#"):
                in_after = False
        out.append(line)
    return out


def downcast_w105(text: str, name: str = "<inline>") -> str:
    """ratified → the RELEASED 0.105 dialect. Two transforms + STOP-list."""
    lines = text.splitlines()
    blocks = _block_ranges(lines)

    for key, _rest, start, _end in blocks:
        if key in W105_STOP_TOP_KEYS:
            _refuse(name, start, f"`{key}:` has no released twin (w105 STOP-list)")

    drop: set[int] = set()
    replace: dict[int, list[str]] = {}

    # inputs + const → one merged vars block (same fold as w2 · values only)
    value_blocks = [b for b in blocks if b[0] in ("inputs", "const")]
    if value_blocks:
        first = value_blocks[0]
        merged: list[str] = ["vars:"]
        for _key, rest, start, end in value_blocks:
            if rest.strip():
                _refuse(name, start, f"flow-style `{_key}:` block")
            merged.extend(lines[start + 1 : end])
        replace[first[2]] = merged
        for i in range(first[2] + 1, first[3]):
            drop.add(i)
        for _key, _rest, start, end in value_blocks[1:]:
            for i in range(start, end):
                drop.add(i)
            j = start - 1
            if j >= 0 and not lines[j].strip() and j not in replace:
                drop.add(j)

    out: list[str] = []
    for i, line in enumerate(lines):
        if i in replace:
            out.extend(replace[i])
        elif i not in drop:
            out.append(line)

    out = _fold_predicates(out)

    def _rewrite(m: re.Match[str]) -> str:
        return re.sub(r"\b(inputs|const)\.", "vars.", m.group(0))

    return TEMPLATE_REF.sub(_rewrite, "\n".join(out).rstrip() + "\n")


def main() -> int:
    text = sys.stdin.read()
    try:
        sys.stdout.write(downcast_w2(text, "<stdin>"))
    except DoorRefusal as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
