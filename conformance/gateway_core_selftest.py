#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Self-test of the reference Gateway validator — the laws of spec
12-gateway.md pinned executable (runs beside the runner in CI)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gateway_core import (  # noqa: E402
    LoweringRefusal, PortError, judge_admission, validate_authority_delta,
    validate_bundle, validate_capabilities, validate_child_authority,
    validate_disclosure_chain, validate_fidelity, validate_lowering,
)

CHECKS: list[tuple[str, bool]] = []


def law(name: str, holds: bool) -> None:
    CHECKS.append((name, holds))


BUNDLE = {
    "manifest": {"id": "site-audit", "version": "1.0.0", "owner": "acme"},
    "lock": {"spec": "6586e5f72", "nika:fetch": "blake3:aa", "provider-catalog": "blake3:bb"},
    "authority": {"permits": {"net": {"http": ["api.example.com"]}}},
    "contracts": {"main": {"inputs": {}, "outputs": {}}},
    "backend_requirements": [
        {"capability": "net.host_allowlist", "on_absent": "refuse"},
        {"capability": "fs.path_confinement", "on_absent": "degrade_declared"},
    ],
}

CAPS = {
    "capabilities": {
        "net.host_allowlist": {"support": "exact", "guarantee": "runtime_enforced",
                                "scope": "all outbound", "assumptions": "proxy on",
                                "evidence": "probe 2026-07-14: unlisted host refused"},
        "fs.path_confinement": {"support": "partial", "guarantee": "best_effort",
                                 "scope": "reads only", "assumptions": "",
                                 "evidence": "doc pin at backend tag"},
    }
}


def refuses(exc, fn, *args) -> bool:
    try:
        fn(*copy.deepcopy(list(args)))
        return False
    except exc:
        return True


# ── bundle laws ─────────────────────────────────────────────────────────
law("bundle · the golden validates", (validate_bundle(BUNDLE) or True))
b = copy.deepcopy(BUNDLE); del b["lock"]
law("bundle · missing region refused", refuses(PortError, validate_bundle, b))
b = copy.deepcopy(BUNDLE); b["lock"]["floating"] = ""
law("bundle · an empty digest refused (pinned, never floating)",
    refuses(PortError, validate_bundle, b))
b = copy.deepcopy(BUNDLE); b["backend_requirements"][0]["on_absent"] = "ignore"
law("bundle · on_absent outside the closed set refused",
    refuses(PortError, validate_bundle, b))

# ── capabilities: claim ≤ evidence ──────────────────────────────────────
law("capabilities · the golden validates", (validate_capabilities(CAPS) or True))
c = copy.deepcopy(CAPS); del c["capabilities"]["net.host_allowlist"]["evidence"]
law("capabilities · a non-unknown claim without evidence refused",
    refuses(PortError, validate_capabilities, c))
c = copy.deepcopy(CAPS)
c["capabilities"]["net.host_allowlist"]["guarantee"] = "attested"
law("capabilities · a guarantee outside ratified G27 refused",
    refuses(PortError, validate_capabilities, c))
c = copy.deepcopy(CAPS)
c["capabilities"]["x"] = {"support": "unknown", "guarantee": "unknown"}
law("capabilities · an unknown claim needs NO evidence (honesty is free)",
    (validate_capabilities(c) or True))

# ── admission: unknown never promoted ───────────────────────────────────
v = judge_admission(BUNDLE, CAPS)
law("admission · partial + degrade_declared ⇒ degraded, listed",
    v["verdict"] == "degrade_declared"
    and v["degraded"][0]["capability"] == "fs.path_confinement")
c = copy.deepcopy(CAPS)
c["capabilities"]["net.host_allowlist"]["support"] = "unknown"
v = judge_admission(BUNDLE, c)
law("admission · unknown is NEVER promoted (treated absent ⇒ refuse)",
    v["verdict"] == "refuse" and v["refused"][0]["capability"] == "net.host_allowlist")

# ── lowering: permissive_unsafe refuses ─────────────────────────────────
ok_report = {"rows": [
    {"rule": "forbid.exec_after", "classification": "exact"},
    {"rule": "net.http", "classification": "restrictive_safe",
     "witness": "backend blocks all subdomains, policy allowed *.example.com"},
]}
v = validate_lowering(ok_report)
law("lowering · restrictive_safe is sound and witnessed",
    v["verdict"] == "sound_with_restrictions" and len(v["witnesses"]) == 1)
bad = {"rows": [{"rule": "fs.write", "classification": "permissive_unsafe",
                  "witness": "backend cannot confine writes under ./out"}]}
law("lowering · permissive_unsafe REFUSES (PORT-002 · the file would lie)",
    refuses(LoweringRefusal, validate_lowering, bad))
now = {"rows": [{"rule": "x", "classification": "lossy"}]}
law("lowering · classification outside the 5-value enum refused",
    refuses(PortError, validate_lowering, now))
now = {"rows": [{"rule": "x", "classification": "restrictive_safe"}]}
law("lowering · a non-exact row without witness refused",
    refuses(PortError, validate_lowering, now))
unk = {"rows": [{"rule": "x", "classification": "unknown", "witness": "no probe exists"}]}
law("lowering · unknown rows surface in the verdict (never silent)",
    validate_lowering(unk)["verdict"] == "unknown_rows_present")

# ── fidelity + authority delta ──────────────────────────────────────────
law("fidelity · lossy without detail refused",
    refuses(PortError, validate_fidelity,
            {"elements": [{"name": "hook", "fidelity": "lossy"}]}))
law("fidelity · the 6-value enum is closed",
    refuses(PortError, validate_fidelity,
            {"elements": [{"name": "x", "fidelity": "partial"}]}))
law("authority delta · non-empty gains refused (import never GAINS)",
    refuses(PortError, validate_authority_delta,
            {"gains": ["ambient env"], "losses": [], "hardenings": []}))
law("authority delta · losses+hardenings listed, gains empty = valid",
    (validate_authority_delta({"gains": [], "losses": ["ambient credentials"],
                               "hardenings": ["prompt-only delegation → preference"]}) or True))

# ── the structural laws ─────────────────────────────────────────────────
law("disclosure · the ⊆-chain holds on nested sets",
    (validate_disclosure_chain({"presented": ["a"], "discoverable": ["a", "b"],
                                "authorized": ["a", "b"], "installed": ["a", "b", "c"]}) or True))
law("disclosure · presented ⊄ discoverable refused",
    refuses(PortError, validate_disclosure_chain,
            {"presented": ["ghost"], "discoverable": [], "authorized": [], "installed": []}))
law("child authority · a child adding a host refused",
    refuses(PortError, validate_child_authority,
            {"net.http": ["evil.com"]}, {"net.http": ["api.example.com"]}))
law("child authority · exec: child true under parent list refused",
    refuses(PortError, validate_child_authority, {"exec": True}, {"exec": ["git"]}))
law("child authority · literal subset admits",
    (validate_child_authority({"net.http": ["api.example.com"]},
                              {"net.http": ["api.example.com", "cdn.example.com"]}) or True))

bad_names = [n for n, ok in CHECKS if not ok]
print(f"gateway-core selftest · {len(CHECKS) - len(bad_names)}/{len(CHECKS)} laws hold")
for n in bad_names:
    print(f"  ✗ {n}")
sys.exit(1 if bad_names else 0)
