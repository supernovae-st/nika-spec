# Migration status · `nika: v1` envelope coverage

> **Status** · v0.1.0-draft · 2026-05-24
> **License** · Apache-2.0

This document closes the audit thread « do all examples carry the canonical
`nika: v1` envelope » and maps each shipped example to the [5 pillars]. The
short answer · **yes · 7/7 shipped examples carry `nika: v1` · all 5
pillars covered**.

[5 pillars]: README.md#the-5-pillars--immutable-forever

---

## 1 · Envelope parity · 7/7 shipped · GREEN

Every shipped example begins its YAML body with the canonical envelope ·

```yaml
nika: v1
workflow: <id>
```

| Example | `nika: v1` line | Verdict |
|---|---:|:---:|
| `examples/01-hello.nika.yaml` | line 12 | ✓ |
| `examples/06-parallel-fanout.nika.yaml` | line 15 | ✓ |
| `examples/16-exec-pipeline.nika.yaml` | line 12 | ✓ |
| `examples/19-schema-retry.nika.yaml` | line 12 | ✓ |
| `examples/22-fetch-chain.nika.yaml` | line 11 | ✓ |
| `examples/23-code-review.nika.yaml` | line 15 | ✓ |
| `examples/26-for-each-locales.nika.yaml` | line 12 | ✓ |

Lines 1-10 carry the SPDX header + the `# yaml-language-server: $schema`
hint (so editors pick up live validation against
`https://nika.sh/spec/v1/workflow.schema.json`). The canonical envelope
starts on the first non-comment line in every file.

Reproducible audit ·

```bash
# 7 matches expected · one per shipped example
grep -nE "^nika: v1" examples/*.nika.yaml
```

---

## 2 · Pillar coverage · 5/5 · GREEN

| Pillar | Concept | Covered by |
|---|---|---|
| **1 · Envelope** | `nika: v1` + `workflow:` + typed `vars/env/secrets` | all 7 |
| **2 · The 4 verbs** | `infer:` · `exec:` · `invoke:` · `agent:` | `01` (infer) · `16` (exec) · `22` (invoke) · `23` (agent) |
| **3 · DAG shape** | tasks · `depends_on` · `when` · `for_each` · output binding | `06` (parallel) · `16` (depends_on + when) · `26` (for_each) · `22` (chain) |
| **4 · Variables** | one `${{ ... }}` syntax · 5 namespaces | `22` (tasks/with namespace binding) · `26` (`with` per iteration) |
| **5 · Error model** | `NIKA-<NS>-<NNN>` codes · retry · structured output | `19` (retry + structured output) |

Every pillar has at least one canonical demonstrator · and every demonstrator
exercises the canonical envelope. **The « 7 foundation workflows · full v0.1
coverage » claim in [README] §Repository layout holds empirically.**

[README]: README.md

---

## 3 · The 19 pending slots · intentional deferral

The numbering scheme reserves 26 example slots (`01` through `26`) ·
seven are populated as the foundation cohort · nineteen remain open for
post-`v0.1.0` contributors to showcase stdlib idioms (provider variants ·
extract modes · builtins) without inflating the 5-pillar foundation.

Currently empty ·

```
02 03 04 05 · cluster · envelope variations + smallest workflows
07 08 09 10 · cluster · DAG patterns beyond parallel-fanout
11 12 13 14 15 · cluster · variables + control flow + bindings
17 18 · cluster · exec follow-ups (long-running · streams)
20 21 · cluster · error handling + retry deepening
24 25 · cluster · fetch + extract mode showcase
```

The empty slots are **not migration debt** · they represent unwritten
content. The 5-pillar contract is fully covered by the 7 shipped
examples.

When a contributor proposes a new example ·

- Pick a slot number that thematically fits the cluster above
- Begin the YAML body with `nika: v1` (line 1 after SPDX + schema hint)
- Add a one-sentence header comment in the same style as the 7 shipped
- Run the conformance harness to confirm it parses

---

## 4 · Conformance coverage · 14 tests

The `conformance/` tree carries an independent test suite (positive +
negative parses · canonical error code surface). It is not part of the
example envelope audit · but the count is canonical for v0.1.0-draft ·

```
conformance/tests/
├── core/
│   ├── envelope/           5 tests (valid minimal · valid full · bad version · bad workflow-id · unknown key)
│   ├── verbs-shape/        4 tests (no verb · two verbs · agent-with-schema · task-id-not-snake-case)
│   ├── dag-topology/       3 tests (cycle · unresolved depends_on · when-without-depends_on)
│   ├── variables/          1 test  (outputs reference missing task)
│   └── errors/             1 test  (timeout bad format)
```

Total · **14 fixtures** · all executable by the reference conformance
runner (per the `feat: reference Core conformance runner` commit) ·
independent of any specific implementation.

---

## 5 · Versioning context

Two version axes are independent ·

- The **language** is locked at `nika: v1` · forever (the envelope you
  write in every workflow file · cohérent the SQL/GraphQL/Dockerfile
  pattern of « one stable contract · evolves additively »).
- The **reference engine** today targets `v0.81.0` (its own semver
  cadence · `forever-v0.x` per ADR-002 · breaking changes ship on MINOR
  until further notice).

The `nika: v1` contract stays stable while the engine evolves through
`v0.81 → v0.82 → ... → v0.99 → v0.100`. This document tracks only the
language-side envelope coverage.

---

## 6 · Update log

```
2026-05-24  v1.0 — Initial status audit
              · Triggered by the question « do all shipped examples
                carry the nika: v1 envelope · and which pillars do they
                cover ».
              · Empirical answer · 7/7 v1 envelope · 5/5 pillars
                covered by the foundation cohort. The 19 unfilled
                example slots are intentional deferral for post-launch
                stdlib showcase contributions · not migration debt.
              · Conformance count · 14 fixtures (core/envelope · verbs-
                shape · dag-topology · variables · errors).
```
