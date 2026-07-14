#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The type-core differential corpus — Python judges, Rust must agree.

Generates a seeded corpus of v1 type expressions and pairs, judges every
pair with the REFERENCE evaluator (conformance/type_core.py: subtype ·
consistent · assignable) and lowers every type (canonical JSON,
sorted keys) — then writes `conformance/type-corpus/corpus.jsonl`.

The Rust engine's `type_differential` test reads this file, re-parses
every expression through ITS hand-written implementation and re-judges:
any disagreement fails loudly. The two implementations never share code
or tables — a common bug would have to be born twice (spec 09 · the
second-evaluator law).

Also the MUTATION harness (`--mutate`): re-judges the corpus under nine
deliberately-broken judgments and requires every mutant to disagree with
the committed verdicts somewhere (a corpus that cannot kill a mutant is
too weak — the specification-adequacy law).

usage:
  python3 scripts/gen-type-corpus.py --write        # (re)generate + judge
  python3 scripts/gen-type-corpus.py --check        # drift gate
  python3 scripts/gen-type-corpus.py --mutate       # mutation adequacy
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "conformance"))
from type_core import (  # noqa: E402
    assignable, consistent, fits, lower, parse_type, subtype,
)

CORPUS = HERE / "conformance" / "type-corpus" / "corpus.jsonl"
N_TYPES = 400          # distinct generated type expressions
N_PAIRS = 4000         # judged pairs (≥ several thousand — the directive floor)
SEED = 20260714

PRIMS = ["null", "bool", "integer", "number", "string", "bytes", "uri",
         "path", "duration", "timestamp"]


def gen_type(rng: random.Random, depth: int = 0):
    """One random v1 type expression (raw form · optional only at fields)."""
    leaf_bias = 0.45 + 0.2 * depth
    r = rng.random()
    if depth >= 3 or r < leaf_bias:
        kind = rng.random()
        if kind < 0.5:
            return rng.choice(PRIMS)
        if kind < 0.65:
            k = rng.randint(1, 3)
            return {"enum": sorted(rng.sample(["a", "b", "c", "d", "e"], k))}
        if kind < 0.8:
            lo = rng.choice([None, rng.randint(-50, 50)])
            hi = rng.choice([None, rng.randint(-50, 50)])
            if lo is not None and hi is not None and lo > hi:
                lo, hi = hi, lo
            b = {}
            if lo is not None:
                b["min"] = lo
            if hi is not None:
                b["max"] = hi
            return {rng.choice(["integer", "number"]): b}
        b = {}
        if rng.random() < 0.5:
            b["pattern"] = rng.choice(["^x", "[a-z]+", "^a[0-9]{2}$"])
        if rng.random() < 0.5:
            b["min_len"] = rng.randint(0, 4)
        if rng.random() < 0.5:
            b["max_len"] = rng.randint(5, 30)
        return {"string": b}
    kind = rng.random()
    if kind < 0.25:
        return {"array": gen_type(rng, depth + 1)}
    if kind < 0.4:
        return {"map": gen_type(rng, depth + 1)}
    if kind < 0.7:
        fields = {}
        for i in range(rng.randint(0, 3)):
            name = f"f{i}"
            ft = gen_type(rng, depth + 1)
            if rng.random() < 0.3:
                ft = {"optional": ft}
            fields[name] = ft
        out = {"object": fields}
        if rng.random() < 0.3:
            out["additional"] = True
        return out
    members = [gen_type(rng, depth + 1) for _ in range(rng.randint(2, 3))]
    return {"union": members}


def canonical(v) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"))


# The sentinel exprs guarantee the DIRECTED pairs a random draw can miss —
# every mutation class has its witness pair here by construction. The
# `{"$unknown": true}` marker spells the internal gradual type (Unknown has
# no authorable surface — both evaluators read the marker identically).
SENTINELS = [
    "integer", "number", "string", "null", "bool", "uri", "path",
    {"$unknown": True},
    {"enum": ["a"]}, {"enum": ["a", "b"]},
    {"integer": {"min": 0, "max": 10}}, {"integer": {"min": 5, "max": 20}},
    {"object": {"a": "string"}},
    {"object": {"a": "string", "b": "integer"}},
    {"object": {"a": "string"}, "additional": True},
    {"object": {"a": {"optional": "string"}}},
    {"union": ["string", "null"]},
    {"array": "integer"}, {"array": "number"},
]


def parse_corpus_expr(e, where: str):
    if isinstance(e, dict) and e.get("$unknown") is True:
        from type_core import UNKNOWN
        return UNKNOWN
    return parse_type(e, set(), where)


def build() -> list[dict]:
    rng = random.Random(SEED)
    exprs = list(SENTINELS) + [gen_type(rng) for _ in range(N_TYPES - len(SENTINELS))]
    rows: list[dict] = []
    parsed = []
    for i, e in enumerate(exprs):
        t = parse_corpus_expr(e, f"corpus[{i}]")
        parsed.append(t)
        rows.append({"kind": "type", "i": i, "expr": e,
                     "lowered": canonical(lower(t, {}))})
    # every ORDERED sentinel pair (the mutation witnesses) …
    n_sent = len(SENTINELS)
    pair_list = [(a, b) for a in range(n_sent) for b in range(n_sent) if a != b]
    # … plus the random flood
    for _ in range(N_PAIRS - len(pair_list)):
        pair_list.append((rng.randrange(N_TYPES), rng.randrange(N_TYPES)))
    for a, b in pair_list:
        rows.append({
            "kind": "pair", "a": a, "b": b,
            "subtype": subtype(parsed[a], parsed[b], {}),
            "consistent": consistent(parsed[a], parsed[b], {}),
            "assignable": assignable(parsed[a], parsed[b], {}),
        })
    return rows


