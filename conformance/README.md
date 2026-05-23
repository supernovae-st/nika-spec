# Conformance · test suite for any implementation

> The conformance suite is the **machine-checkable definition** of
> « v0.1-compliant ». Any engine that passes the suite may claim
> conformance. Three levels · Core · Runtime · Stdlib v0.1 (see [`../spec/07-conformance.md`](../spec/07-conformance.md)).

---

## Status · 14 core fixtures shipped (parse/validate layer) · runtime+stdlib pending

The **Core conformance fixture set** (14 cases · `tests/core/`) is shipped — the
machine-checkable parse + validate + DAG + variable layer, the part that needs
NO engine to define. Each is an `input.yaml` + `expected.json` pair (see
[`runner-protocol.md`](./runner-protocol.md) for the contract). 10 are
schema-checkable (a YAML + `schemas/workflow.schema.json` validator passes them
with zero engine code) · 4 are engine-parse cross-reference rules (cycle
`NIKA-DAG-001` · unresolved depends_on `NIKA-DAG-002` · undeclared `when:`/`with:`
reference `NIKA-DAG-003` · missing `outputs:`/`${{ }}` task ref `NIKA-VAR`).
They lock every rule hardened in the v1 language reviews (incl. the new
`outputs:` block · agent `schema:` · and the `when→depends_on` rule).

Runtime + Stdlib fixtures (verb execution · provider/builtin behavior · mock-driven)
land with the reference engine. Of the four GA blockers (spec · examples · JSON
schemas · conformance) the static conformance layer is now seeded.

### Run it today · the reference Core runner

[`runner.py`](./runner.py) is the **reference oracle** for Level-1 (Core) — it
implements the static layer (JSON Schema + the 4 cross-reference rules
`NIKA-DAG-001/002/003` + `NIKA-VAR-001`) with **no LLM engine required**, so the
14 fixtures are executable + CI-runnable today ·

```bash
python conformance/runner.py run                       # all core fixtures → exit non-zero on fail
python conformance/runner.py validate flow.nika.yaml   # validate one workflow → JSON verdict
python conformance/runner.py examples examples         # assert every example is valid
```

Current · **14/14 core fixtures pass · 7/7 examples valid**. A language engine in
any language re-implements the same checks; this reference runner proves the
suite is self-consistent and is the canonical static-layer oracle.

## Planned structure

```
conformance/
├── tests/
│   ├── core/                     Core conformance (parse + validate + DAG + variables + errors)
│   │   ├── envelope/
│   │   │   ├── 001-valid-minimal/
│   │   │   │   ├── input.yaml
│   │   │   │   └── expected.json
│   │   │   ├── 002-missing-envelope/
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

🦋 *14 core fixtures + reference runner (14/14 pass) · runtime+stdlib pending · machine-checkable forever.*
