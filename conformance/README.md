# Conformance · test suite for any implementation

> The conformance suite is the **machine-checkable definition** of
> « v0.1-compliant ». Any engine that passes the suite may claim
> conformance. Three levels · Core · Runtime · Stdlib v0.1 (see [`../spec/07-conformance.md`](../spec/07-conformance.md)).

---

## Status · the full STATIC suite is shipped · behavioral fixtures post-announce

Three populated surfaces today (run the runner for the live counts · counts in
prose drift · the suite is the source) ·

1. **Core fixtures** (`tests/core/` · envelope · verbs-shape · dag-topology ·
   variables · errors) — the machine-checkable parse + validate + DAG +
   variable layer, the part that needs NO engine to define. Each is an
   `input.yaml` + `expected.json` pair (see
   [`runner-protocol.md`](./runner-protocol.md) for the contract). They lock
   every rule hardened in the v1 language reviews (incl. the `outputs:` block ·
   agent `schema:` · the `when→depends_on` rule · the three tool namespaces).

2. **Stdlib static-surface fixtures** (`tests/stdlib/` · providers · builtins ·
   extract-modes) — the stdlib **names + shapes** layer · provider prefixes
   (`model: <provider>/<name>` · the provider is the prefix) · the closed
   `nika:*` builtin set · the canonical extract modes · the `jq:`/`mode: jq`
   coupling. The canonical lists derive from [`canon.yaml`](../canon.yaml)
   (the SSOT) — the runner never hardcodes them.

3. **Examples as conformance inputs** (`../examples/*.nika.yaml`) — every
   shipped example is executed by the `all` gate and MUST validate at the full
   static level. An example that drifts from the spec breaks CI.

**Behavioral** Runtime + Stdlib fixtures (verb execution · provider/builtin
behavior · mock-driven) are **post-announce** — they require an executing
engine and land with the reference engine's vertical slice (see
[`../spec/07-conformance.md`](../spec/07-conformance.md) §Suite status).

### Run it today · the reference static runner

[`runner.py`](./runner.py) is the **reference oracle** for the static layer
(JSON Schema + the cross-reference rules + the stdlib surface) with **no LLM
engine required** ·

```bash
python conformance/runner.py all                       # THE static gate · core + stdlib + examples
python conformance/runner.py run                       # core fixtures only
python conformance/runner.py run conformance/tests/stdlib   # stdlib surface fixtures
python conformance/runner.py validate flow.nika.yaml   # validate one workflow → JSON verdict
python conformance/runner.py examples examples         # assert every example is valid
```

A language engine in any language re-implements the same checks; this
reference runner proves the suite is self-consistent and is the canonical
static-layer oracle.

## Structure

```
conformance/
├── tests/
│   ├── core/                     Core conformance (parse + validate + DAG + variables + errors)
│   │   ├── envelope/
│   │   │   ├── 001-valid-minimal/
│   │   │   │   ├── input.yaml
│   │   │   │   └── expected.json
│   │   │   └── ...
│   │   ├── verbs-shape/
│   │   ├── dag-topology/
│   │   ├── variables/
│   │   └── errors/
│   │
│   ├── stdlib/                    Stdlib v0.1 · static surface (populated) + behavioral (post-announce)
│   │   ├── providers/             prefix discipline · canon.yaml-driven
│   │   ├── builtins/              closed nika:* set · namespace ownership
│   │   └── extract-modes/         canonical modes · jq/mode coupling
│   │
│   └── runtime/                   Runtime conformance (verb execution + task fields) · post-announce
│       ├── infer/
│       ├── exec/
│       ├── invoke/
│       ├── agent/
│       └── workflow-lifecycle/
│
├── runner.py                      the reference static oracle (Core + stdlib surface + examples)
├── runner-protocol.md             how to run the suite against an engine
└── README.md                      this file
```

## Test format

Each test is a directory with ·

- `input.yaml` — the workflow to feed to the engine
- `expected.json` — the expected output or error structure
- `description.md` — (optional) human description of what's being tested
- `env.json` — (optional) environment variables to provide to the engine

The runner pipes `input.yaml` to the engine · captures the structured
output · compares against `expected.json`.

## Runner protocol (planned)

```bash
# Generic runner
conformance-runner --engine "nika run --input -" --tests ./tests/core/

# Output
PASS  core/envelope/001-valid-minimal
PASS  core/envelope/002-missing-envelope
FAIL  core/dag-topology/001-cycle-detection (expected NIKA-DAG-001, got NIKA-PARSE-007)
...

Summary · 245/247 passed · 2 failed
```

A v0.1-compliant engine MUST exit with non-zero if any test in the
claimed level fails.

## Adoption by other engines

When non-SuperNovae engines are written (Python · Go · TS impls of Nika),
they can run this suite to validate conformance. Open a PR on
[supernovae-st/nika-spec](https://github.com/supernovae-st/nika-spec) to be
listed in `CONFORMANT_IMPLEMENTATIONS.md`.

## Mock-driven determinism

Many tests use the `mock` provider and HTTP mocks for · (a) determinism · (b) zero cost · (c) CI-friendly. The mock provider is part of stdlib v0.1 (see [`../stdlib/providers-v0.1.md`](../stdlib/providers-v0.1.md)).

---

🦋 *Core + stdlib-surface fixtures + every example · one static gate (`runner.py all`) · behavioral fixtures land with the engine · machine-checkable forever.*