def render(rows: list[dict]) -> str:
    return "\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n"


# ── mutations (each MUST be killed by the corpus) ────────────────────────

def mutations():
    """Nine broken judgments — (name, judge(a, b) -> dict of relation
    overrides or None to keep the true verdict)."""
    def m_widening_reversed(a, b, true):
        # break integer ⊑ number by also allowing number ⊑ integer
        if a == {"prim": "number"} and b == {"prim": "integer"}:
            return {"subtype": True}
        return None

    def m_unknown_universal(a, b, true):
        # Unknown becomes a universal subtype (the laundering bug)
        if a == {"unknown": True} or b == {"unknown": True}:
            return {"subtype": True}
        return None

    def m_objects_open(a, b, true):
        # closed objects forget their width bar
        if "object" in a and "object" in b and not b.get("additional"):
            wide = dict(b)
            wide["additional"] = True
            return {"subtype": subtype(a, wide, {})}
        return None

    def m_optional_is_nullable(a, b, true):
        # optional fields judged as required-but-nullable
        def rewrite(t):
            if "object" in t:
                return {"object": {k: {"ty": ({"union": sorted([f["ty"], {"prim": "null"}], key=repr)}
                                              if f["opt"] else f["ty"]),
                                       "opt": False}
                                   for k, f in t["object"].items()},
                        **({"additional": True} if t.get("additional") else {})}
            return t
        if "object" in a or "object" in b:
            return {"subtype": subtype(rewrite(a), rewrite(b), {})}
        return None

    def m_enum_superset(a, b, true):
        if "enum" in a and "enum" in b:
            return {"subtype": set(a["enum"]) >= set(b["enum"])}
        return None

    def m_bounds_reversed(a, b, true):
        if a.get("refined") in ("integer", "number") and b.get("refined") == a.get("refined"):
            ab, bb = a["bounds"], b["bounds"]
            lo = "min" not in bb or ("min" in ab and ab["min"] <= bb["min"])
            hi = "max" not in bb or ("max" in ab and ab["max"] >= bb["max"])
            return {"subtype": lo and hi}
        return None

    def m_union_any_member(a, b, true):
        # union ⊑ b judged by ANY member instead of ALL
        if "union" in a:
            return {"subtype": any(subtype(m, b, {}) for m in a["union"])}
        return None

    def m_newtype_bidirectional(a, b, true):
        # string ⊑ uri (the newtype narrowing reversed)
        if a == {"prim": "string"} and b.get("prim") in ("uri", "path", "duration", "timestamp"):
            return {"subtype": True}
        return None

    def m_consistency_transitive(a, b, true):
        # consistency judged as assignability (subsumption leaks into ~)
        return {"consistent": assignable(a, b, {})}

    return [
        ("widening_reversed", m_widening_reversed),
        ("unknown_universal_subtype", m_unknown_universal),
        ("objects_open_by_default", m_objects_open),
        ("optional_confused_with_nullable", m_optional_is_nullable),
        ("enum_superset_accepted", m_enum_superset),
        ("numeric_bounds_reversed", m_bounds_reversed),
        ("union_any_member", m_union_any_member),
        ("newtype_bidirectional", m_newtype_bidirectional),
        ("consistency_gains_subsumption", m_consistency_transitive),
    ]


def run_mutations() -> int:
    rows = build()
    types = {r["i"]: parse_corpus_expr(r["expr"], "m") for r in rows if r["kind"] == "type"}
    pairs = [r for r in rows if r["kind"] == "pair"]
    failures = []
    for name, mutant in mutations():
        killed = False
        for p in pairs:
            override = mutant(types[p["a"]], types[p["b"]], p)
            if override is None:
                continue
            for rel, verdict in override.items():
                if verdict != p[rel]:
                    killed = True
                    break
            if killed:
                break
        print(f"  {'KILLED' if killed else 'SURVIVED'} · {name}")
        if not killed:
            failures.append(name)
    print(f"mutation adequacy: {len(mutations()) - len(failures)}/{len(mutations())} killed")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--mutate", action="store_true")
    args = ap.parse_args()
    if args.mutate:
        return run_mutations()
    rendered = render(build())
    if args.write:
        CORPUS.parent.mkdir(parents=True, exist_ok=True)
        CORPUS.write_text(rendered)
        n_types = sum(1 for line in rendered.splitlines() if '"kind": "type"' in line or '"kind":"type"' in line)
        print(f"corpus: {N_TYPES} types · {N_PAIRS} judged pairs → {CORPUS.relative_to(HERE)}")
        return 0
    if not CORPUS.is_file() or CORPUS.read_text() != rendered:
        print("type-corpus DRIFT — run scripts/gen-type-corpus.py --write", file=sys.stderr)
        return 1
    print("type-corpus in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
