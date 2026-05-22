# 00 · Overview

> The one-page vision. Read this first.

---

## What Nika is

Nika is a **declarative YAML language for AI workflows**.

It describes the **what** ·

- which LLMs to call (`infer:`)
- which commands to run (`exec:`)
- which URLs to fetch (`fetch:`)
- which tools to invoke (`invoke:`)
- which agentic loops to spawn (`agent:`)

The **how** lives in conformant engines.

---

## Why a language?

Every AI harness today reinvents the wheel · Python files · TypeScript
classes · skills crystallized into their own runtime. None of them are
**portable**.

A portable language means ·

- One YAML workflow · runs on any conformant engine
- Read · share · review · diff like any text
- The contract is the language · not the runtime

Standards work · SQL · GraphQL · OpenAPI · Dockerfile · GitHub Actions YAML. Nika is that for AI workflows.

---

## The 5 pillars · immutable forever

```
1.  ENVELOPE        nika: v1
                    workflow: my-workflow-id

2.  THE 5 VERBS     infer:  exec:  fetch:  invoke:  agent:

3.  DAG SHAPE       tasks · depends_on · when · for_each · output binding

4.  VARIABLES       ${{ ... }} = CEL · ONE syntax · 5 namespaces
                    vars · with · tasks · env · secrets

5.  ERROR MODEL     NIKA-<NS>-<NNN> codes · retry semantics · structured output
```

These 5 pillars are **locked forever** at `nika: v1`. Everything else (providers · builtins · extract modes · etc.) lives in the **stdlib** and evolves independently. Minor language additions are **additive** within `v1` (feature-detected · no minor version in the file).

---

## Hello world

```yaml
nika: v1
workflow: hello

provider: anthropic
model: claude-haiku-4-5

tasks:
  - id: greet
    infer:
      prompt: "Say hello in French"
```

---

## A more representative example

```yaml
nika: v1
workflow: scrape-and-summarize

provider: anthropic
model: claude-sonnet-4-6

tasks:
  - id: fetch_page
    fetch:
      url: "https://example.com/article"
      mode: article          # readability extraction

  - id: summarize
    depends_on: [fetch_page]
    with:
      content: ${{ tasks.fetch_page.output }}
    infer:
      prompt: "Summarize in 3 bullets · ${{ with.content }}"

  - id: write_file
    depends_on: [summarize]
    with:
      summary: ${{ tasks.summarize.output }}
    invoke:
      tool: "nika:write"
      args:
        path: "summary.md"
        content: "${{ with.summary }}"
```

3 tasks · DAG with deps · 3 different verbs (`fetch:` · `infer:` · `invoke:`) · variable substitution + task output reference.

---

## How to read the rest

| Section | What it covers |
|---|---|
| [01 envelope](./01-envelope.md) | The header · `nika: v1` · `workflow:` · typed `vars` · `env` · `secrets` |
| [02 verbs](./02-verbs.md) | The 5 verbs · signatures · semantics |
| [03 DAG](./03-dag.md) | Tasks · `depends_on` · `when` · `for_each` · output binding |
| [04 variables](./04-variables.md) | `${{ vars · with · tasks · env · secrets }}` · 5 namespaces |
| [05 errors](./05-errors.md) | Error codes · retry · structured output schemas |
| [06 stdlib contract](./06-stdlib-contract.md) | How the stdlib versions independently |
| [07 conformance](./07-conformance.md) | What « v0.1-compliant » means |
| [08 out of scope](./08-out-of-scope.md) | Explicit defer list (memory · macros · etc.) |

---

## What's NOT in v0.1 of the language

The following are **deferred** to stdlib v0.x or beyond ·

- Memory subsystem APIs (Diamond memory · `nika-memory` orchestrator + satellites · separate stdlib version)
- Workflow include/import (single-file workflows only in v0.1)
- Macros / templates (no preprocessing layer)
- 24 media builtins (`pdf_extract` · `chart` · `qr_validate` · etc. · stdlib v0.x)
- Persistent jobs · scheduled execution (runtime concern · daemon at v0.3)
- Streaming output (deferred)
- Multi-workflow orchestration (deferred)

See [`08-out-of-scope.md`](./08-out-of-scope.md) for the explicit list.

---

## Forever-v0.x

This spec follows the **forever-v0.x** discipline (per the reference engine ADR-002). No v1.0 release target. The 5 pillars are locked at the `nika: v1` contract · minor language additions are additive only (feature-detected · no minor version in the file) · breaking changes would ship as a new contract (`nika: v2`) with its own spec — and per forever-v0.x, that is effectively never.

In practice · we expect v1 to last 10+ years.

---

🦋 *Less but better · Rams principle 10.*
