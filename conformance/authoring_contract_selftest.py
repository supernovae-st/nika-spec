#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
"""Keep every authoring surface aligned with the normative CEL callable set."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUTHORING_GUIDE = ROOT / "templates/AUTHORING.md"
SURFACES = (
    ROOT / "spec/03-dag.md",
    AUTHORING_GUIDE,
    ROOT / "eval/run-eval.py",
)
CALLABLES = ("size(", "has(", ".size(", ".contains(", ".startsWith(", ".endsWith(")
RETIRED = ("the ONE v0.1 function", "size() is the only CEL function")

failures: list[str] = []
entry = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", entry)
if not any((ROOT / link.split("#", 1)[0]).resolve() == AUTHORING_GUIDE.resolve()
           for link in links):
    failures.append("AGENTS.md: no Markdown link to templates/AUTHORING.md")
for phrase in RETIRED:
    if phrase in entry:
        failures.append(f"AGENTS.md: retired claim {phrase!r}")
for path in SURFACES:
    if not path.is_file():
        failures.append(f"{path.relative_to(ROOT)}: teaching surface is missing")
        continue
    text = path.read_text(encoding="utf-8")
    # A member `.size(` must not stand in for the global `size(` function.
    missing = [name for name in CALLABLES
               if not re.search((r"(?<![\w.])" if not name.startswith(".") else "")
                                + re.escape(name), text)]
    stale = [phrase for phrase in RETIRED if phrase in text]
    if missing:
        failures.append(f"{path.relative_to(ROOT)}: missing {', '.join(missing)}")
    if stale:
        failures.append(f"{path.relative_to(ROOT)}: retired claim {stale[0]!r}")

if failures:
    print("authoring_contract_selftest FAIL")
    for failure in failures:
        print(f"  ✗ {failure}")
    sys.exit(1)

print(f"authoring_contract_selftest PASS · linked guide · {len(SURFACES)} teaching surfaces · {len(CALLABLES)} CEL callables")
