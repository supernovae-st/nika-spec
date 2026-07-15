# SPDX-License-Identifier: Apache-2.0
#
# The reference proof layer (spec 15-proof.md · W6). Stdlib-only.
#
# What this reference PINS (the meaningful, algorithm-independent part):
#   · canonical(ir) — the JCS-shaped canonical byte string (sorted keys ·
#     no spaces · raw UTF-8) · IDEMPOTENT
#   · the domain-separated pre-image (domain ‖ format_version ‖ canonical)
#     — distinct domains never share a pre-image over identical bytes
#   · semantic distinctness — different IRs → different canonical bytes
#   · assert leveling — StaticProof only where the property is statically
#     decidable · else TraceVerified or Unknown (claim ≤ evidence)
#   · nika.lock pin-by-default — an unpinned dependency is a refusal
#
# The HASH ALGORITHM (blake3, engine-side) is a pinned choice both
# evaluators share; the reference validates the PRE-IMAGE (what gets
# hashed) — a differential on the canonical bytes, never on the digest,
# so no blake3 dependency is needed here (stdlib has none).

from __future__ import annotations

import hashlib
import json

DOMAINS = ("source", "canonical", "semantic", "plan", "trace", "artifact", "receipt")
LOCK_FORMAT = 1
RECEIPT_FORMAT = 1
ASSERT_LEVELS = ("StaticProof", "TraceVerified", "Unknown")
# properties statically decidable at check (on the graph/IR)
STATIC_PROPERTIES = {"before", "bounded", "no_secret_egress"}
# properties only a completed trace can settle
TRACE_PROPERTIES = {"eventually", "resource"}


class ProofError(Exception):
    """NIKA-LOCK-001 / NIKA-ASSERT-001 — a proof-layer law is violated."""


def canonical(v) -> str:
    """The JCS-shaped canonical form (sorted keys · no spaces · raw
    UTF-8) — the one byte encoding both evaluators hash over."""
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def preimage(domain: str, format_version: int, ir) -> str:
    """domain ‖ format_version ‖ JCS(ir) — the domain-separated bytes.
    The NUL separator makes the concatenation unambiguous (a domain can
    never bleed into the version or the payload)."""
    if domain not in DOMAINS:
        raise ProofError(f"unknown hash domain {domain!r} — the set is closed {DOMAINS}")
    return f"{domain}\x00{format_version}\x00{canonical(ir)}"


def semantic_hash(ir, format_version: int = 1) -> str:
    """H_semantic pre-image digest (sha256 here · the engine pins blake3
    over the SAME pre-image — the parity is on `preimage`, not the algo)."""
    return hashlib.sha256(preimage("semantic", format_version, ir).encode("utf-8")).hexdigest()


def canonical_is_idempotent(ir) -> bool:
    once = canonical(ir)
    return canonical(json.loads(once)) == once


# ── nika.lock (pin by default) ───────────────────────────────────────────

def validate_lock(lock: dict, resolved: set[str]) -> None:
    """NIKA-LOCK-001 · every resolved dependency must be pinned by digest;
    a hand-edited digest that does not match the lock's own hash is a lie
    the check catches. `resolved` is the set of dependency refs the run
    actually resolved."""
    if lock.get("lock_format") != LOCK_FORMAT:
        raise ProofError(f"nika.lock · lock_format must be {LOCK_FORMAT}")
    pinned: set[str] = set()
    for section in ("providers", "tools", "registry"):
        block = lock.get(section)
        if not isinstance(block, dict):
            continue
        for ref, entry in block.items():
            if not (isinstance(entry, dict) and isinstance(entry.get("digest"), str)
                    and entry["digest"]):
                raise ProofError(f"nika.lock.{section}.{ref} · a digest pin is required "
                                 "(pin by default · nothing floats · NIKA-LOCK-001)")
            pinned.add(ref)
    unpinned = resolved - pinned
    if unpinned:
        raise ProofError(f"nika.lock · resolved dependencies not pinned: {sorted(unpinned)} "
                         "(NIKA-LOCK-001)")


# ── assert: leveling (claim ≤ evidence) ──────────────────────────────────

def _property_name(a) -> str:
    if isinstance(a, str):
        return a
    if isinstance(a, dict) and len(a) == 1:
        return next(iter(a))
    raise ProofError(f"assert · not a v1 property: {a!r}")


def assert_level(a, trace_available: bool) -> str:
    """The HONEST level a given assertion can be judged at right now —
    StaticProof iff statically decidable · else TraceVerified when a
    trace exists · else Unknown. Never optimistic."""
    prop = _property_name(a)
    if prop in STATIC_PROPERTIES:
        return "StaticProof"
    if prop in TRACE_PROPERTIES:
        return "TraceVerified" if trace_available else "Unknown"
    raise ProofError(f"assert · {prop!r} is not a v1 assertion property")


def check_assert_claim(a, claimed_level: str, trace_available: bool) -> None:
    """NIKA-ASSERT-001 · a claimed level the evidence cannot support is a
    refusal (a StaticProof the IR cannot decide · a mis-leveled
    obligation)."""
    if claimed_level not in ASSERT_LEVELS:
        raise ProofError(f"assert · level {claimed_level!r} not in {ASSERT_LEVELS}")
    achievable = assert_level(a, trace_available)
    rank = {"Unknown": 0, "TraceVerified": 1, "StaticProof": 2}
    if rank[claimed_level] > rank[achievable]:
        raise ProofError(
            f"assert · {_property_name(a)!r} claims {claimed_level} but the evidence "
            f"only supports {achievable} (claim ≤ evidence · NIKA-ASSERT-001)")


# ── the one receipt (fold) ───────────────────────────────────────────────

def build_receipt(certificate: dict, trace_verdict: dict, assertions: list,
                  lock_digest: str, semantic: str) -> dict:
    """receipt_format 1 · the one shape the Decision Receipt and the
    registry cert are instances of · domain-separated · Merkle-linked to
    the semantic hash it proves."""
    receipt = {
        "receipt_format": RECEIPT_FORMAT,
        "proves": semantic,           # the semantic hash this receipt is about
        "certificate": certificate,
        "trace_verdict": trace_verdict,
        "assertions": assertions,
        "lock_digest": lock_digest,
    }
    receipt["digest"] = hashlib.sha256(
        preimage("receipt", RECEIPT_FORMAT, receipt).encode("utf-8")).hexdigest()
    return receipt
