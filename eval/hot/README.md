# eval/hot — compile-HOT candidate inventory

**Not** the LLM authoring harness ([`../intents.yaml`](../intents.yaml) +
`run-eval.py`). **Not** the official template registry
(`canon/templates/registry.yaml` — recount **22** on 2026-09-18).

**Landing:** this tree ships on branch `eval/hot-candidate-inventory`
([PR #335](https://github.com/supernovae-st/nika-spec/pull/335)). Until that
PR is merged, **main has no `eval/hot/`**. Tracker text must not say the
corpus “lives on main”.

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
| `validate.py` | structural gate |

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
```

No milliseconds. No “0 provider calls” claim. No assembler in this repo.
