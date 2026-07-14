#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Self-test of the reference type core — the laws of spec 09-types.md
(§the relations · §normalization · §lowering · §meet · §optional is
presence · §the regex dialect · the runtime fit), pinned executable.
`python3 conformance/type_core_selftest.py` exits 0 iff every law holds
(the CI gate runs it beside the runner)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from type_core import (  # noqa: E402
    NEVER, UNKNOWN, TypeError_, assignable, consistent, fits, join, lower,
    meet, parse_type, regex_dialect_violation, subtype,
)

CHECKS: list[tuple[str, bool]] = []


def law(name: str, holds: bool) -> None:
    CHECKS.append((name, holds))


def t(expr, names=()):
    return parse_type(expr, set(names), "test")


def refuses(expr, code, names=()):
    try:
        parse_type(expr, set(names), "test")
        return False
    except TypeError_ as e:
        return e.code == code


N: dict = {}

# ── ⊑ · the PARTIAL ORDER (reflexive · transitive · antisymmetric) ──────
law("⊑ reflexive · string", subtype(t("string"), t("string"), N))
law("⊑ · integer ⊑ number (the one widening)", subtype(t("integer"), t("number"), N))
law("⊑ · number ⋢ integer", not subtype(t("number"), t("integer"), N))
law("⊑ · no string→integer coercion", not subtype(t("string"), t("integer"), N))
law("⊑ · enum ⊑ string", subtype(t({"enum": ["a", "b"]}), t("string"), N))
law("⊑ · enum subset", subtype(t({"enum": ["a"]}), t({"enum": ["a", "b"]}), N))
law("⊑ · enum superset ⋢", not subtype(t({"enum": ["a", "c"]}), t({"enum": ["a", "b"]}), N))
law("⊑ · bounded int nests", subtype(t({"integer": {"min": 1, "max": 5}}),
                                     t({"integer": {"min": 0, "max": 10}}), N))
law("⊑ · bounded int escapes ⋢", not subtype(t({"integer": {"min": 0, "max": 20}}),
                                             t({"integer": {"min": 0, "max": 10}}), N))
law("⊑ · bounded ⊑ bare primitive", subtype(t({"integer": {"min": 0}}), t("integer"), N))
law("⊑ · bounded int ⊑ number-refined superset",
    subtype(t({"integer": {"min": 1, "max": 2}}), t({"number": {"min": 0, "max": 3}}), N))
law("⊑ · uri ⊑ string (newtype)", subtype(t("uri"), t("string"), N))
law("⊑ · string ⋢ uri", not subtype(t("string"), t("uri"), N))
law("⊑ · array covariant", subtype(t({"array": "integer"}), t({"array": "number"}), N))
law("⊑ · map covariant", subtype(t({"map": {"enum": ["x"]}}), t({"map": "string"}), N))

# UNKNOWN in the ORDER: comparable only to itself (antisymmetry survives)
law("⊑ · Unknown ⋢ T (order)", not subtype(UNKNOWN, t("integer"), N))
law("⊑ · T ⋢ Unknown (order)", not subtype(t("integer"), UNKNOWN, N))
law("⊑ · Unknown ⊑ Unknown", subtype(UNKNOWN, UNKNOWN, N))
# NEVER is bottom
law("⊑ · Never ⊑ everything", subtype(NEVER, t("string"), N) and subtype(NEVER, UNKNOWN, N))
law("⊑ · nothing ⊑ Never (but Never)", not subtype(t("null"), NEVER, N))

# antisymmetry probes on normalized knowns (a ⊑ b ∧ b ⊑ a ⇒ a == b)
for a_e, b_e in [("integer", "number"), ({"enum": ["a"]}, "string"),
                 ({"array": "integer"}, {"array": "number"})]:
    a_t, b_t = t(a_e), t(b_e)
    both = subtype(a_t, b_t, N) and subtype(b_t, a_t, N)
    law(f"⊑ antisymmetric on ({a_e!r},{b_e!r})", (not both) or a_t == b_t)

# ── ~ · gradual consistency (symmetric · NOT transitive) ────────────────
law("~ · Unknown ~ T", consistent(UNKNOWN, t("bool"), N) and consistent(t("bool"), UNKNOWN, N))
law("~ · reflexive", consistent(t({"array": "string"}), t({"array": "string"}), N))
law("~ · null ≁ bool (structure differs)", not consistent(t("null"), t("bool"), N))
law("~ · never launders: null~Unknown~bool yet null≁bool",
    consistent(t("null"), UNKNOWN, N) and consistent(UNKNOWN, t("bool"), N)
    and not consistent(t("null"), t("bool"), N))
law("~ · deep Unknown leaf", consistent(t({"array": "string"}),
                                        {"array": UNKNOWN}, N))

