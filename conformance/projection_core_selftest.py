#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Self-test of the reference projection surface — spec 16 laws executable."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from projection_core import (  # noqa: E402
    ProjectionError, accepts_unknown_additive_field, validate,
)

CHECKS: list[tuple[str, bool]] = []


def law(name: str, holds: bool) -> None:
    CHECKS.append((name, holds))


def refuses(doc) -> bool:
    try:
        validate(doc)
        return False
    except ProjectionError:
        return True


HEALTHY = {"semantic_document_format": 1,
           "graph": {"graph_format": 2, "workflow": "w", "tasks": [], "edges": []},
           "spans": {"a": {"start": {"line": 1, "character": 0},
                           "end": {"line": 1, "character": 1}}}}
UNBUILDABLE = {"semantic_document_format": 1, "reason": "parse", "spans": {}}

# ── the version key ─────────────────────────────────────────────────────
law("a healthy document validates", (validate(HEALTHY) or True))
law("an unbuildable document with a reason validates", (validate(UNBUILDABLE) or True))
law("a missing semantic_document_format is refused",
    refuses({"graph": {"graph_format": 2}, "spans": {}}))
law("a wrong semantic_document_format is refused",
    refuses({**HEALTHY, "semantic_document_format": 2}))
law("the surface version is distinct from the nested graph_format",
    HEALTHY["semantic_document_format"] != HEALTHY["graph"]["graph_format"])

# ── reason: present IFF graph absent ────────────────────────────────────
law("a healthy document carries NO reason key (presence is the signal)",
    refuses({**HEALTHY, "reason": "parse"}))
law("an unbuildable document MUST name a reason",
    refuses({"semantic_document_format": 1, "graph": None, "spans": {}}))
law("a reason outside the closed vocabulary is refused",
    refuses({"semantic_document_format": 1, "reason": "because", "spans": {}}))
law("both closed reasons validate",
    (validate({"semantic_document_format": 1, "reason": "parse", "spans": {}}) or True)
    and (validate({"semantic_document_format": 1, "reason": "findings", "spans": {}}) or True))

# ── spans ───────────────────────────────────────────────────────────────
law("spans must be an object",
    refuses({"semantic_document_format": 1, "reason": "parse", "spans": []}))
law("empty spans are valid",
    (validate({"semantic_document_format": 1, "reason": "parse", "spans": {}}) or True))

# ── structure-only (no secret material) ─────────────────────────────────
law("a projection leaking a secret key is refused",
    refuses({**HEALTHY, "spans": {"a": {"resolved_secret": "hunter2"}}}))
law("a projection leaking an env_value is refused",
    refuses({**HEALTHY, "graph": {"graph_format": 2, "env_value": "PROD"}}))

# ── additive forward-compat ─────────────────────────────────────────────
law("an unknown additive field is IGNORED, never rejected",
    accepts_unknown_additive_field({**HEALTHY, "holes": [{"task": "a"}]}))
law("a healthy doc with an unknown field still validates",
    (validate({**HEALTHY, "capabilities": {"experimental.nika.holes": True}}) or True))

bad = [n for n, ok in CHECKS if not ok]
print(f"projection-core selftest · {len(CHECKS) - len(bad)}/{len(CHECKS)} laws hold")
for n in bad:
    print(f"  ✗ {n}")
sys.exit(1 if bad else 0)
