#!/usr/bin/env python3
"""permits-explicit-v1 codemod — NEP-0003 (TEMPORARY tool).

The one official codemod for the absent-permits flip (LAW-AUTH-0324 ·
ratified 2026-07-22 · precedent: codemod-esplit.py). Line-based and
structure-aware: it preserves comments, blank lines, anchors and source
order byte-for-byte outside the inserted block, and it is idempotent (a
file that already carries `permits:` passes through unchanged). It dies
with the window once the census of block-less effect-carrying files
reaches zero.

What it does, per file, in ONE pass:

  INSERT a top-level `permits:` block immediately above the `tasks:` key
  (above the contiguous blank/comment run glued to `tasks:`, so a heading
  comment stays attached to its section). The block is the ORACLE's own
  inference (conformance/deep_static.py `_infer_permits_block` — the same
  object the NIKA-AUTH-006 detail carries inline), never a guess:

    tools:  every statically-invoked tool (pure included · PERMITS-FIT
            default-denies any omitted tool once a block exists)
    exec:   every static argv[0]
    net:    { http: [every static fetch/notify host] }
    fs:     { read: [static read paths] · write: [static write paths] }

A file with NO static effects needs no block (pure compute stays green
under NEP-0003 law 4) — the codemod says so and changes nothing. A file
whose only effects are DYNAMIC (a computed host/path/program) is the
runtime boundary's (NIKA-SEC-004 · law 3), not this tool's.

usage:
  codemod-permits-explicit-v1.py --check FILE...   dry-run report
  codemod-permits-explicit-v1.py --write FILE...   apply, then re-validate
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "conformance"))

import yaml  # noqa: E402
from deep_static import _infer_permits_block, iter_tasks  # noqa: E402


def _flow_seq(xs: list) -> str:
    return "[" + ", ".join(json.dumps(x) for x in xs) + "]"


def render(block: dict) -> list[str]:
    """The block in house style (one line per category · flow collections ·
    the deep/014-permits-fit-valid shape)."""
    lines = ["permits:"]
    if "tools" in block:
        lines.append(f"  tools: {_flow_seq(block['tools'])}")
    if "exec" in block:
        lines.append(f"  exec: {_flow_seq(block['exec'])}")
    if "net" in block:
        lines.append(f"  net: {{ http: {_flow_seq(block['net']['http'])} }}")
    if "fs" in block:
        parts = [f"{k}: {_flow_seq(block['fs'][k])}"
                 for k in ("read", "write") if k in block["fs"]]
        lines.append("  fs: { " + ", ".join(parts) + " }")
    return lines


def migrate(text: str) -> tuple[str | None, str]:
    """(new_text, note) · (None, note) when the file is left alone."""
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict):
        return None, "not a mapping — skipped"
    if "permits" in doc:
        return None, "permits: present — idempotent no-op"
    block = _infer_permits_block(iter_tasks(doc))
    if not block:
        return None, "no static effects — pure compute needs no block (law 4)"
    lines = text.split("\n")
    idx = next((i for i, l in enumerate(lines) if l.startswith("tasks:")), None)
    if idx is None:
        return None, "no top-level tasks: key — skipped"
    # keep the blank/comment run above tasks: glued to tasks:
    ins = idx
    while ins > 0 and (not lines[ins - 1].strip()
                       or lines[ins - 1].lstrip().startswith("#")):
        ins -= 1
    out = lines[:ins] + render(block)
    if lines[ins].lstrip().startswith("#"):
        out.append("")
    out += lines[ins:]
    return "\n".join(out), f"inserted {render(block)}"


def validate(path: pathlib.Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "conformance" / "runner.py"),
         "validate", str(path)],
        capture_output=True, text=True)
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return False, f"runner emitted no verdict: {proc.stdout[:120]}"
    if verdict.get("valid") is True:
        return True, "valid"
    got = [e.get("code") or e.get("namespace") for e in verdict.get("errors", [])]
    return False, f"STILL RED: {got}"


def main(argv: list[str]) -> int:
    write = "--write" in argv
    files = [pathlib.Path(a) for a in argv[1:] if not a.startswith("--")]
    if not files:
        print(__doc__)
        return 2
    rc = 0
    for f in files:
        new, note = migrate(f.read_text())
        if new is None:
            print(f"SKIP  {f} · {note}")
            continue
        if write:
            f.write_text(new)
            ok, verdict = validate(f)
            print(f"{'WRITE' if ok else 'FAIL '}  {f} · {verdict}")
            rc |= 0 if ok else 1
        else:
            print(f"WOULD {f} · {note}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
