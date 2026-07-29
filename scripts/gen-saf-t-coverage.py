#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate `conformance/redteam/coverage-saf-t.tsv` — GENERATED, never
hand-edited (F-P10 · a SAF-T technique in-scope without a fixture, a
bench, or an explicit out-of-scope row is a coverage FAIL).

Each `saf-tNNNN-*.nika.yaml` fixture declares its tag by name; this
walks the directory and emits one row per tag: tag · gate · fixture.
The gate exits 1 when an in-scope tag (the registry the file itself
carries) has zero rows.
"""
from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
REDTEAM = HERE.parent / "conformance" / "redteam"
OUT = REDTEAM / "coverage-saf-t.tsv"

# The in-scope registry (the techniques this corpus must cover — grows
# by NEP, never silently). Each row: tag · the gate judged to answer it.
IN_SCOPE: list[tuple[str, str]] = [
    ("SAF-T1001", "F-O1 (NEP-0004 · the permit-parameterization taint)"),
    ("SAF-T2004", "F-O7 (NEP-0006 · the data-as-code sink)"),
    ("SAF-T3009", "F-O7 composition (decode-then-trim)"),
]


def main() -> int:
    rows: dict[str, str] = {}
    for fixture in sorted(REDTEAM.glob("saf-t*-*.nika.yaml")):
        m = re.match(r"(saf-t\d+)", fixture.name, re.IGNORECASE)
        if m is None:
            continue
        rows[m.group(1).upper()] = fixture.name.removesuffix(".nika.yaml")
    lines = ["tag\tgate\tfixture_or_out_of_scope"]
    missing = 0
    for tag, gate in IN_SCOPE:
        fixture = rows.get(tag, "MISSING — no fixture, no bench, no out-of-scope row")
        if fixture.startswith("MISSING"):
            missing += 1
        lines.append(f"{tag}\t{gate}\t{fixture}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8"), end="")
    if missing:
        print(f"coverage FAIL · {missing} in-scope tag(s) without a row", file=sys.stderr)
        return 1
    print(f"coverage OK · {len(IN_SCOPE) - missing}/{len(IN_SCOPE)} in-scope tags covered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
