#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
"""Every `Run ·` header names a path that exists.

The corpus README promises « the exact Run · command » — and for one day
after the flatten all 26 job headers taught `examples/showcase/tN-…`, a
directory that no longer existed (rc=3 for anyone who copied the line;
found by the golden re-proof, not by a gate). The files crossed the
rename; their own headers did not. This refuses the next one.

    python3 scripts/check-run-lines.py     # exit 0 clean · 1 on a dead path
"""

from __future__ import annotations

import pathlib
import re
import sys

SPEC_ROOT = pathlib.Path(__file__).resolve().parent.parent
RUN_RE = re.compile(r"^#\s*Run(?:\s*·| ·)?\s.*?\bnika\s+(?:run|check)\s+(\S+)", re.M)

def main() -> int:
    dead: list[str] = []
    files = sorted(
        list((SPEC_ROOT / "examples").glob("*.nika.yaml"))
        + list((SPEC_ROOT / "templates").glob("*.nika.yaml"))
    )
    for f in files:
        for target in RUN_RE.findall(f.read_text()):
            t = target.strip("`'\"")
            if t.startswith("-") or "<" in t or "$" in t:
                continue  # a flag or a placeholder, not a path
            if not (SPEC_ROOT / t).exists():
                dead.append(f"{f.relative_to(SPEC_ROOT)} → {t}")
    for d in dead:
        print(f"✗ dead Run · path · {d}", file=sys.stderr)
    if dead:
        return 1
    print(f"✓ Run · headers resolve · {len(files)} workflows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
