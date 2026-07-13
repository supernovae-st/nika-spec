#!/usr/bin/env python3
"""W1 « the map » migrator — workflow object + tasks map (TEMPORARY tool).

Line-based and structure-aware: preserves comments, blank lines and source
order byte-for-byte outside the three transformed shapes. Idempotent (a
migrated file passes through unchanged). Dies with the window once the
corpus is migrated (the lasting user-facing teaching lives in the engine's
`check --fix`, per the G6 ruling) — until then it is the ONE official
codemod every sweep goes through.

Transforms (top-level only · nothing else is touched):
  1. `workflow: <scalar>`            → `workflow:\n  id: <scalar>`
  2. top-level `description: <text>` → `  description: <text>` under workflow
  3. `tasks:` sequence items `  - id: X` → map keys `  X:` (content lines
     keep their indentation — the two-space list marker becomes the key's
     two-space indent, so the body never re-indents)

Deliberately NOT handled (loud is correct): a task whose `id:` is not the
item's first line — the conformance runner flags the file post-sweep.

usage:
  migrate-w1.py FILE...            rewrite in place (only when changed)
  migrate-w1.py --check FILE...    exit 1 if any file WOULD change
  migrate-w1.py --md FILE...       migrate fenced ```yaml blocks in markdown
"""

from __future__ import annotations

import re
import sys

WF_SCALAR = re.compile(r"^workflow: +([A-Za-z0-9_-]+)( +#.*)? *$")
DESC_TOP = re.compile(r"^description: +(.+?) *$")
TASK_ITEM = re.compile(r"^(  )- id: +([a-z][a-z0-9_]*)( +#.*)? *$")


def migrate_yaml(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    desc: str | None = None
    desc_line = -1
    wf_line = -1
    # pass 1: find the top-level description (to hoist) and the workflow line
    for i, l in enumerate(lines):
        if DESC_TOP.match(l) and desc is None:
            desc = DESC_TOP.match(l).group(1)
            desc_line = i
        if (WF_SCALAR.match(l) or l.startswith("workflow:")) and wf_line < 0:
            wf_line = i
    in_tasks = False
    for i, l in enumerate(lines):
        if i == desc_line:
            continue  # hoisted under workflow
        m = WF_SCALAR.match(l)
        if m and i == wf_line:
            out.append("workflow:")
            out.append(f"  id: {m.group(1)}{m.group(2) or ''}")
            if desc is not None:
                out.append(f"  description: {desc}")
            continue
        if l.startswith("workflow:") and i == wf_line and not m:
            # already an object — still hoist a stray top-level description
            out.append(l)
            if desc is not None:
                out.append(f"  description: {desc}")
            continue
        if re.match(r"^[a-z_]+:", l):
            in_tasks = l.startswith("tasks:")
        t = TASK_ITEM.match(l)
        if t and in_tasks:
            out.append(f"  {t.group(2)}:{t.group(3) or ''}")
            continue
        out.append(l)
    return "\n".join(out)


FENCE = re.compile(r"(```ya?ml\n)(.*?)(```)", re.S)


def migrate_md(text: str) -> str:
    def sub(m: re.Match) -> str:
        block = m.group(2)
        # migrate full workflows AND fragments (a `- id:` block is a nika
        # tasks fragment; non-nika yaml in our docs never uses that shape)
        if "nika: v1" not in block and "- id:" not in block:
            return m.group(0)
        return m.group(1) + migrate_yaml(block) + m.group(3)

    return FENCE.sub(sub, text)


def main() -> int:
    args = sys.argv[1:]
    check = "--check" in args
    md = "--md" in args
    files = [a for a in args if not a.startswith("--")]
    would = 0
    for path in files:
        with open(path, encoding="utf-8") as f:
            before = f.read()
        after = migrate_md(before) if md else migrate_yaml(before)
        if after != before:
            would += 1
            if check:
                print(f"WOULD-CHANGE {path}")
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(after)
                print(f"migrated {path}")
    if check and would:
        print(f"{would} file(s) still carry the old map")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
