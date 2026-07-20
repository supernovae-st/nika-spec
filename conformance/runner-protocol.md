# Conformance runner protocol

> How to run the Nika conformance suite against an engine, and the exact
> contract of a fixture. The suite is the **machine-checkable definition** of
> v0.1-compliance. SPDX-License-Identifier: Apache-2.0

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

(`tests/runtime/` carries the behavioral CONTRACT today — fixture shape ·
run.json invocation · expected-run.json assertions · determinism rules ·
see [tests/runtime/README.md](tests/runtime/README.md) — the fixtures
execute when the reference engine's vertical slice lands ·
[07](../spec/07-conformance.md#suite-status--v01-honest). They use
`input.nika.yaml`, NOT `input.yaml`, so the static `all` gate ignores
them by construction.)

`conformance/tests/lints/` is the **linter-conformance corpus** (the
03-dag one-obvious-way table is « normative for linters ») · per case
`input.yaml` + `expected-lints.json` (`{"lints": [{"rule", "task"}]}` ·
exact ordered equality · fires/silent pairs pin the precision
contract). Engines with a linter walk it (the reference engine's
`lints_one_obvious_way` suite); the Python oracle ships no linter, so
the static `all` gate does not run this tier.

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
  - an unresolved `with:`/`after:` edge target (`NIKA-DAG-002`)
  - a `tasks.*` reference outside the boundary — `when:` · `for_each:` · any
    verb body · a non-parent `on_finally` read (`NIKA-VAR-021` · per
    [04-variables.md](../spec/04-variables.md) §the reference boundary ·
    the fix is machine-applicable: hoist into `with:`)
  - a dead `depends_on:` (`NIKA-PARSE-024`) · an unknown `after:` predicate
    (`NIKA-DAG-005`)
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

## Running

### Third-party mode (available today · `runner.py --engine`)

Any engine proves itself against the suite BY COMMAND, never by
linkage — the reference runner drives it per fixture:

```bash
pip install -r conformance/requirements.txt
python3 conformance/runner.py run conformance/tests/core   --engine "<your-validate-command>"
```

The contract of `<your-validate-command>`: it receives the workflow
path as its **final argument** and prints the wire-shape verdict JSON
on **stdout** — `{"valid": bool, "errors": [{"code"|"namespace",
"category", "detail"}]}` (the shape above). The process exit code is
free — the JSON is the verdict. An engine whose native output differs
wraps itself in a small adapter script (the Bowtie harness pattern).
A missing command, a timeout, or a non-JSON reply fails LOUD as a
`harness_error` — never a silent pass.

Self-test of the mode (the reference oracle driven as if external —
byte-parity with the internal path):

```bash
python3 conformance/runner.py run conformance/tests/core   --engine "python3 conformance/runner.py validate"
```

### Native CLI (planned)

```bash
nika conformance run conformance/tests/core      # one level
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
