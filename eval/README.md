# eval/ · the agent-authoring benchmark

> Measures the thesis behind the [authoring protocol](../AGENTS.md):
> **a weak model following the deterministic path beats a strong model
> improvising.** Until this runs, that sentence is a claim. After it
> runs, it is a table.

## What it does

[`intents.yaml`](intents.yaml) holds 12 plain-language jobs (two per
template family, no Nika vocabulary in the wording). For each intent ×
condition, [`run-eval.py`](run-eval.py):

1. asks the model to author the workflow —
   - **protocol** · system prompt = the protocol + the matched template
     file inline (structure instantiated, slots filled)
   - **freeform** · same model, same intent, just the envelope basics
2. validates the reply with the conformance oracle (the same one CI
   runs — schema + cross-refs + deep-static + stdlib surface),
3. on errors, feeds the exact error list back for up to 3 repair
   loops (the protocol's repair step, mechanized),
4. records first-pass validity, final validity and loops used.

```sh
# pilot (4 intents × 2 conditions · ~16-24 model calls)
python3 eval/run-eval.py --model haiku --condition both --limit 4

# full grid · then compare models
python3 eval/run-eval.py --model haiku
python3 eval/run-eval.py --model sonnet

# re-print a past run
python3 eval/run-eval.py --report eval/results/<file>.json
```

Model calls go through the `claude` CLI (`-p` print mode); swap the
call in `call_model` for any other provider CLI to benchmark engines
against each other. No CLI, no fabricated numbers — the harness exits.

## How the results feed back

Every failure names a code. Codes cluster → the cluster names the fix:

| Failure cluster | The fix lands in |
|---|---|
| same `NIKA-*` code across intents | a new hard rule in [AGENTS.md](../AGENTS.md) + the docs protocol page |
| failures concentrated in one family | that template grows a slot or a comment |
| freeform ≫ protocol on some family | the routing table gains a row (the intent didn't map) |
| repair loops not converging | the error's `detail` line gets more prescriptive |

Results land in `eval/results/*.json` (gitignored until a run is worth
keeping — a kept run is a benchmark, commit it deliberately).

🦋 *The bible evolves on data, not on taste.*
