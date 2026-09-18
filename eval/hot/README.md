# eval/hot — compile-HOT candidate inventory

**Not** the LLM authoring harness ([`../intents.yaml`](../intents.yaml) +
`run-eval.py`). **Not** the official template registry
(`canon/templates/registry.yaml` — recount **22** on 2026-09-18).

**Scope:** a candidate corpus, not implemented Compile support or measured HOT
coverage. This revision consolidates the inventory proposed in
[PR #335](https://github.com/supernovae-st/nika-spec/pull/335) with integrity gates
and executable wiring proofs.

Owners: nika#1665 (HOT) · nika#1666 (patterns) · nika#1656 (measure).

## Law

```
HOT = known semantic structure
    + typed value binding
    + zero provider calls during COMPILE
    + Check still runs
```

A HOT compile **may** emit a workflow whose **Run** still `infer`s / `agent`s.
False HOT is worse than a safe WARM/COLD miss. Template count is not a KPI.
`PROMOTED_HOT` in `families.json` must stay **0** until compile is instrumented.

## Files

| Path | Role |
|---|---|
| `families.yaml` / `.json` | 220 **candidates**, not templates |
| `first-wave.yaml` / `.json` | 30 test targets, not promoted |
| `skeleton-audit.json` | derived audit of the 22 canon skeletons |
| `patterns.json` | private pattern contracts (no public YAML keys) |
| `goldens.json` | G01–G24, N01–N15, E01–E10 |
| `paraphrases.json` | FR/EN seeds — do not tune BM25 on held-out |
| `near-misses.json` | effect/authority traps |
| `edits.json` | locality metrics |
| `composition-fixtures.json` | assembler laws as data (not rust yet) |
| `wave1-decisions.json` | ADD / FACTOR / PATTERN / GOLDEN / REJECT |
| `proposed-skeletons/` | teaching YAML **not** in the registry |
| `validate.py` / `validate_selftest.py` | fail-closed integrity gate and mutation tests |
| `rehearsal.py` | explicit-engine, offline mock wiring proof; no classifier/HOT score |

## Wave-1 skeleton decisions (see `wave1-decisions.json`)

| Item | Verdict |
|---|---|
| lookup-and-enrich | PATTERN + proposed file, not canon tonight |
| facts-to-draft | PATTERN + proposed file |
| known-path-agent-fallback | PATTERN + proposed file |
| reconcile-and-propose | FACTOR `snapshot-diff` + GOLDEN |
| approve-and-apply | FACTOR `human-gated-ship` |
| join-records | PATTERN ONLY |
| lookup-decide-gate | GOLDEN ONLY (G05 compose) |
| notify-effect | FACTOR `gate-and-act` |
| chain as HOT family | REJECT (too generic) |

```sh
python3 eval/hot/validate.py
python3 -O eval/hot/validate_selftest.py
python3 eval/hot/rehearsal.py --engine /path/to/nika
```

The JSON files own the inventory; their YAML companions must parse to exactly
the same values, including empty lists. The integrity gate checks identities,
references, canonical skeleton digests and the three proposed workflows against
the reference static oracle. CI runs the gate and proves it rejects corrupted
data even with Python optimization enabled.

The separate rehearsal requires an explicitly selected engine. It permits only
mock models and local fixture reads. It proves exact fact preservation, literal
lookup (including quotes and backslashes), missing-data refusal, and the actual
known/unknown branch behavior. Its deterministic classifier substitution tests
wiring, not classification quality. Engine version is included in the result.

The corpus has no frozen TRAIN/DEV/HELDOUT split yet. Paraphrases and negative
cases are design seeds, not held-out measurements. No latency, HOT coverage,
classifier accuracy, or zero-provider-calls-during-compile claim follows from
these checks. No assembler exists in this repo; all candidate statuses remain
unchanged and `PROMOTED_HOT` stays zero.
