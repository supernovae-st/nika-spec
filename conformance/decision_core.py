#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The reference Decision evaluator (spec 11-decision.md · G18).

Stdlib-only, engine-free BY DESIGN: this file is the canonical copy of
the portable interpreter a bundle owner vendors beside their bundle.
Conformance for any engine: byte-equal canonical-JSON receipts on the
bundle's own fixtures (`JSON_engine == JSON_reference`).

Laws implemented (spec 11):
- bundle self-validation (NIKA-DECIDE-001): fixed-point integers only ·
  rules read only declared evidence keys · identity keys never feed
  technical dimensions · a contradictory fixture is mandatory ·
  declared monotonicity is CHECKED against the bundle's own fixtures
- snapshot validation (NIKA-DECIDE-002): required keys · authorized
  sources · integrity floor (untrusted ⊑ observed ⊑ verified ⊑
  authoritative) · type fit via type_core (one voice with spec 09)
- Belnap {True, False, Unknown, Conflict}: Unknown ≠ False ≠ 0 ·
  authoritative×authoritative disagreement on a required key ⇒
  human_required + witness
- intervals: a missing/Unknown input contributes [lo, hi] over the
  transform's declared range, never an invented zero · robust
  dominance (inf > sup, else incomparable)
- outcomes {recommend · defer · human_required · opted_out ·
  overridden}: abstention is a successful evaluation · never_automatic
  outcomes force human_required
- the receipt: term-by-term contributions + determination provenance ·
  canonical JSON (sorted keys · no spaces · raw UTF-8)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from type_core import fits, parse_type  # noqa: E402 — one voice with spec 09

INTEGRITY = ["untrusted", "observed", "verified", "authoritative"]
COMPLETENESS = {"complete", "paginated_partial", "source_down", "permission_denied"}
OUTCOMES = {"recommend", "defer", "human_required", "opted_out", "overridden"}
TRANSFORMS = {"clamp", "linear", "bucket"}
FIXTURE_CLASSES = {"positive", "negative", "ambiguous", "contradictory", "adversarial"}


class BundleError(Exception):
    """NIKA-DECIDE-001 — the bundle violates its own laws."""


class SnapshotError(Exception):
    """NIKA-DECIDE-002 — the snapshot does not satisfy the schema."""


