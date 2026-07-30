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

## The tier-scoping rule · a `valid: true` fixture is whole-spec legal

A conformant engine MAY judge more layers than the tier a fixture lives
in binds — authority (`permits` · NIKA-SEC-004), confidentiality
(`egress:` sanctions · NIKA-SEC-006), policy (`endorsement:` ·
NIKA-SEC-013) — and a refusal on ANY spec law is a correct refusal.
Tier-scoping therefore lives in the FIXTURE, never in the runner:

- **`valid: true` asserts the whole spec.** The input MUST be a fully
  legal workflow under every law of the spec, not merely at the tier
  that motivated it: every effect its body names is declared
  (`permits.fs.write` for a literal output path · `permits.net.http`
  for a literal webhook host) · every secret reach is sanctioned
  (`egress:`) · every human gate runs under a declared `endorsement:`
  mode. The reference oracle judges fewer layers than a full engine; a
  fixture that leans on that gap asserts an accident, not a law.
- **`valid: false` fixtures need no scoping.** The matching rule asserts
  the expected entries against the emitted set; an engine that piles
  further out-of-tier refusals on top changes nothing — extra errors
  never un-match, and the verdict is already a refusal.

No runner mechanism carries this rule (no `binds:` field, no namespace
filter): a filter that ignored out-of-tier refusals on valid fixtures
would let a broken engine pass them — fail-open, the one thing this
suite exists to refuse. Applied 2026-07-30 to the six class-C fixtures
(below); the engine-side workaround (choosing narrow tiers) is
superseded.

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

### Tier selection (the T0 dry-run contract · `--tier`)

A fixture's `expected.json` MAY declare `"tier": "<name>"`; the runner
flag `--tier <name>` runs exactly that labeled subset (unlabeled
fixtures are skipped, never failed):

```bash
python3 conformance/runner.py run conformance/tests/core --tier t0
```

The `t0` tier is the dry-run subset of the **weekend re-implementation
rule** (the golden rule a third party must hold before any freeze:
re-implement the checker's core from the spec and the fixtures alone,
in one weekend). The subset is mechanical by construction — parse +
envelope (core/envelope 001-008) · the absent-permits law
(core/authority 001-006) · the error taxonomy for that scope
(core/errors 001-006) · the verb shape gates (verbs-shape 005-006).
A missing command, a timeout, or a non-JSON reply fails LOUD as a
`harness_error` — never a silent pass.

Self-test of the mode (the reference oracle driven as if external —
byte-parity with the internal path):

```bash
python3 conformance/runner.py run conformance/tests/core   --engine "python3 conformance/runner.py validate"
```

### The reference engine's adapter · and the parity it measured

[`adapters/nika-engine.py`](adapters/nika-engine.py) is that small
adapter for the Rust reference engine (its `nika check --json` speaks a
30-key report contract, not this wire shape). Run it:

```bash
NIKA_BIN=/path/to/nika python3 conformance/runner.py run conformance/tests/deep/composition \
  --engine "python3 conformance/adapters/nika-engine.py"
```

**Measured 2026-07-29 · 200 of 215 fixtures agree.** Per tier: core
124/129 · deep **37/37** · stdlib 22/32 · values 10/10 · types 4/4 ·
gates 3/3. The composition family (`tests/deep/composition`) is **9/9**
— two independent oracles, same fixtures, same verdicts.

**Re-measured 2026-07-30 · 203 of 215** (same binary lineage · nika
0.106.1 debug): the adapter learned to derive `category` from the
diagnostics registry and class A closed — stdlib 22/32 → **25/32**,
every other tier byte-identical. The derivation is monotone by
construction: the matching rule consults an emitted `category` ONLY on
the category-only path, so a derived value can open a match, never
close one.

**Re-measured 2026-07-30 (later) · 209 of 215**: the six class-C
fixtures were made whole-spec legal (§the tier-scoping rule) — core
124/129 → **127/129** · stdlib 25/32 → **28/32** · deep/values/types/
gates byte-identical. The six survivors are exactly the four class-B
fixtures (the codeless MODELS rung · an engine owe) and the two
class-D doctrine rows below.

**Re-measured 2026-07-30 (operator locks) · 213 of 217**: the two
class-D rows closed by decision — the TYPE family owns the type-fit
(`core/envelope/010` pins the exact `NIKA-TYPE-001` both oracles
emit), and static binding went **strict by default** (04 §Static
binding validation rewritten: declaring `properties:` closes a level
for binding · `additionalProperties: true` reopens it explicitly ·
bare `type: object` and schema-less producers stay open and sound).
The universe grew 215 → **217**: the undeclared-sibling read moved out
of `core/variables/013` into its own violation/boundary pair
(`014-undeclared-sibling-read-rejected` ·
`015-valid-additional-properties-opens-binding`). Core is FULL —
**131/131** — and every remaining divergence is the one class-B owe:
stdlib 28/32.

