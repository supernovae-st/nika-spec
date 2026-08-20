#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 SuperNovae Studio <contact@supernovae.studio>
"""Keep every authoring surface aligned with the normative CEL callable set."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SURFACES = (
    ROOT / "spec/03-dag.md",
    ROOT / "AGENTS.md",
    ROOT / "eval/run-eval.py",
)
CALLABLES = ("size(", "has(", ".size(", ".contains(", ".startsWith(", ".endsWith(")
RETIRED = ("the ONE v0.1 function", "size() is the only CEL function")

failures: list[str] = []
for path in SURFACES:
    text = path.read_text(encoding="utf-8")
    missing = [callable_name for callable_name in CALLABLES if callable_name not in text]
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

print("authoring_contract_selftest PASS · 3 teaching surfaces · 6 CEL callables")
