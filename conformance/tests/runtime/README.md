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
├── run.json            invocation · {"vars": {...}, "env": {...}}
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
      "error_code": "NIKA-…"              // optional · when status=failure
    }
  },
  "events_include": ["task.started:<id>", "task.skipped:<id>"]   // optional · order-free
}
```

Determinism rules · `mock/echo` only (prompt-verbatim output · schema →
shaped defaults) · no network (fetch fixtures use the engine's HTTP mock ·
post-announce) · no wall-clock asserts (durations are reported · never
asserted).

## The five areas (one per execution contract)

| Area | First fixtures (the contracts rounds 1-7 locked) |
|---|---|
| `gates/` | default gate cancels on upstream failure · explicit `when:` evaluates over terminal deps · `when: true` runs in a failing workflow (the always-pattern) |
| `for-each/` | per-iteration timeout · null placeholder at a failed index (zip alignment) · empty collection → skipped |
| `errors/` | retry honors transient-only + on_codes · on_error.skip preserves the error · recover substitutes BEFORE bindings · DAG-004-class await never deadlocks |
| `agent/` | budget exhaustion = NIKA-AGENT-001/002 with partial in error.details · tool errors feed back EXCEPT security_error · nika:done result: becomes .output |
| `permits/` | NIKA-SEC-004 at the first out-of-boundary effect · permits:{} = pure compute |
