#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Table-driven selftest for the project's missed-slot law (01 §The project's missed slots).

Proves the project schema's `manqué` on both sides of each boundary: the three words, the explicit
`{ rattraper: N }` from 1, and every near miss refused (0, a negative, a fraction, a quoted number,
an extra key, an empty mapping, an unknown word).
Exit 0 green · 1 red.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
SCHEMA = json.loads((HERE.parent / "schemas" / "project.schema.json").read_text())
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA)

CHECKS: list[tuple[str, bool]] = []


def law(name: str, holds: bool) -> None:
    CHECKS.append((name, holds))


def project(manque: object) -> dict:
    return {
        "nika": "missed-slots",
        "arm": [{"workflow": "workflows/report.nika", "cadence": "TZ=Europe/Paris 0 9 * * 1-5",
                 "plafond": 0.5, "manqué": manque}],
    }


for word in ("sauter", "rattraper", "rattraper-une-fois"):
    law(f"manqué: {word} is valid", VALIDATOR.is_valid(project(word)))
for n in (1, 3, 30):
    law(f"manqué: {{ rattraper: {n} }} is valid", VALIDATOR.is_valid(project({"rattraper": n})))
for refused in (
    {"rattraper": 0},
    {"rattraper": -2},
    {"rattraper": 2.5},
    {"rattraper": "3"},
    {"rattraper": 3, "plafond": 1},
    {},
    "rattraper-deux",
    3,
):
    errors = list(VALIDATOR.iter_errors(project(refused)))
    law(f"manqué: {json.dumps(refused, ensure_ascii=False)} is refused", bool(errors))
    law(
        f"manqué: {json.dumps(refused, ensure_ascii=False)} is refused at manqué",
        all(list(e.absolute_path)[:3] == ["arm", 0, "manqué"] for e in errors),
    )

failed = [name for name, holds in CHECKS if not holds]
for name in failed:
    print(f"FAIL  {name}")
print(f"project-missed-slots selftest · {len(CHECKS) - len(failed)}/{len(CHECKS)} laws hold")
sys.exit(1 if failed else 0)
