# Runtime behavioral fixtures · RESERVED (post-announce)

This tier holds the **execution-half** fixtures — they require a running
engine and land with the reference engine's vertical slice
([07 §suite status](../../../spec/07-conformance.md#suite-status--v01-honest)).
Until then this directory carries the CONTRACT (shapes · no inputs the
static runner would pick up — `runner.py all` globs `input.yaml`, these
fixtures use `input.nika.yaml` + `run.json` precisely so the static gate
ignores them).

## Fixture shape (behavioral)

```
tests/runtime/<area>/<NNN-name>/
├── input.nika.yaml     the workflow · model: mock/echo (deterministic)
├── run.json            invocation · {"vars": {...}, "inputs": {...}, "env": {...}}
│                       (vars + inputs both thread through `--var` — the
│                        flag sets a workflow `inputs:` value · env
│                        overlays the engine's process environment)
└── expected-run.json   the assertion · see below
```

`expected-run.json` asserts on the RUN REPORT (not stdout) ·

```json
{
  "workflow_state": "success | failure | cancelled",
  "tasks": {
    "<id>": {
      "status": "success | failure | skipped | cancelled",
      "output": "<exact value>",          // optional · exact match
      "output_contains": "<substring>",   // optional · weaker assert
      "error_code": "NIKA-…",             // optional · when status=failure
      "attempts": 1                       // optional · the outcome payload's retry count (task_completed/failed carry it · task_skipped does not)
    }
  },
  "events_include": ["task.started:<id>", "task.skipped:<id>"]   // optional · order-free
}
```

Determinism rules · `mock/echo` only — its output is
`mock(echo) · <prompt>` (the marker is PART of the contract: synthetic
output never masquerades as real content, and the spec's own examples
teach the same format — retuned 2026-07-30 from the aspirational
"prompt-verbatim" this parenthetical used to claim; the `nika:done`
`result:` path stays unprefixed, it carries an authored value) ·
schema → shaped defaults · no network (fetch fixtures use the engine's
HTTP mock · post-announce) · no wall-clock asserts (durations are
reported · never asserted).

## The five areas (one per execution contract)

| Area | First fixtures (the contracts rounds 1-7 locked) |
|---|---|
| `gates/` | default gate cancels on upstream failure · explicit `when:` evaluates over terminal deps · `when: true` runs in a failing workflow (the always-pattern) |
| `for-each/` | per-iteration timeout · null placeholder at a failed index (zip alignment) · empty collection → skipped |
| `errors/` | retry honors transient-only (the non-transient half is `004-retry-never-on-non-transient` — attempts stays 1 under a declared retry · the TRANSIENT half needs a deterministic transient error and parks behind the HTTP mock, post-announce) + on_codes · on_error.skip preserves the error · recover substitutes BEFORE bindings · DAG-004-class await never deadlocks — **parked**: the engine's check refuses the await shape itself (the corpus's one divergent-by-design row, `errors/recover-task-ref-no-edge` · nika#291), so the runtime contract is unstageable by command until that lands |
| `agent/` | budget exhaustion = NIKA-AGENT-001/002 with partial in error.details · tool errors feed back EXCEPT security_error (the feed-back half is `003-tool-error-feeds-back` — the final AGENT-001 IS the proof the loop survived the tool error · the security half — a refusal that must END the loop — stays unstageable with mock/echo, which cannot be steered to synthesize an out-of-boundary argument deterministically) · nika:done result: becomes .output |
| `permits/` | NIKA-SEC-004 at the first out-of-boundary effect · permits:{} = pure compute |
| `access-harness/` | an unattested agent seat refuses `infer:` with the failed infer-grade conjuncts; an attested one-shot seat admits the same task · `run.json.harness_attestations` is injected conformance evidence, never host discovery |

### Infer-grade harness fixture extension

An `access-harness` fixture adds these invocation fields:

```json
{
  "access": "codex",
  "harness_attestations": {
    "codex": {
      "single_turn": true,
      "no_implicit_tools": true,
      "structured_output": "json_schema",
      "model_identity": "requested"
    }
  }
}
```

The runner injects this declaration instead of discovering a host binary or
reading an account store. `expected-run.json.admission` asserts the
pre-inference meet: `accepted`, and on refusal the exact error code plus a
`witness_contains` list. This keeps the fixture hermetic while the adapter's
own repository proves its process wire with a scripted fake binary.
