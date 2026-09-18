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
| `splits.json` | TRAIN/DEVELOPMENT · HELD-OUT · ADVERSARIAL freeze at this pin; not a score |
| `paraphrases.json` | FR/EN seeds — do not tune BM25 on held-out |
| `near-misses.json` | effect/authority traps |
| `edits.json` | locality metrics |
| `composition-fixtures.json` | assembler laws as data (not rust yet) |
| `wave1-decisions.json` | ADD / FACTOR / PATTERN / GOLDEN / REJECT |
| `proposed-skeletons/` | teaching YAML **not** in the registry |
| `validate.py` / `validate_selftest.py` | fail-closed integrity gate and mutation tests |
| `rehearsal.py` | explicit-engine, offline mock wiring proof; no classifier/HOT score |
| [`complex/`](complex/README.md) | composed authoring goldens: reference workflows, near-misses that pass check, a semantic judge with negative controls, an offline behaviour rehearsal; promotes nothing |

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

`G01`–`G24`, `N01`–`N15` and `E01`–`E10` state what a compiled candidate
should mean; they carry no workflow and no judge. [`complex/`](complex/README.md)
is where twelve of those meanings become executable: a candidate is accepted or
rejected mechanically, and every assertion is shown to reject a plausible
incorrect workflow. It judges candidates, not the compiler that produced them.

```sh
python3 eval/hot/complex/judge.py
python3 -O eval/hot/complex/judge_selftest.py
python3 eval/hot/complex/behaviour.py --engine /path/to/nika
```

`splits.json` freezes TRAIN/DEVELOPMENT vs HELD-OUT vs ADVERSARIAL as of
origin/main `7722aa66b` (2026-09-18). Every id already on main and already
read that day (G01–G24, N01–N15, E01–E10, X01–X12, 220 families) is
DEVELOPMENT. HELD-OUT and ADVERSARIAL are empty lists with an explicit
reason: inventing a holdout by moving those ids would leak the research
set. Paraphrases and negative cases remain design seeds, not held-out
measurements. No latency, HOT coverage, classifier accuracy, or
zero-provider-calls-during-compile claim follows from these checks. No
assembler exists in this repo; nothing here is a compiler-generated
workflow; all candidate statuses remain unchanged and `PROMOTED_HOT`
stays zero.

The consent extension adds X13 to DEVELOPMENT and pins the revised `complex/`
tree at `8c73d7d9`; `splits.json.initial_freeze` retains the original pin and
digests. Its near-misses are adversarial in kind and already read, so they do
not enter the ADVERSARIAL scoring split. Both scoring splits remain empty,
and the integrity gate rejects overlapping membership.
