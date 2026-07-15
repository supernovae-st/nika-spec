#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Self-test of the reference proof layer — the laws of spec 15 pinned
executable (runs beside the runner in CI)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from proof_core import (  # noqa: E402
    ProofError, assert_level, build_receipt, canonical, canonical_is_idempotent,
    check_assert_claim, preimage, semantic_hash, validate_lock,
)

CHECKS: list[tuple[str, bool]] = []


def law(name: str, holds: bool) -> None:
    CHECKS.append((name, holds))


def refuses(fn, *a) -> bool:
    try:
        fn(*a)
        return False
    except ProofError:
        return True


IR_A = {"workflow": "w", "tasks": {"a": {"verb": "exec", "cmd": ["echo", "x"]}}}
IR_B = {"workflow": "w", "tasks": {"a": {"verb": "exec", "cmd": ["echo", "y"]}}}

# ── canonical + hash ────────────────────────────────────────────────────
law("canonical is sorted-keys, no spaces",
    canonical({"b": 1, "a": 2}) == '{"a":2,"b":1}')
law("canonical is idempotent", canonical_is_idempotent(IR_A))
law("semantically-different IRs → different canonical bytes",
    canonical(IR_A) != canonical(IR_B))
law("semantically-different IRs → different semantic hash",
    semantic_hash(IR_A) != semantic_hash(IR_B))
law("the same IR → the same hash (deterministic)",
    semantic_hash(IR_A) == semantic_hash(IR_A))

# ── domain separation ───────────────────────────────────────────────────
law("domain separation: same bytes, different domain → different pre-image",
    preimage("semantic", 1, IR_A) != preimage("trace", 1, IR_A))
law("an unknown hash domain is refused",
    refuses(preimage, "made-up", 1, IR_A))
law("format_version participates in the pre-image",
    preimage("semantic", 1, IR_A) != preimage("semantic", 2, IR_A))

# ── nika.lock (pin by default) ──────────────────────────────────────────
GOOD_LOCK = {"lock_format": 1,
             "providers": {"anthropic/claude": {"digest": "blake3:aa"}},
             "tools": {"nika:fetch": {"digest": "blake3:bb"}}}
law("a fully-pinned lock validates",
    (validate_lock(GOOD_LOCK, {"anthropic/claude", "nika:fetch"}) or True))
law("an unpinned resolved dependency is refused (pin by default)",
    refuses(validate_lock, GOOD_LOCK, {"anthropic/claude", "nika:fetch", "mcp:x/y"}))
law("a digest-less lock entry is refused",
    refuses(validate_lock,
            {"lock_format": 1, "providers": {"p": {}}}, {"p"}))
law("a wrong lock_format is refused",
    refuses(validate_lock, {"lock_format": 9}, set()))

# ── assert leveling (claim ≤ evidence) ──────────────────────────────────
law("a static property levels StaticProof",
    assert_level({"before": {"first": "a", "second": "b"}}, False) == "StaticProof")
law("no_secret_egress is StaticProof",
    assert_level("no_secret_egress", False) == "StaticProof")
law("a trace property with no trace is Unknown",
    assert_level({"eventually": {"task": "t", "state": "success"}}, False) == "Unknown")
law("a trace property with a trace is TraceVerified",
    assert_level({"eventually": {"task": "t", "state": "success"}}, True) == "TraceVerified")
law("claiming StaticProof on a trace-only property is refused",
    refuses(check_assert_claim,
            {"eventually": {"task": "t", "state": "success"}}, "StaticProof", True))
law("claiming TraceVerified with no trace is refused (Unknown only)",
    refuses(check_assert_claim,
            {"resource": {"cost_usd": {"max": 5}}}, "TraceVerified", False))
law("an honest StaticProof claim is accepted",
    (check_assert_claim({"bounded": {"task": "c", "max_iterations": 100}},
                        "StaticProof", False) or True))
law("an unknown assertion property is refused",
    refuses(assert_level, {"telepathy": {}}, False))

# ── the one receipt ─────────────────────────────────────────────────────
r = build_receipt({"attempts": 1}, {"outcome": "success"},
                  [{"assert": "no_secret_egress", "level": "StaticProof"}],
                  "blake3:lock", semantic_hash(IR_A))
law("the receipt proves its semantic hash",
    r["proves"] == semantic_hash(IR_A) and r["receipt_format"] == 1)
law("the receipt is self-digesting (domain-separated)",
    isinstance(r["digest"], str) and len(r["digest"]) == 64)

bad = [n for n, ok in CHECKS if not ok]
print(f"proof-core selftest · {len(CHECKS) - len(bad)}/{len(CHECKS)} laws hold")
for n in bad:
    print(f"  ✗ {n}")
sys.exit(1 if bad else 0)