# ── ⊑~ · assignability (consistent subtyping — the judge's relation) ────
law("⊑~ · Unknown accepts both ways", assignable(UNKNOWN, t("integer"), N)
    and assignable(t("integer"), UNKNOWN, N))
law("⊑~ · subsumption rides (integer ⊑~ number)", assignable(t("integer"), t("number"), N))
law("⊑~ · never launders (null ⋢~ bool)", not assignable(t("null"), t("bool"), N))
law("⊑~ · Unknown leaf accepts",
    assignable(t({"array": "integer"}), {"array": UNKNOWN}, N))

# ── join · meet (honest three-way) ──────────────────────────────────────
law("⊔ · join is the union", subtype(t("integer"), join(t("integer"), t("string")), N))
law("⊓ · string ⊓ integer = Never (impossibility, NOT Unknown)",
    meet(t("string"), t("integer"), N) == NEVER)
law("⊓ · nested bounds intersect exactly",
    meet(t({"integer": {"min": 0, "max": 10}}), t({"integer": {"min": 5, "max": 20}}), N)
    == t({"integer": {"min": 5, "max": 10}}))
law("⊓ · disjoint bounds = Never",
    meet(t({"integer": {"min": 0, "max": 3}}), t({"integer": {"min": 5}}), N) == NEVER)
law("⊓ · enum intersection exact",
    meet(t({"enum": ["a", "b"]}), t({"enum": ["b", "c"]}), N) == t({"enum": ["b"]}))
law("⊓ · disjoint enums = Never", meet(t({"enum": ["a"]}), t({"enum": ["c"]}), N) == NEVER)
law("⊓ · Unknown ⊓ T = not-computed (None) — information ≠ impossibility",
    meet(UNKNOWN, t("string"), N) is None)
law("⊓ · subtype side returns the smaller",
    meet(t({"enum": ["a"]}), t("string"), N) == t({"enum": ["a"]}))

# ── optional is presence, not null ──────────────────────────────────────
law("optional refused OUTSIDE a field position",
    refuses({"optional": "string"}, "NIKA-TYPE-001"))
law("nullable is a union", fits(None, t({"union": ["string", "null"]}), N))
Story = t({"object": {"headline": "string",
                      "byline": {"optional": "string"},
                      "score": {"union": ["integer", "null"]}}})
law("fit · absent optional field ok", fits({"headline": "h", "score": 1}, Story, N))
law("fit · PRESENT null on optional non-nullable field refused",
    not fits({"headline": "h", "byline": None, "score": 1}, Story, N))
law("fit · present T on optional ok",
    fits({"headline": "h", "byline": "b", "score": 1}, Story, N))
law("fit · required nullable: present null ok · ABSENT refused",
    fits({"headline": "h", "score": None}, Story, N)
    and not fits({"headline": "h"}, Story, N))
law("⊑ · optional field may be absent in the subtype",
    subtype(t({"object": {"a": "string"}}),
            t({"object": {"a": "string", "b": {"optional": "integer"}}}), N))
law("⊑ · an optional a-field cannot serve a required b-slot",
    not subtype(t({"object": {"a": {"optional": "string"}}}),
                t({"object": {"a": "string"}}), N))

# ── objects · width/depth/closedness ────────────────────────────────────
A = t({"object": {"a": "string", "b": "integer"}})
B = t({"object": {"a": "string"}})
law("⊑ · closed B refuses extra field (width)", not subtype(A, B, N))
law("⊑ · additional:true admits extra", subtype(A, t({"object": {"a": "string"},
                                                      "additional": True}), N))
law("⊑ · missing required refused", not subtype(B, A, N))
law("⊑ · depth: field types must fit",
    not subtype(t({"object": {"a": "number"}}), t({"object": {"a": "integer"}}), N))

# ── normalization ───────────────────────────────────────────────────────
law("union of one collapses", t({"union": ["string", "string"]}) == t("string"))
law("nested unions flatten",
    t({"union": [{"union": ["string", "null"]}, "integer"]})
    == t({"union": ["string", "null", "integer"]}))

# ── reserved · money leaves the primitives ──────────────────────────────
law("money is reserved (W-DEC)", refuses("money", "NIKA-TYPE-001"))
law("result/artifact/secret reserved", all(refuses(r, "NIKA-TYPE-001")
                                           for r in ("result", "artifact", "secret")))

# ── the regex dialect (locked whitelist · TYPE-006) ─────────────────────
for pat in ("^abc$", "a|b", "(?:ab)+c*", "[a-z0-9_]{2,8}", r"\d+\.\d{2}",
            r"a\.b\+c", "x{3}", "x{3,}", "[^abc]"):
    law(f"regex in-dialect: {pat!r}", regex_dialect_violation(pat) is None)
