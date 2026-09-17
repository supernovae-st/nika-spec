#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Structural gate for eval/hot/families.json — not a compiler quality score."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATUSES = {
    "CANDIDATE",
    "COVERED",
    "FACTORABLE",
    "NEEDS_PATTERN",
    "READY_FOR_HOT_TEST",
    "PROMOTED_HOT",
    "REJECTED_FOR_HOT",
    "OPEN_WORLD",
    "NEEDS_WARM",
    "NEEDS_COLD",
}
REQUIRED = {
    "family_id",
    "domain",
    "title",
    "example_intent",
    "structure_signature",
    "patterns",
    "bindings",
    "effects",
    "authority_class",
    "promotion_status",
    "proposed_path",
}


def main() -> int:
    data = json.loads((ROOT / "families.json").read_text())
    fams = data["families"]
    ids = [f["family_id"] for f in fams]
    assert len(ids) == len(set(ids)), "duplicate family_id"
    assert len(fams) >= 100, f"inventory too small: {len(fams)}"
    promoted = [f for f in fams if f["promotion_status"] == "PROMOTED_HOT"]
    assert promoted == [], "inventory must not claim PROMOTED_HOT without #1656 evidence"
    for f in fams:
        missing = REQUIRED - f.keys()
        assert not missing, f"{f.get('family_id')}: missing {missing}"
        assert f["promotion_status"] in STATUSES, f["family_id"]
        # provider-specific explosion check
        title = f["title"].lower()
        assert "gmail-to-slack" not in title
        assert "outlook-to-teams" not in title
    print(
        json.dumps(
            {
                "family_count": len(fams),
                "status": dict(Counter(f["promotion_status"] for f in fams)),
                "promoted_hot": 0,
                "skeleton_recount_declared": data.get("skeleton_recount"),
            },
            indent=2,
        )
    )
    # extra inventories
    for extra in ("skeleton-audit.json","patterns.json","goldens.json","wave1-decisions.json"):
        fp = ROOT / extra
        assert fp.exists(), extra
        json.loads(fp.read_text())
    audit = json.loads((ROOT / "skeleton-audit.json").read_text())
    assert audit["skeleton_count"] == 22, audit["skeleton_count"]
    g = json.loads((ROOT / "goldens.json").read_text())
    assert len(g["positive"]) >= 24
    assert len(g["negative"]) >= 15
    assert len(g["edits"]) >= 10
    return 0


if __name__ == "__main__":
    sys.exit(main())