def canonical(v) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _int(v, where: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise BundleError(f"{where} · fixed-point law: integer basis-points only, "
                          f"never a float (spec 11 §decision IR) — got {v!r}")
    return v


# ── bundle validation (NIKA-DECIDE-001) ──────────────────────────────────

def validate_bundle(b: dict) -> None:
    for region in ("manifest", "evidence_schema", "transforms", "rules",
                   "governance", "fixtures"):
        if region not in b:
            raise BundleError(f"bundle.{region} · mandatory region missing")
    man = b["manifest"]
    for k in ("id", "version", "owner", "license"):
        if not isinstance(man.get(k), str) or not man[k]:
            raise BundleError(f"manifest.{k} · required string")
    schema = b["evidence_schema"]
    if not isinstance(schema, dict) or not schema:
        raise BundleError("evidence_schema · non-empty map of evidence keys")
    for key, decl in schema.items():
        t = decl.get("type")
        if t is None:
            raise BundleError(f"evidence_schema.{key}.type · required (a spec-09 type)")
        parse_type(t, set(), f"evidence_schema.{key}.type")
        floor = decl.get("integrity", "observed")
        if floor not in INTEGRITY:
            raise BundleError(f"evidence_schema.{key}.integrity · not in the lattice: {floor}")
    for name, tr in b["transforms"].items():
        kind = tr.get("kind")
        if kind not in TRANSFORMS:
            raise BundleError(f"transforms.{name}.kind · not a v1 transform "
                              f"(clamp · linear · bucket): {kind}")
        _int(tr.get("min", 0), f"transforms.{name}.min")
        _int(tr.get("max", 0), f"transforms.{name}.max")
        if tr["min"] > tr["max"]:
            raise BundleError(f"transforms.{name} · empty range: min > max")
        if kind == "linear":
            _int(tr.get("scale_bp", 10000), f"transforms.{name}.scale_bp")
            _int(tr.get("offset", 0), f"transforms.{name}.offset")
        if kind == "bucket":
            edges = tr.get("edges")
            values = tr.get("values")
            if not (isinstance(edges, list) and isinstance(values, list)
                    and len(values) == len(edges) + 1):
                raise BundleError(f"transforms.{name} · bucket needs edges[n] + values[n+1]")
            for e in edges:
                _int(e, f"transforms.{name}.edges[]")
            if edges != sorted(edges):
                raise BundleError(f"transforms.{name}.edges · must be sorted")
            for v in values:
                _int(v, f"transforms.{name}.values[]")
    rules = b["rules"]
    dims = rules.get("dimensions")
    if not isinstance(dims, dict) or not dims:
        raise BundleError("rules.dimensions · non-empty map")
    for dname, dim in dims.items():
        for i, term in enumerate(dim.get("terms", [])):
            where = f"rules.dimensions.{dname}.terms[{i}]"
            key = term.get("evidence")
            if key not in schema:
                raise BundleError(f"{where}.evidence · undeclared key {key!r} — rules "
                                  "read only evidence_schema keys (spec 11)")
            if schema[key].get("identity") is True:
                raise BundleError(f"{where} · identity key {key!r} feeds a technical "
                                  "dimension — identity counterfactual invariance (spec 11)")
            if term.get("transform") not in b["transforms"]:
                raise BundleError(f"{where}.transform · unknown: {term.get('transform')}")
            _int(term.get("weight_bp"), f"{where}.weight_bp")
            mono = term.get("monotonicity", "none")
            if mono not in ("increases", "decreases", "none"):
                raise BundleError(f"{where}.monotonicity · not in the closed set: {mono}")
    for th in rules.get("thresholds", []):
        if th.get("dimension") not in dims:
            raise BundleError(f"rules.thresholds · unknown dimension {th.get('dimension')!r}")
        _int(th.get("recommend_gte_bp"), "rules.thresholds[].recommend_gte_bp")
    gov = b["governance"]
    for o in gov.get("never_automatic", []):
        if o not in OUTCOMES:
            raise BundleError(f"governance.never_automatic · not an outcome: {o}")
    fixtures = b["fixtures"]
    classes = {f.get("class") for f in fixtures}
    bad = classes - FIXTURE_CLASSES
    if bad:
        raise BundleError(f"fixtures · unknown class(es): {sorted(bad)}")
    if "contradictory" not in classes:
        raise BundleError("fixtures · a CONTRADICTORY fixture is mandatory — a bundle "
                          "that cannot prove its Conflict handling is unpublishable (spec 11)")
    _check_monotonicity_on_fixtures(b)


def _check_monotonicity_on_fixtures(b: dict) -> None:
    """Declared monotonicity is property-CHECKED against the bundle's own
    fixtures: for every pair of fixtures differing on ONE monotone key
    (all else equal), the dimension score must move the declared way."""
    dims = b["rules"]["dimensions"]
    fixtures = [f for f in b["fixtures"] if f.get("class") in ("positive", "negative", "ambiguous")]
    for dname, dim in dims.items():
        for term in dim.get("terms", []):
            mono = term.get("monotonicity", "none")
            if mono == "none":
                continue
            key = term["evidence"]
            for i, fa in enumerate(fixtures):
                for fb in fixtures[i + 1:]:
                    ea, eb = fa.get("evidence", {}), fb.get("evidence", {})
                    if key not in ea or key not in eb or ea[key] == eb[key]:
                        continue
                    others_a = {k: v for k, v in ea.items() if k != key}
                    others_b = {k: v for k, v in eb.items() if k != key}
                    if others_a != others_b:
                        continue
                    sa = _dimension_point_score(b, dname, ea)
                    sb = _dimension_point_score(b, dname, eb)
                    if sa is None or sb is None:
                        continue
                    va, vb = ea[key], eb[key]
                    rising = (vb > va)
                    expect_up = (mono == "increases") == rising
                    if (sb > sa) != expect_up and sb != sa:
                        raise BundleError(
                            f"rules.dimensions.{dname} · monotonicity({key}={mono}) "
                            f"violated by the bundle's OWN fixtures "
                            f"({fa.get('name')}→{fb.get('name')}: {va}→{vb} but "
                            f"score {sa}→{sb}) — refused at publication (spec 11)")


# ── evaluation ───────────────────────────────────────────────────────────

def _apply_transform(tr: dict, v: int) -> int:
    lo, hi = tr["min"], tr["max"]
    v = max(lo, min(hi, v))
    kind = tr["kind"]
    if kind == "clamp":
        return v
    if kind == "linear":
        return (v * tr.get("scale_bp", 10000)) // 10000 + tr.get("offset", 0)
    edges = tr["edges"]
    for i, e in enumerate(edges):
        if v < e:
            return tr["values"][i]
    return tr["values"][len(edges)]


def _transform_range(tr: dict) -> tuple[int, int]:
    lo, hi = _apply_transform(tr, tr["min"]), _apply_transform(tr, tr["max"])
    return (min(lo, hi), max(lo, hi))


def _dimension_point_score(b: dict, dname: str, evidence_values: dict):
    """Point score when every term's key is present (fixture probing)."""
    total = 0
    for term in b["rules"]["dimensions"][dname].get("terms", []):
        key = term["evidence"]
        if key not in evidence_values:
            return None
        v = evidence_values[key]
        if isinstance(v, bool):
            v = 1 if v else 0
        if not isinstance(v, int):
            return None
        t = _apply_transform(b["transforms"][term["transform"]], v)
        total += t * term["weight_bp"] // 10000
    return total


def validate_snapshot(b: dict, snapshot: dict) -> list[str]:
    """NIKA-DECIDE-002 gate · returns the MISSING required keys (they are
    facts for abstention, not errors); raises on schema violations."""
    schema = b["evidence_schema"]
    present: set[str] = set()
    # EVERY item is validated — a duplicate key is two claims, both judged
    # (the Conflict detector reads them all; a dict would swallow one)
    for e in snapshot.get("evidence", []):
        key = e.get("key")
        decl = schema.get(key)
        if decl is None:
            raise SnapshotError(f"evidence.{key} · not a declared evidence key "
                                "(the schema is the closed surface · NIKA-DECIDE-002)")
        present.add(key)
        ty = parse_type(decl["type"], set(), f"evidence_schema.{key}.type")
        if not fits(e.get("value"), ty, {}):
            raise SnapshotError(f"evidence.{key} · value does not fit the declared "
                                f"type (spec 09 fit · NIKA-DECIDE-002)")
        srcs = decl.get("sources")
        if isinstance(srcs, list) and e.get("source") not in srcs:
            raise SnapshotError(f"evidence.{key} · source {e.get('source')!r} is not "
                                f"authorized (declared: {srcs})")
        floor = decl.get("integrity", "observed")
        got = e.get("integrity", "untrusted")
        if got not in INTEGRITY:
            raise SnapshotError(f"evidence.{key} · integrity {got!r} not in the lattice")
        if INTEGRITY.index(got) < INTEGRITY.index(floor):
            raise SnapshotError(f"evidence.{key} · integrity {got} below the declared "
                                f"floor {floor} (NIKA-DECIDE-002)")
    missing = [k for k, d in schema.items()
               if d.get("required", False) and k not in present]
    return sorted(missing)


def _conflicts(b: dict, snapshot: dict) -> list[dict]:
    """authoritative × authoritative disagreement on one key ⇒ Conflict."""
    by_key: dict[str, list[dict]] = {}
    for e in snapshot.get("evidence", []):
        by_key.setdefault(e["key"], []).append(e)
    out = []
    for key, items in sorted(by_key.items()):
        auth = [e for e in items if e.get("integrity") == "authoritative"]
        values = {canonical(e.get("value")) for e in auth}
        if len(values) > 1:
            out.append({
                "key": key,
                "class": "unresolved",
                "required": bool(b["evidence_schema"].get(key, {}).get("required", False)),
                "witness": [
                    {"source": e.get("source"), "value": e.get("value"),
                     "digest": e.get("digest")}
                    for e in sorted(auth, key=lambda e: str(e.get("source")))
                ],
            })
    return out


def evaluate(bundle: dict, snapshot: dict) -> dict:
    """D = Evaluate(Bundle, Snapshot) — the receipt, deterministically."""
    validate_bundle(bundle)
    missing = validate_snapshot(bundle, snapshot)
    conflicts = _conflicts(bundle, snapshot)
    items = {e["key"]: e for e in snapshot.get("evidence", [])}
    # first-wins on duplicates for scoring (conflicts are reported above)
    dims_out = {}
    determination: list[str] = []
    for dname, dim in sorted(bundle["rules"]["dimensions"].items()):
        lo_total, hi_total = 0, 0
        contributions = []
        for term in dim.get("terms", []):
            key = term["evidence"]
            tr = bundle["transforms"][term["transform"]]
            w = term["weight_bp"]
            e = items.get(key)
            v = e.get("value") if e is not None else None
            if isinstance(v, bool):
                v = 1 if v else 0
            if isinstance(v, int):
                t = _apply_transform(tr, v)
                c_lo = c_hi = t * w // 10000
                known = True
            else:
                r_lo, r_hi = _transform_range(tr)
                a, c = r_lo * w // 10000, r_hi * w // 10000
                c_lo, c_hi = min(a, c), max(a, c)
                known = False
            lo_total += c_lo
            hi_total += c_hi
            contributions.append({
                "evidence": key, "known": known,
                "contribution": {"lo": c_lo, "hi": c_hi},
                "weight_bp": w, "transform": term["transform"],
            })
        dims_out[dname] = {"interval": {"lo": lo_total, "hi": hi_total},
                           "contributions": contributions}
    # outcome — governance first, then abstention, then thresholds
    gov = bundle["governance"]
    outcome = None
    if any(c["required"] for c in conflicts):
        outcome = "human_required"
        determination.append("conflict on a required key forces human_required (Belnap · spec 11)")
    elif missing:
        outcome = "defer"
        determination.append(f"missing required evidence {missing} — abstention is a safety property")
    else:
        for th in bundle["rules"].get("thresholds", []):
            d = dims_out[th["dimension"]]["interval"]
            gate = th["recommend_gte_bp"]
            if d["lo"] >= gate:
                outcome = "recommend"
                determination.append(
                    f"dimension {th['dimension']} dominates the threshold "
                    f"(inf {d['lo']} >= {gate} bp) — robust, not point-estimated")
                break
            if d["hi"] < gate:
                continue
            outcome = "defer"
            determination.append(
                f"dimension {th['dimension']} straddles the threshold "
                f"([{d['lo']}, {d['hi']}] vs {gate} bp) — incomparable with the "
                "available evidence, never a false order")
            break
        if outcome is None:
            outcome = "defer"
            determination.append("no threshold admitted — defer")
    if outcome in set(gov.get("never_automatic", [])):
        determination.append(f"governance.never_automatic lists {outcome} — human_required")
        outcome = "human_required"
    return {
        "decision_receipt_format": 1,
        "bundle": {"id": bundle["manifest"]["id"],
                   "version": bundle["manifest"]["version"],
                   "digest": bundle["manifest"].get("digest")},
        "snapshot": {"t": snapshot.get("t"),
                     "digests": sorted(e.get("digest") for e in snapshot.get("evidence", [])
                                       if e.get("digest")),
                     "missing": missing},
        "dimensions": dims_out,
        "conflicts": conflicts,
        "outcome": outcome,
        "determination_provenance": determination,
    }


if __name__ == "__main__":
    bundle = json.loads(Path(sys.argv[1]).read_text())
    snapshot = json.loads(Path(sys.argv[2]).read_text())
    print(canonical(evaluate(bundle, snapshot)))