for pat, why in [(r"(a)\1", "backref"), ("(?=x)a", "lookahead"),
                 ("(?<=x)a", "lookbehind"), ("(?P<n>a)", "named group"),
                 ("(?i)abc", "inline flag"), ("a*?", "lazy"),
                 (r"\bword\b", "word boundary"), (r"\p{L}+", "unicode class"),
                 (r"\x41", "hex escape"), ("a{2,1", "malformed brace"),
                 ("*a", "dangling quantifier"), ("x" * 513, "over length")]:
    law(f"regex refused ({why})", regex_dialect_violation(pat) is not None)
law("TYPE-006 at declaration",
    refuses({"string": {"pattern": r"(a)\1"}}, "NIKA-TYPE-006"))

# ── lowering ────────────────────────────────────────────────────────────
law("lower closed object bars additional",
    lower(t({"object": {"a": "string"}}), N).get("additionalProperties") is False)
law("lower open object omits the bar",
    "additionalProperties" not in lower(t({"object": {"a": "string"},
                                           "additional": True}), N))
law("optional field leaves required · lowers as lower(T), no implicit null",
    (lambda s: s["required"] == ["a"] and s["properties"]["b"] == {"type": "integer"})(
        lower(t({"object": {"a": "string", "b": {"optional": "integer"}}}), N)))
law("nullable field: anyOf carries null · field stays required",
    (lambda s: "anyOf" in s["properties"]["x"] and s["required"] == ["x"])(
        lower(t({"object": {"x": {"union": ["string", "null"]}}}), N)))
law("enum lowers", lower(t({"enum": ["x", "y"]}), N) == {"type": "string", "enum": ["x", "y"]})
law("union lowers to anyOf", "anyOf" in lower(t({"union": ["string", "integer"]}), N))
law("bytes lowers base64", lower(t("bytes"), N).get("contentEncoding") == "base64")
law("timestamp lowers date-time", lower(t("timestamp"), N).get("format") == "date-time")
law("Never lowers to the empty schema {not:{}}", lower(NEVER, N) == {"not": {}})
law("Unknown lowers to accept-anything", lower(UNKNOWN, N) == {})
law("named ref inlines (no $ref)",
    "$ref" not in str(lower(parse_type("Summary", {"Summary"}, "t"),
                            {"Summary": t({"object": {"x": "string"}})})))
for expr in ("null", "bool", "integer", "number", "string", "bytes", "uri",
             "path", "duration", "timestamp",
             {"array": "string"}, {"map": "integer"},
             {"object": {"a": {"optional": {"enum": ["k"]}}}},
             {"union": ["string", {"integer": {"min": 0}}]},
             {"string": {"pattern": "^x", "min_len": 1, "max_len": 9}}):
    try:
        lower(t(expr), N)
        law(f"lowering total on {expr!r}"[:60], True)
    except Exception:  # noqa: BLE001 — the law IS "never raises"
        law(f"lowering total on {expr!r}"[:60], False)

# ── runtime fit (the TYPE-101 judgment) ─────────────────────────────────
law("fit · value inhabits object", fits({"count": 3}, t({"object": {"count": "integer"}}), N))
law("fit · wrong member refused", not fits({"count": "x"}, t({"object": {"count": "integer"}}), N))
law("fit · closed refuses extras", not fits({"count": 3, "x": 1},
                                            t({"object": {"count": "integer"}}), N))
law("fit · additional admits", fits({"count": 3, "x": 1},
                                    t({"object": {"count": "integer"}, "additional": True}), N))
law("fit · 3.0 integer · 3.5 not", fits(3.0, t("integer"), N) and not fits(3.5, t("integer"), N))
law("fit · bool is NOT integer", not fits(True, t("integer"), N))
law("fit · enum membership", fits("hi", t({"enum": ["hi", "lo"]}), N)
    and not fits("mid", t({"enum": ["hi", "lo"]}), N))
law("fit · null needs a nullable union", fits(None, t({"union": ["string", "null"]}), N)
    and not fits(None, t("string"), N))
law("fit · array judged per element", fits(["a"], t({"array": "string"}), N)
    and not fits(["a", 1], t({"array": "string"}), N))
law("fit · Never admits nothing", not fits("x", NEVER, N) and not fits(None, NEVER, N))
law("fit · Unknown admits all", fits({"any": 1}, UNKNOWN, N))

bad = [n for n, ok in CHECKS if not ok]
print(f"type-core selftest · {len(CHECKS) - len(bad)}/{len(CHECKS)} laws hold")
for n in bad:
    print(f"  ✗ {n}")
sys.exit(1 if bad else 0)
