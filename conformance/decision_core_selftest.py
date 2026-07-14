#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Self-test of the reference Decision evaluator — the laws of spec
11-decision.md pinned executable (runs beside the runner in CI)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from decision_core import (  # noqa: E402
    BundleError, SnapshotError, canonical, evaluate, validate_bundle,
)

G = Path(__file__).parent / "decision-goldens"
BUNDLE = json.loads((G / "pr-triage.bundle.json").read_text())
CHECKS: list[tuple[str, bool]] = []


def law(name: str, holds: bool) -> None:
    CHECKS.append((name, holds))


def refuses_bundle(mutate) -> bool:
    b = copy.deepcopy(BUNDLE)
    mutate(b)
    try:
        validate_bundle(b)
        return False
    except BundleError:
        return True


def snap(*evidence):
    return {"t": "2026-07-14T20:00:00Z", "evidence": list(evidence)}


def ev(key, value, source="ci", integrity="verified", digest="d"):
    return {"key": key, "value": value, "source": source,
            "observed_at": "2026-07-14T20:00:00Z", "digest": digest,
            "confidentiality": "internal", "integrity": integrity,
            "quality": {"freshness": "fresh", "completeness": "complete",
                        "independence_group": source}}


# ── golden byte-equality (the G18 proof shape · reference side) ─────────
for name in ("s1-dominant-risk", "s2-missing-required", "s3-straddle",
             "s4-conflict", "s5-cold"):
    got = canonical(evaluate(BUNDLE, json.loads((G / f"{name}.snapshot.json").read_text())))
    want = (G / f"{name}.receipt.golden.json").read_text().strip()
    law(f"golden byte-equal · {name}", got == want)

# ── determinism: same inputs, same bytes, twice ─────────────────────────
s1 = json.loads((G / "s1-dominant-risk.snapshot.json").read_text())
law("determinism · two runs byte-equal",
    canonical(evaluate(BUNDLE, s1)) == canonical(evaluate(BUNDLE, s1)))

# ── bundle laws (NIKA-DECIDE-001) ───────────────────────────────────────
law("fixed-point · float weight refused",
    refuses_bundle(lambda b: b["rules"]["dimensions"]["change_risk"]["terms"][0]
                   .__setitem__("weight_bp", 0.5)))
law("closed rules · undeclared evidence key refused",
    refuses_bundle(lambda b: b["rules"]["dimensions"]["change_risk"]["terms"][0]
                   .__setitem__("evidence", "ghost_key")))
law("identity invariance · identity key in a technical dimension refused",
    refuses_bundle(lambda b: b["rules"]["dimensions"]["change_risk"]["terms"]
                   .append({"evidence": "author_tenure_days", "transform": "checks_0_10",
                            "weight_bp": 100, "monotonicity": "none"})))
law("contradictory fixture mandatory",
    refuses_bundle(lambda b: b.__setitem__(
        "fixtures", [f for f in b["fixtures"] if f["class"] != "contradictory"])))
law("monotonicity checked on the bundle's own fixtures",
    refuses_bundle(lambda b: b["rules"]["dimensions"]["change_risk"]["terms"][0]
                   .__setitem__("monotonicity", "decreases")))
law("bucket edges must be sorted",
    refuses_bundle(lambda b: b["transforms"]["release_step"].__setitem__("edges", [1, 0])))

# ── snapshot laws (NIKA-DECIDE-002) ─────────────────────────────────────
def refuses_snapshot(s) -> bool:
    try:
        evaluate(BUNDLE, s)
        return False
    except SnapshotError:
        return True

law("type fit · a string where integer is declared refused",
    refuses_snapshot(snap(ev("failed_required_checks", "eight"),
                          ev("touches_release_workflow", False))))
law("unauthorized source refused",
    refuses_snapshot(snap(ev("failed_required_checks", 1, source="random-blog"),
                          ev("touches_release_workflow", False))))
law("integrity floor · observed below verified refused",
    refuses_snapshot(snap(ev("failed_required_checks", 1, integrity="observed"),
                          ev("touches_release_workflow", False))))
law("undeclared evidence key refused",
    refuses_snapshot(snap(ev("failed_required_checks", 1),
                          ev("touches_release_workflow", False),
                          ev("ghost", 1))))

# ── Belnap + abstention + governance ────────────────────────────────────
r = evaluate(BUNDLE, snap(ev("failed_required_checks", 2, integrity="authoritative"),
                          ev("failed_required_checks", 7, source="audit-bot",
                             integrity="authoritative", digest="d9"),
                          ev("touches_release_workflow", False)))
law("Belnap · authoritative conflict on required ⇒ human_required",
    r["outcome"] == "human_required")
law("Belnap · the witness carries both sources",
    len(r["conflicts"][0]["witness"]) == 2)

r = evaluate(BUNDLE, snap(ev("touches_release_workflow", True)))
law("Unknown ≠ 0 · missing required ⇒ defer (never a zero-filled score)",
    r["outcome"] == "defer" and "failed_required_checks" in r["snapshot"]["missing"])

r = evaluate(BUNDLE, snap(ev("failed_required_checks", 4),
                          ev("touches_release_workflow", False)))
law("intervals · unknown optional straddles ⇒ incomparable ⇒ defer",
    r["outcome"] == "defer"
    and r["dimensions"]["evidence_quality"]["interval"]["lo"]
    != r["dimensions"]["evidence_quality"]["interval"]["hi"])

r = evaluate(BUNDLE, snap(ev("failed_required_checks", 9),
                          ev("touches_release_workflow", True),
                          ev("relevant_coverage_bp", 1000, source="coverage-bot",
                             integrity="observed")))
law("governance · never_automatic(recommend) forces human_required",
    r["outcome"] == "human_required"
    and any("never_automatic" in d for d in r["determination_provenance"]))

# ── receipt shape ───────────────────────────────────────────────────────
law("receipt · contributions are term-by-term",
    all(c.get("contribution") is not None
        for d in r["dimensions"].values() for c in d["contributions"]))
law("receipt · determination provenance is non-empty",
    bool(r["determination_provenance"]))

bad = [n for n, ok in CHECKS if not ok]
print(f"decision-core selftest · {len(CHECKS) - len(bad)}/{len(CHECKS)} laws hold")
for n in bad:
    print(f"  ✗ {n}")
sys.exit(1 if bad else 0)
