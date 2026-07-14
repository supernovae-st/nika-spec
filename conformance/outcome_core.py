#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The reference Outcome judge (spec 13-outcomes.md · W5 · G12).

Stdlib + PyYAML (the runner's existing dependency). THE transition
table lives in canon.yaml (`outcome_transitions`) — this module loads
it and judges: any (class, cause) pair outside the table is an engine
bug, never a state; the payload law is per class.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_CANON = yaml.safe_load((Path(__file__).parent.parent / "canon.yaml").read_text())
TABLE = _CANON["outcome_transitions"]
CLASSES = tuple(TABLE["classes"])
LEGAL = {k: tuple(v) for k, v in TABLE["legal"].items()}
PAYLOAD = {k: tuple(v) for k, v in TABLE["payload"].items()}
TRACE_FORMAT = TABLE["trace_format"]


class OutcomeError(Exception):
    """An outcome outside the normative table — an engine bug, never a state."""


def validate_outcome(outcome: dict) -> None:
    cls = outcome.get("class")
    if cls not in CLASSES:
        raise OutcomeError(f"class {cls!r} · not a terminal class {CLASSES}")
    cause = outcome.get("cause")
    if cause not in LEGAL[cls]:
        raise OutcomeError(
            f"({cls}, {cause}) · outside the normative table — legal causes "
            f"for {cls}: {LEGAL[cls]} (spec 13 · an engine bug, never a state)")
    payload = outcome.get("payload", {})
    allowed = {f.rstrip("?") for f in PAYLOAD[cls]}
    required = {f for f in PAYLOAD[cls] if not f.endswith("?")}
    extra = set(payload) - allowed
    if extra:
        raise OutcomeError(
            f"({cls}, {cause}) · payload carries undeclared field(s) {sorted(extra)} "
            "— a new fact is a new CAUSE row, never a field beside the record")
    missing = required - set(payload)
    if missing:
        raise OutcomeError(f"({cls}, {cause}) · payload missing required {sorted(missing)}")
    # per-row laws
    if cls == "success" and cause == "recovered" and "recovered_from" not in payload:
        raise OutcomeError("success(recovered) · recovered_from (the original error) is required")
    if cls == "success" and cause == "normal" and "recovered_from" in payload:
        raise OutcomeError("success(normal) · recovered_from must be absent")
    if cls == "skipped":
        if cause == "error_skip" and "error" not in payload:
            raise OutcomeError("skipped(error_skip) · the PRESERVED error is required")
        if cause == "gate" and payload.get("error") is not None:
            raise OutcomeError("skipped(gate) · a decision-skip's error reads defined-null")
    if "attempts" in payload:
        a = payload["attempts"]
        if isinstance(a, bool) or not isinstance(a, int) or a < 1:
            raise OutcomeError("attempts · a positive integer counting every attempt")