The fifteen divergences were not one bug; they are four classes, and
naming them is the point of running this at all:

| # | class | count | what it means |
|---|---|---|---|
| A | **adapter reach** · CLOSED 2026-07-30 | ~~3~~ 0 | the fixture asserts a `category`-ONLY expectation; the engine's report carries `code`+`gate`+`kind` and no category. Closed by derivation, not invention: [`canon/diagnostics/registry.yaml`](../canon/diagnostics/registry.yaml) records each imported code's category as the greppable `category: <c>` note (the C0 canon-flip audit trail) and the adapter maps code → category through it, gated by `canon.yaml`'s closed `error_categories` set — ONE truth. Codes the registry does not cover stay category-less and loud (`stdlib/builtins/001·002·004` now agree) |
| B | **a codeless rung** | 4 | the fixtures expect `NIKA-PROVIDER`; the engine's MODELS rung emits findings with no spec code (`model`·`tasks`·`why`), so nothing can match by code. The engine owes that rung a code — the harness cannot invent one (`stdlib/001` · `stdlib/providers/001·002·006`). Same owe family, second member found 2026-07-30: the engine's strict-binding rung ("`maybe_extra` is not in the declared schema — did you mean …?") also refuses codeless, while its coded `NIKA-VAR-003` twin still speaks only the pre-lock `additionalProperties: false` law — which is why `core/variables/014` asserts the refusal with an empty pin until that rung gains its code |
| C | **layer scope** · CLOSED 2026-07-30 | ~~6~~ 0 | a full engine judges MORE layers than a tier-scoped fixture binds — and verifying the five UNVERIFIED members one by one showed the six were never one class: 3× under-granted authority (`stdlib/builtins/005·006·007` wrote literal paths with no `permits.fs.write` · NIKA-SEC-004) · 1× unsanctioned secret reach (`core/envelope/012` · secrets→exec env with no `egress:` · NIKA-SEC-006 · the law is [01-envelope §egress](../spec/01-envelope.md)'s own default-deny) · 1× undeclared endorsement mode (`core/policy/001` · a human gate under no `endorsement:` · NIKA-SEC-013 · [10 §policy](../spec/10-authority.md)) · 1× not layer-scope at all (`core/dag-topology/011` · `nika:notify` under the canonical arg shape wants `channel`+`target`+`message`, and a literal webhook host wants `permits.net.http`). All six inputs made whole-spec legal (§the tier-scoping rule) · both oracles now accept each. Named honestly: the reference oracle implements neither NIKA-SEC-006 nor NIKA-SEC-013 today — exactly how illegal inputs sat green in this suite |
| D | **doctrine** · CLOSED 2026-07-30 (operator locks) | ~~2~~ 0 | a real disagreement, each side reasoned in its own file. `core/variables/013-valid-output-schema-open-path` asserted « open schema levels … are never statically rejected — the check is sound »; the engine's `schema_typing.rs` answered « a structured-output `schema:` compiles strict — flagging unknown keys is the point of the check ». **Locked strict-by-default**: declaring `properties:` closes a level for binding, `additionalProperties: true` reopens it explicitly, genuinely-open surfaces stay sound — one voice with the `returns:` walk, which was already closed-by-default ([04 §Static binding validation](../spec/04-variables.md) rewritten · 013 keeps the sound half · the sibling read became the 014/015 pair). `core/envelope/010` (both oracles reject · code family PARSE vs TYPE) **locked TYPE**: the type system owns the type-fit, and both oracles already emit the exact `NIKA-TYPE-001`, so the fixture pins it |

Class A was the adapter's own honest limit — closed 2026-07-30 by
deriving the category from the registry (one truth, never a guess).
Class C exposed a missing law, not a missing mechanism — closed
2026-07-30 by §the tier-scoping rule (a `valid: true` fixture is
whole-spec legal) applied to all six inputs. Class D needed a decision,
not a patch — both locked by the operator 2026-07-30 (TYPE owns the
fit · strict binding by default). Class B — the codeless rungs
(MODELS · strict-binding) — is the ONE remaining owe, and it is the
engine's.

One defect was found and FIXED by this measurement: the MODELS rung
refused a TEMPLATED `model:` — reading `${{ const.model }}` as a bare
model id and thereby refusing the parameterization pattern
[08 §H8](../spec/08-out-of-scope.md) recommends by name (« one
workflow, any backend ») on this suite's own fixture
`stdlib/providers/005-valid-parameterized-model`. A rung that cannot
decide must not refuse.

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
