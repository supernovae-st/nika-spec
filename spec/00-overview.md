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
1.  ENVELOPE        apiVersion: nika.sh/v1
                    schema: nika/workflow@v1
                    workflow: my-workflow-id

2.  THE 5 VERBS     infer:  exec:  fetch:  invoke:  agent:

3.  DAG SHAPE       tasks · depends_on · when · output binding

4.  VARIABLES       ${{ ... }} substitution
                    $task_id reference
                    with: scope rules

5.  ERROR MODEL     codes namespace · retry semantics · structured output
```

These 5 pillars are **locked forever** at v1. Everything else (providers · builtins · extract modes · etc.) lives in the **stdlib** and evolves independently.

---

## Hello world

```yaml
apiVersion: nika.sh/v1
schema: nika/workflow@v1
workflow: hello

provider: anthropic
model: claude-3-5-haiku

tasks:
  - id: greet
    infer:
      prompt: "Say hello in French"
```

---

## A more representative example

```yaml
apiVersion: nika.sh/v1
schema: nika/workflow@v1
workflow: scrape-and-summarize

provider: anthropic
model: claude-3-5-sonnet

tasks:
  - id: fetch_page
    fetch:
      url: "https://example.com/article"
      mode: article          # readability extraction

  - id: summarize
    depends_on: [fetch_page]
    with:
      content: $fetch_page
    infer:
      prompt: "Summarize in 3 bullets · ${{ with.content }}"

  - id: write_file
    depends_on: [summarize]
    with:
      summary: $summarize
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
| [01 envelope](./01-envelope.md) | The required header · `apiVersion` · `schema` · `workflow` |
| [02 verbs](./02-verbs.md) | The 5 verbs · signatures · semantics |
| [03 DAG](./03-dag.md) | Tasks · `depends_on` · `when` · output binding |
| [04 variables](./04-variables.md) | `${{ vars.X }}` · `${{ with.X }}` · `${{ tasks.X.output }}` · `${{ env.X }}` |
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

This spec follows the **forever-v0.x** discipline (per the reference engine ADR-002). No v1.0 release target. The 5 pillars are locked at v1 of the major version (`apiVersion: nika.sh/v1`) · minor schema bumps (`schema: nika/workflow@v1.X`) are additive only · breaking changes ship as a new major (`apiVersion: nika.sh/v2`) and a new spec.

In practice · we expect v1 to last 10+ years.

---

🦋 *Less but better · Rams principle 10.*
