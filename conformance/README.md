# Conformance · test suite for any implementation

> The conformance suite is the **machine-checkable definition** of
> « v0.1-compliant ». Any engine that passes the suite may claim
> conformance. Three levels · Core · Runtime · Stdlib v0.1 (see [`../spec/07-conformance.md`](../spec/07-conformance.md)).

---

## Status · placeholder for v0.1.0-draft

The suite will ship in this directory for v0.1.0 GA. Authoring the
suite is one of the four blocker tasks to GA · alongside spec
finalization · examples recopy · and JSON schemas.

## Planned structure

```
conformance/
├── tests/
│   ├── core/                     Core conformance (parse + validate + DAG + variables + errors)
│   │   ├── envelope/
│   │   │   ├── 001-valid-minimal/
│   │   │   │   ├── input.yaml
│   │   │   │   └── expected.json
│   │   │   ├── 002-missing-apiVersion/
│   │   │   ├── 003-bad-workflow-id/
│   │   │   └── ...
│   │   ├── verbs-shape/
│   │   ├── dag-topology/
│   │   │   ├── 001-cycle-detection/
│   │   │   ├── 002-unresolved-depends-on/
│   │   │   └── ...
│   │   ├── variables/
│   │   └── errors/
│   │
│   ├── runtime/                   Runtime conformance (verb execution + task fields)
│   │   ├── infer/
│   │   ├── exec/
│   │   ├── fetch/
│   │   ├── invoke/
│   │   ├── agent/
│   │   └── workflow-lifecycle/
│   │
│   └── stdlib/                    Stdlib v0.1 conformance
│       ├── providers/             (uses mock provider where possible)
│       ├── extract-modes/         (uses HTTP mocks)
│       └── builtins/
│
├── runner-protocol.md             how to run the suite against an engine
└── README.md                       this file
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
PASS  core/envelope/002-missing-apiVersion
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

🦋 *Conformance · pending v0.1.0 GA · machine-checkable forever.*
