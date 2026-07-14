#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The reference Gateway validator (spec 12-gateway.md · W-PORT).

Stdlib-only. The gateway artifacts are DECLARATIVE contracts — this
module judges their internal coherence and their laws; enforcing them
around a live run is backend/adapter work, deliberately out of the
contract layer.

Laws implemented (spec 12):
- NIKA-PORT-001 (validation): mandatory regions · closed enums ·
  evidence required on any non-unknown capability claim
  (Strength(Claim) ≤ Strength(Evidence)) · the disclosure ⊆-chain
  (T_presented ⊆ T_discoverable ⊆ T_authorized ⊆ T_installed) ·
  child authority ⊆ parent (entry-wise, conservative) · an
  AuthorityDelta with a non-empty `gains` (import must never GAIN
  authority) · fidelity detail required on lossy/ambiguous/
  security_restricted rows
- NIKA-PORT-002 (security): a `permissive_unsafe` lowering row —
  the run is refused with the divergence witness · `unknown` rows
  are never admitted silently (refuse or declared degrade)
- admission: every bundle backend_requirement judged against the
  capabilities report — exact admits · partial/absent follow the
  requirement's on_absent {refuse · degrade_declared} · unknown is
  NEVER promoted (treated as absent)
"""

from __future__ import annotations

import json

SUPPORT = ("exact", "partial", "absent", "unknown")
GUARANTEE = ("statically_proven", "runtime_enforced", "best_effort",
             "observed", "unknown")  # G27 · ratified · never extended here
LOWERING = ("exact", "restrictive_safe", "permissive_unsafe",
            "unsupported", "unknown")
FIDELITY = ("exact", "adapted", "lossy", "unsupported", "ambiguous",
            "security_restricted")
ON_ABSENT = ("refuse", "degrade_declared")
DISCLOSURE_CHAIN = ("presented", "discoverable", "authorized", "installed")


class PortError(Exception):
    """NIKA-PORT-001 — a gateway artifact violates its laws."""


class LoweringRefusal(Exception):
    """NIKA-PORT-002 — permissive_unsafe: the backend would allow what
    the policy forbids."""


def canonical(v) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _need(d: dict, key: str, where: str):
    if key not in d:
        raise PortError(f"{where}.{key} · mandatory field missing")
    return d[key]


# ── the deployment bundle ────────────────────────────────────────────────

def validate_bundle(b: dict) -> None:
    for region in ("manifest", "lock", "authority", "contracts",
                   "backend_requirements"):
        _need(b, region, "bundle")
    man = b["manifest"]
    for k in ("id", "version", "owner"):
        if not isinstance(man.get(k), str) or not man[k]:
            raise PortError(f"manifest.{k} · required string")
    lock = b["lock"]
    if not isinstance(lock, dict) or not lock:
        raise PortError("lock · non-empty digest map (nothing resolves at run time)")
    for name, digest in lock.items():
        if not isinstance(digest, str) or not digest:
            raise PortError(f"lock.{name} · a digest string is required (pinned, never floating)")
    for i, req in enumerate(b["backend_requirements"]):
        where = f"backend_requirements[{i}]"
        cap = _need(req, "capability", where)
        if not isinstance(cap, str) or not cap:
            raise PortError(f"{where}.capability · required string")
        on_absent = _need(req, "on_absent", where)
        if on_absent not in ON_ABSENT:
            raise PortError(f"{where}.on_absent · not in {ON_ABSENT}: {on_absent}")


# ── the capabilities report ──────────────────────────────────────────────

def validate_capabilities(report: dict) -> None:
    caps = _need(report, "capabilities", "capabilities_report")
    if not isinstance(caps, dict):
        raise PortError("capabilities_report.capabilities · a map of capability → claim")
    for name, claim in caps.items():
        where = f"capabilities.{name}"
        support = _need(claim, "support", where)
        if support not in SUPPORT:
            raise PortError(f"{where}.support · not in {SUPPORT}: {support}")
        g = _need(claim, "guarantee", where)
        if g not in GUARANTEE:
            raise PortError(f"{where}.guarantee · not in the ratified G27 enum: {g}")
        if support != "unknown":
            ev = claim.get("evidence")
            if not isinstance(ev, str) or not ev:
                raise PortError(
                    f"{where}.evidence · a non-unknown claim REQUIRES evidence "
                    "(Strength(Claim) ≤ Strength(Evidence) · spec 12)")


def judge_admission(bundle: dict, report: dict) -> dict:
    """Every backend_requirement judged · unknown is NEVER promoted."""
    validate_bundle(bundle)
    validate_capabilities(report)
    caps = report["capabilities"]
    refused, degraded, admitted = [], [], []
    for req in bundle["backend_requirements"]:
        name = req["capability"]
        claim = caps.get(name)
        support = claim["support"] if claim is not None else "absent"
        if support == "unknown":
            support = "absent"  # never promoted (the honest floor)
        if support == "exact":
            admitted.append(name)
        elif req["on_absent"] == "degrade_declared":
            degraded.append({"capability": name, "support": support})
        else:
            refused.append({"capability": name, "support": support})
    verdict = "refuse" if refused else ("degrade_declared" if degraded else "admit")
    return {"verdict": verdict, "admitted": sorted(admitted),
            "degraded": degraded, "refused": refused}


# ── the lowering report ──────────────────────────────────────────────────

def validate_lowering(report: dict) -> dict:
    """Returns {verdict, witnesses} · raises LoweringRefusal on any
    permissive_unsafe row (NIKA-PORT-002)."""
    rows = _need(report, "rows", "lowering_report")
    witnesses = []
    for i, row in enumerate(rows):
        where = f"lowering_report.rows[{i}]"
        rule = _need(row, "rule", where)
        cls = _need(row, "classification", where)
        if cls not in LOWERING:
            raise PortError(f"{where}.classification · not in {LOWERING}: {cls}")
        if cls != "exact":
            w = row.get("witness")
            if not isinstance(w, str) or not w:
                raise PortError(f"{where}.witness · every non-exact row carries "
                                "its divergence witness")
            witnesses.append({"rule": rule, "classification": cls, "witness": w})
        if cls == "permissive_unsafe":
            raise LoweringRefusal(
                f"rule {rule!r} lowers permissive_unsafe — the backend would "
                f"allow what the policy forbids · witness: {row.get('witness')} "
                "(NIKA-PORT-002 · running anyway would make the file lie)")
    unknowns = [w for w in witnesses if w["classification"] == "unknown"]
    verdict = "sound_with_restrictions" if witnesses else "exact"
    if unknowns:
        verdict = "unknown_rows_present"  # caller decides refuse/degrade · never silent
    return {"verdict": verdict, "witnesses": witnesses}


# ── the import contracts ─────────────────────────────────────────────────

def validate_fidelity(report: dict) -> None:
    for i, el in enumerate(_need(report, "elements", "fidelity_report")):
        where = f"fidelity_report.elements[{i}]"
        _need(el, "name", where)
        f = _need(el, "fidelity", where)
        if f not in FIDELITY:
            raise PortError(f"{where}.fidelity · not in the 6-value enum: {f}")
        if f in ("lossy", "ambiguous", "security_restricted"):
            d = el.get("detail")
            if not isinstance(d, str) or not d:
                raise PortError(f"{where}.detail · {f} names what was lost/"
                                "ambiguous/restricted — never silent")


def validate_authority_delta(delta: dict) -> None:
    gains = _need(delta, "gains", "authority_delta")
    if gains:
        raise PortError(
            f"authority_delta.gains · import must never GAIN authority — "
            f"non-empty gains: {gains} (spec 12 §AgentRuntimeAdapter)")
    for k in ("losses", "hardenings"):
        v = _need(delta, k, "authority_delta")
        if not isinstance(v, list):
            raise PortError(f"authority_delta.{k} · a list (possibly empty · never absent)")


# ── the structural laws ──────────────────────────────────────────────────

def validate_disclosure_chain(sets: dict) -> None:
    """T_presented ⊆ T_discoverable ⊆ T_authorized ⊆ T_installed."""
    tiers = []
    for name in DISCLOSURE_CHAIN:
        v = _need(sets, name, "disclosure")
        if not isinstance(v, list):
            raise PortError(f"disclosure.{name} · a list of tool ids")
        tiers.append((name, set(v)))
    for (a_name, a), (b_name, b) in zip(tiers, tiers[1:]):
        extra = a - b
        if extra:
            raise PortError(
                f"disclosure · {a_name} ⊄ {b_name} — {sorted(extra)} "
                "(disclosure changes CONTEXT, never AUTHORITY · the chain is the law)")


def validate_child_authority(child: dict, parent: dict) -> None:
    """Authority(child) ⊆ Authority(parent) — entry-wise, conservative
    (a child entry must appear literally in the parent's grant; glob
    subsumption is approximated by exact entry equality, deliberately)."""
    for category in sorted(set(child) | set(parent)):
        c = child.get(category, [])
        p = parent.get(category, [])
        if isinstance(c, bool) or isinstance(p, bool):
            # the exec tri-state: child true needs parent true · child
            # list needs parent true or a superset list
            if c is True and p is not True:
                raise PortError(f"authority.{category} · child grants any, parent does not")
            if isinstance(c, list) and p is not True and not set(c) <= set(p if isinstance(p, list) else []):
                raise PortError(f"authority.{category} · child exceeds parent")
            continue
        if not set(c) <= set(p):
            extra = sorted(set(c) - set(p))
            raise PortError(
                f"authority.{category} · Authority(child) ⊄ Authority(parent) — "
                f"child adds {extra} (spec 12 · containment law)")
