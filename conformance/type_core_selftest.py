#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Self-test of the reference type core — the lattice + lowering laws of
spec 09-types.md, pinned executable. `python3 conformance/type_core_selftest.py`
exits 0 iff every law holds (the CI gate runs it beside the runner)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from type_core import lower, parse_type, subtype  # noqa: E402

CHECKS: list[tuple[str, bool]] = []


def law(name: str, holds: bool) -> None:
    CHECKS.append((name, holds))


def t(expr, names=(), named=None):
    return parse_type(expr, set(names), "test")


N: dict = {}

# ── lattice laws ─────────────────────────────────────────────────────────
law("reflexivity · string ⊑ string", subtype(t("string"), t("string"), N))
law("integer ⊑ number (the one widening)", subtype(t("integer"), t("number"), N))
law("number ⋢ integer", not subtype(t("number"), t("integer"), N))
law("string ⋢ integer (no coercion)", not subtype(t("string"), t("integer"), N))
law("enum ⊑ string", subtype(t({"enum": ["a", "b"]}), t("string"), N))
law("enum subset ⊑", subtype(t({"enum": ["a"]}), t({"enum": ["a", "b"]}), N))
law("enum superset ⋢", not subtype(t({"enum": ["a", "c"]}), t({"enum": ["a", "b"]}), N))
law("bounded int nests", subtype(t({"integer": {"min": 1, "max": 5}}),
                                 t({"integer": {"min": 0, "max": 10}}), N))
law("bounded int escapes ⋢", not subtype(t({"integer": {"min": 0, "max": 20}}),
                                         t({"integer": {"min": 0, "max": 10}}), N))
law("bounded ⊑ bare primitive", subtype(t({"integer": {"min": 0}}), t("integer"), N))
law("uri ⊑ string (newtype narrows)", subtype(t("uri"), t("string"), N))
law("string ⋢ uri", not subtype(t("string"), t("uri"), N))
law("array covariant", subtype(t({"array": "integer"}), t({"array": "number"}), N))
law("map covariant", subtype(t({"map": {"enum": ["x"]}}), t({"map": "string"}), N))

# optional normalizes to union[T, null] — and null passes it
opt = t({"optional": "string"})
law("optional = union with null", subtype(t("null"), opt, N))
law("member ⊑ union", subtype(t("string"), opt, N))
law("union ⊑ only if every member fits",
    subtype(t({"union": ["integer", {"enum": ["a"]}]}), t({"union": ["number", "string"]}), N))
law("union with escapee ⋢",
    not subtype(t({"union": ["integer", "bytes"]}), t("number"), N))

# gradual consistency is NOT transitive — Unknown never launders
# (null ~ Unknown ~ bool · yet null ⋢ bool · spec 09 §lattice)
law("unknown never launders (null ⋢ bool despite ~Unknown~)",
    not subtype(t("null"), t("bool"), N))

# objects · width + depth + closedness
A = t({"object": {"a": "string", "b": "integer"}})
B = t({"object": {"a": "string"}})
law("closed B refuses extra field (width)", not subtype(A, B, N))
B_open = t({"object": {"a": "string"}, "additional": True})
law("additional:true admits extra field", subtype(A, B_open, N))
law("missing required field ⋢", not subtype(B, A, N))
B_opt = t({"object": {"a": "string", "b": {"optional": "integer"}}})
law("optional field may be absent", subtype(B, B_opt, N))
law("depth · field types must fit",
    not subtype(t({"object": {"a": "number"}}), t({"object": {"a": "integer"}}), N))

# normalization: union flatten + dedup + one-member collapse
law("union of one collapses", t({"union": ["string", "string"]}) == t("string"))
law("nested unions flatten",
    t({"union": [{"union": ["string", "null"]}, "integer"]})
    == t({"union": ["string", "null", "integer"]}))

# ── lowering laws (the table of 09 §lowering) ────────────────────────────
law("lower closed object sets additionalProperties:false",
    lower(t({"object": {"a": "string"}}), N).get("additionalProperties") is False)
law("lower open object omits the bar",
    "additionalProperties" not in lower(t({"object": {"a": "string"}, "additional": True}), N))
law("optional field leaves required",
    lower(t({"object": {"a": "string", "b": {"optional": "integer"}}}), N)["required"] == ["a"])
law("enum lowers to string+enum",
    lower(t({"enum": ["x", "y"]}), N) == {"type": "string", "enum": ["x", "y"]})
law("union lowers to anyOf",
    "anyOf" in lower(t({"union": ["string", "integer"]}), N))
law("bytes lowers with contentEncoding",
    lower(t("bytes"), N).get("contentEncoding") == "base64")
law("timestamp lowers with format",
    lower(t("timestamp"), N).get("format") == "date-time")
law("named ref inlines (no $ref)",
    "$ref" not in str(lower(parse_type("Summary", {"Summary"}, "t"),
                            {"Summary": t({"object": {"x": "string"}})})))

# lowering is total on the grammar (spot the tricky composites)
for expr in ("null", "bool", "integer", "number", "string", "bytes", "uri",
             "path", "duration", "money", "timestamp",
             {"array": "string"}, {"map": "integer"},
             {"object": {"a": {"optional": {"enum": ["k"]}}}},
             {"union": ["string", {"integer": {"min": 0}}]},
             {"string": {"pattern": "^x", "min_len": 1, "max_len": 9}}):
    try:
        lower(t(expr), N)
        law(f"lowering total on {expr!r}"[:60], True)
    except Exception:  # noqa: BLE001 — the law IS "never raises"
        law(f"lowering total on {expr!r}"[:60], False)

bad = [n for n, ok in CHECKS if not ok]
print(f"type-core selftest · {len(CHECKS) - len(bad)}/{len(CHECKS)} laws hold")
for n in bad:
    print(f"  ✗ {n}")
sys.exit(1 if bad else 0)
