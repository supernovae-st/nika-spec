# Conformance runner protocol

> How to run the Nika conformance suite against an engine, and the exact
> contract of a fixture. The suite is the **machine-checkable definition** of
> v0.1-compliance. SPDX-License-Identifier: Apache-2.0.

---

## Fixture layout

Each test case is a directory holding two files ·

```
conformance/tests/<level>/<group>/<NNN-name>/
├── input.yaml       the workflow under test (carries an SPDX header)
└── expected.json    the expected verdict
```

`<level>` ∈ `core` · `runtime` · `stdlib`. `<group>` is the spec area
(`envelope` · `verbs-shape` · `dag-topology` · `variables` · `errors` · …).

## `expected.json` contract

```jsonc
{
  "valid": false,                        // does the workflow pass parse + validation?
  "errors": [                            // present iff valid=false · the engine MUST emit at least one matching error
    { "code": "NIKA-DAG-001",            //   match by exact code when given …
      "category": "validation_error" }   //   … OR by namespace + category when only those are given
  ],
  "note": "human-readable rationale"     // optional · documentation only · not asserted
}
```

(A `mode:` field appeared in early fixtures · it is **reserved, never
asserted** by the reference runner — strict mode is the test default.)

### The emitted wire shape

A conformant validator emits ·

```json
{ "valid": false,
  "errors": [
    { "namespace": "NIKA-VAR", "category": "validation_error", "detail": "…" },
    { "code": "NIKA-BUILTIN-DONE-001", "namespace": "NIKA-BUILTIN",
      "category": "validation_error", "detail": "…" }
  ] }
```

Each error carries `namespace` + `category` (+ `code` when an exact
registered code applies) + a prescriptive `detail` (repair loops converge
on it).

### Matching rule (an expected entry vs the emitted set)

An expected entry **matches** when ANY of ·
- it has a `code` and an emitted error's `code` equals it;
- it has a `namespace` and EITHER an emitted `code` starts with
  `<namespace>-` OR an emitted `namespace` equals it (most static-layer
  errors carry `namespace` without an exact `code` — `category` is
  **advisory** on this path · asserted only via the category-only form
  below);
- it has ONLY a `category` and an emitted error's `category` equals it.

## Suite layout · the tiers the reference runner executes

```
conformance/tests/core/      schema shape · DAG cross-refs · variables · errors
conformance/tests/deep/      the deep-static layer · CEL EBNF parse · jq compile ·
                             durations · schema-meta · when-form · binding purity ·
                             builtin arg shapes (jq expression · wait XOR · write
                             content · done placement)
conformance/tests/stdlib/    stdlib static surface · provider prefixes · extract
                             modes · builtin names (canon.yaml-derived)
```

(`tests/runtime/` is reserved · behavioral fixtures land with the reference
engine's vertical slice · [07](../spec/07-conformance.md#suite-status--v01-honest).)

Runner subcommands · `validate <file>` (one verdict JSON) · `run <dir>`
(one tier) · `examples <dir>` (every example must validate) · **`all`**
(the CI gate · core + stdlib + deep + examples + showcase + templates ·
exit non-zero on any failure).

## Pass criteria (per fixture)

1. Parse + statically validate `input.yaml`.
2. If `expected.valid == true` · the engine MUST accept (zero errors).
3. If `expected.valid == false` · the engine MUST reject, and **EVERY
   entry** in `expected.errors` MUST match the emitted set (per the
   matching rule above) — a fixture listing two expected errors asserts
   both.
4. Stdlib BEHAVIORAL fixtures (post-announce) additionally compare
   execution output (a future `output.json` companion · the `mock`
   provider for determinism).

The engine MUST exit non-zero if any fixture in the claimed level fails.

## The stdlib STATIC-surface layer (`tests/stdlib/`)

Stdlib v0.1 fixtures split the level in two halves ·

- **static surface** (populated · runner-executable today) — the names + shapes
  half · a literal `model:` must be `<provider>/<name>` with a canonical
  provider prefix (→ `NIKA-PROVIDER`) · `nika:*` tools come from the closed
  canonical builtin set (schema enum) · a literal `nika:fetch` `mode:` must be
  a canonical extract mode and a `jq:` argument requires `mode: jq`
  (→ `NIKA-BUILTIN`). The canonical lists derive from [`canon.yaml`](../canon.yaml) ·
  dynamic `${{ }}` values are skipped (runtime's job).
- **behavioral** (post-announce · lands with the reference engine) — execution
  semantics under the `mock` provider + HTTP mocks · a future `output.json`
  companion per fixture.

These fixtures bind **Stdlib-level claims only** — a Core-only engine does not
run them (a Core engine has no provider/builtin knowledge by design).

## Two static layers in `core`

Core fixtures split by *what catches the violation* — useful for engine
authors and tooling ·

- **schema-checkable** — caught by the JSON Schema alone
  (`schemas/workflow.schema.json` · e.g. `nika` const · id patterns ·
  exactly-one-verb · `additionalProperties` · `timeout` pattern). A YAML+JSON-Schema
  validator passes these with zero engine code.
- **engine-parse** — *cross-reference* rules the schema structurally cannot
  express, requiring the engine's DAG/variable resolver ·
  - cycle detection, including self-dependency (`NIKA-DAG-001`)
  - unresolved `depends_on` (`NIKA-DAG-002`)
  - a `${{ tasks.X }}` reference from `when:` · `with:` · `for_each:` · or any
    verb body without `depends_on:[X]` (`NIKA-DAG-003` · per
    [03-dag.md](../spec/03-dag.md) the edge is never inferred)
  - an unresolved `${{ }}` reference (`NIKA-VAR-001` · per
    [04-variables.md](../spec/04-variables.md) §Resolution order) · a
    non-existent task · an undeclared `vars.` / `with.` / `env.` / `secrets.`
    entry · an undefined namespace (`${{ foo.bar }}`) · a loop-local
    (`item` / `index`) outside a `for_each` task
  - an unclosed `${{` delimiter (`NIKA-VAR` · `validation_error` · the
    substitution surface belongs to 04-variables.md · `\${{` escapes)
  - a duplicate task id (`NIKA-PARSE` · `validation_error` · per
    [03-dag.md](../spec/03-dag.md) ids are unique within the workflow)

A minimal Core engine MAY reuse the published JSON Schema for the first layer
and add the cross-reference checks for the second.

## Running (planned CLI)

```bash
nika conformance run conformance/tests/core      # one level
nika conformance run conformance/tests           # all levels
# any engine · same fixtures
<engine> conformance run conformance/tests/core
```

Output (planned) ·

```
PASS  core/envelope/001-valid-minimal
PASS  core/dag-topology/003-when-reference-without-depends-on (NIKA-DAG-003)
FAIL  core/dag-topology/001-cycle (expected NIKA-DAG-001, got NIKA-PARSE-007)
...
Summary · 13/14 passed · 1 failed
```

## Adoption

Non-SuperNovae engines (Python · Go · TS) run this same suite to validate
conformance · open a PR on `supernovae-st/nika-spec` to be listed in
`CONFORMANT_IMPLEMENTATIONS.md`.

---

🦋 *The suite is the contract · machine-checkable forever.*
