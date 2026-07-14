#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Self-test of the reference Outcome judge — the spec-13 table pinned
executable (runs beside the runner in CI)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from outcome_core import CLASSES, LEGAL, OutcomeError, validate_outcome  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def law(name: str, holds: bool) -> None:
    CHECKS.append((name, holds))


def ok(o) -> bool:
    try:
        validate_outcome(o)
        return True
    except OutcomeError:
        return False


# ── every legal (class, cause) row admits with its minimal payload ─────
MINIMAL = {
    ("success", "normal"): {"value": 42, "attempts": 1},
    ("success", "recovered"): {"value": 42, "attempts": 2,
                               "recovered_from": {"code": "NIKA-EXEC-001"}},
    ("failure", "verb_error"): {"error": {"code": "NIKA-EXEC-001"}, "attempts": 1},
    ("failure", "timeout"): {"error": {"code": "NIKA-TIMEOUT-001"}, "attempts": 1},
    ("failure", "retry_exhausted"): {"error": {"code": "NIKA-EXEC-001"}, "attempts": 3},
    ("skipped", "gate"): {},
    ("skipped", "error_skip"): {"error": {"code": "NIKA-TYPE-101"}},
    ("cancelled", "upstream"): {"reason": "upstream"},
    ("cancelled", "operator"): {"reason": "operator"},
    ("cancelled", "budget"): {"reason": "budget"},
}
total_rows = sum(len(v) for v in LEGAL.values())
law(f"the table has exactly {total_rows} rows and every one admits",
    all(ok({"class": c, "cause": k, "payload": p}) for (c, k), p in MINIMAL.items())
    and len(MINIMAL) == total_rows)

# ── every ILLEGAL pair refuses (the full complement) ────────────────────
all_causes = sorted({k for v in LEGAL.values() for k in v})
illegal_refused = all(
    not ok({"class": c, "cause": k, "payload": {}})
    for c in CLASSES for k in all_causes if k not in LEGAL[c])
law("every (class, cause) outside the table refuses — a bug, never a state",
    illegal_refused)

# ── the per-row laws ────────────────────────────────────────────────────
law("success(recovered) requires recovered_from",
    not ok({"class": "success", "cause": "recovered",
            "payload": {"value": 1, "attempts": 2}}))
law("success(normal) forbids recovered_from",
    not ok({"class": "success", "cause": "normal",
            "payload": {"value": 1, "attempts": 1, "recovered_from": {}}}))
law("skipped(error_skip) requires the PRESERVED error",
    not ok({"class": "skipped", "cause": "error_skip", "payload": {}}))
law("skipped(gate) forbids a non-null error (defined-null law)",
    not ok({"class": "skipped", "cause": "gate",
            "payload": {"error": {"code": "X"}}}))
law("an undeclared payload field refuses (a new fact is a new CAUSE row)",
    not ok({"class": "failure", "cause": "timeout",
            "payload": {"error": {}, "attempts": 1, "was_flaky": True}}))
law("attempts must be a positive integer",
    not ok({"class": "failure", "cause": "verb_error",
            "payload": {"error": {}, "attempts": 0}}))
law("an unknown class refuses",
    not ok({"class": "paused", "cause": "normal", "payload": {}}))

bad = [n for n, okk in CHECKS if not okk]
print(f"outcome-core selftest · {len(CHECKS) - len(bad)}/{len(CHECKS)} laws hold")
for n in bad:
    print(f"  ✗ {n}")
sys.exit(1 if bad else 0)
