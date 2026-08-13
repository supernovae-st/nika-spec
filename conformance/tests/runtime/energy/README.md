# Energy reading contracts · LIVE (engine-consumed)

The reading half of [07 §the spend-honesty law](../../../spec/07-conformance.md):
a workflow (`input.yaml`) plus the `energy` block a conformant engine
MUST report for it. The static gate ignores this tier (it asserts no
`valid`/`errors`); the executable proof is `nika check <file> --json`,
whose `energy` key carries the reading **structurally** — counts, the
per-scope subtotals, and one row per task that earned a ceiling.

## Contract shape

```
tests/runtime/energy/<NNN-name>/
├── input.yaml             the workflow
└── expected-energy.json   the `energy` block of `nika check --json`, plus a `note`
```

Everything but `note` is compared as data. The rung's rendered TEXT is
the engine's ergonomics; what is normative is the reading underneath it.

## What the pair holds

- **`001`** — the three fates of a task in one workflow. A ceiling exists
  only where BOTH a cap and a sourced rate do, and that row carries the
  three axes (`provenance` · `scope` · `measured_at`) without which two
  honest numbers are incomparable. An uncapped task is COUNTED here and
  NAMED at COST — once, not once per rung. A model with no sourced rate
  is `unpriced`, never a zero.
- **`002`** — a proven zero is not an unknown. A `for_each` over a
  literal EMPTY list provably never runs, so the task is counted
  `never_runs` and gets **no row**; a ceiling over it would be invented.

## Reproducing, and the envelope caveat

These inputs carry the corpus envelope (`nika: <id>`). The shipped
0.108.0 still requires the pre-freeze form, so a probe must rewrite the
identity line — and only that line, which cannot reach a computation
that reads tasks, models and caps. See `conformance/FINDINGS.md` F-3 for
why the corpus is ahead of the binary; both go green together when the
envelope window lands.

A green here is only worth what it discriminates: measured 2026-08-13,
`002` with its `for_each` made non-empty reports `never_runs: 0` and two
rows instead of one, so the fixture falls — it judges its subject.
