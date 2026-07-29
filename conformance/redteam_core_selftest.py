#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Self-test of the redteam leg — every seeded hostile fixture MUST be
refused by the deterministic oracle, and the refusal MUST carry the law
the fixture header names (F-P10 · a seeded attack that passes silently
is the worst verdict in the corpus).

Each `saf-tNNNN-*.nika.yaml` declares its expectation in the header:
`Expected: NIKA-XXX-NNN at CHECK`. This walks the directory, judges
every fixture with the reference pipeline (the same `validate_text`
the runner gates on), and asserts (a) the verdict is a refusal and
(b) the named code is among the findings.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from runner import load_canon, load_schema, validate_text  # noqa: E402

REDTEAM = HERE / "redteam"
EXPECTED_RE = re.compile(r"^#\s*Expected:\s*(NIKA-[A-Z]+-\d+)\s+at\s+(CHECK|RUN)\b", re.MULTILINE)


def main() -> int:
    validator = load_schema()
    canon = load_canon()
    fixtures = sorted(REDTEAM.glob("saf-t*-*.nika.yaml"))
    checks: list[tuple[str, bool, str]] = []
    if not fixtures:
        checks.append(("corpus non-empty", False, "no saf-t* fixture found"))
    for fixture in fixtures:
        text = fixture.read_text(encoding="utf-8")
        m = EXPECTED_RE.search(text)
        if m is None:
            checks.append((fixture.name, False, "no `Expected: NIKA-… at CHECK|RUN` header"))
            continue
        code, phase = m.group(1), m.group(2)
        if phase != "CHECK":
            checks.append((fixture.name, False, f"phase {phase} unsupported by this gate (CHECK only)"))
            continue
        verdict = validate_text(text, validator, canon)
        emitted = {e.get("code") for e in verdict["errors"]} - {None}
        ok = (not verdict["valid"]) and code in emitted
        detail = "refused as named" if ok else (
            "PASSED SILENTLY — the attack went through" if verdict["valid"]
            else f"refused but {code} not among {sorted(emitted)}"
        )
        checks.append((fixture.name, ok, detail))
    bad = 0
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name} · {detail}")
        bad += 0 if ok else 1
    print(f"redteam leg · {len(checks) - bad}/{len(checks)} fixtures die as named")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
