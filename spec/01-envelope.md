# 01 · Envelope

> Every Nika workflow starts with one header line. That line names the
> language and pins the contract version. Everything else is the
> workflow id, optional defaults, and the task graph.

---

## Minimal envelope

```yaml
nika: v1
workflow: my-workflow-id

tasks:
  - id: ...
    ...
```

Two required lines (`nika:` + `workflow:`) and a non-empty `tasks:`. That's
the **whole minimum** to be a valid Nika workflow.

---

## Full envelope

```yaml
nika: v1                                # required · language + contract version
workflow: scrape-and-summarize          # required · kebab-case · unique within file
description: "Fetch + summarize"         # optional · human-readable

# Workflow-level default model · any task may override · <provider>/<name>
model: anthropic/claude-sonnet-4-6      # optional · ollama/llama3.1 for local

# Inputs · available as ${{ vars.<name> }} · untyped OR typed
vars:
  output_dir: "./output"                 # untyped · the value is the default
  topic:                                 # typed · enables schema-gen + validation
    type: string
    required: true
    description: "Subject to research"

# Non-sensitive runtime config · available as ${{ env.<name> }}
env:
  LOG_LEVEL: info

# Sensitive values · vault-backed · masked in logs · available as ${{ secrets.<name> }}
secrets:
  api_key:
    source: vault                        # never inline · a reference to a store
    key: prod/anthropic/api-key

# Tasks (the DAG)
tasks:
  - id: ...
    ...
```

---

## Field-by-field

### `nika` · **required · the contract version**

```yaml
nika: v1
```

The first line of every workflow. The key `nika` declares « this is a
Nika workflow »; the value `v1` pins the **language contract version**.

`v1` is the only value for the entire lifetime of the v1 contract. Minor
additions to the language (a new optional field, a new builtin) are
**additive** and never change this value. A future `nika: v2` would be a
deliberate breaking-change generation with its own spec, not
backward-compatible with v1 — and per `forever-v0.x`, that is
effectively never.

**Anti-pattern** · do not write `nika: v1.0` · `nika: "1"` · or
`nika: 1.0`. The value is exactly `v1`.

> **Why one field, not `apiVersion` + `schema`?** Earlier drafts used a
> Kubernetes-style `apiVersion: nika.sh/v1` plus a separate
> `schema: nika/workflow@v1`. That is two version-ish fields and
> ceremony a workflow file does not need. Modern specs converge on a
> single version marker — OpenAPI writes `openapi: 3.1.0`, Docker
> Compose dropped its `version:` field entirely. Nika takes the
> middle, proven path: **one field, the language name as the key, the
> contract version as the value.** The engine's internal canonical URI
> stays `https://nika.sh/spec/v1` for RDF / conformance tooling — but
> the author never types a URL. (Locked D-2026-05-22-N10.)

### `workflow` · **required · kebab-case · unique within file**

```yaml
workflow: scrape-and-summarize
```

A stable identifier for the workflow. Kebab-case. Used in journal events,
traces, and error messages.

The presence of `workflow:` is also the **document-type discriminator** —
it marks this file as a workflow. Future Nika document types (if any ever
ship) would use their own top-level key; there is no separate `kind:`
field in v1.

Must match · `^[a-z][a-z0-9-]*$`.

### `description` · *optional · human-readable*

```yaml
description: "Fetch article, summarize in 3 bullets, write to disk"
```

Free-form text. Not used by the engine for execution. Useful for `nika ls`
listings + LSP hover hints.

### `model` · *optional · default model · `<provider>/<name>`*

```yaml
model: anthropic/claude-sonnet-4-6      # cloud
# model: ollama/llama3.1                # local · same shape
```

Default model for any `infer:` or `agent:` verb in this workflow, as a single
**`<provider>/<name>`** string (the LiteLLM / OpenRouter / Vercel convention —
there is no separate `provider:` field). The provider prefix selects the
backend and decides local-vs-cloud (`ollama/` · `lmstudio/` = local · the rest
= cloud). See [stdlib/providers-v0.1.md](../stdlib/providers-v0.1.md) for the
10-provider catalog.

A task may override this. If absent · each `infer:`/`agent:` task must specify
its own `model:`.

### `vars` · *optional · workflow inputs · untyped OR typed*

```yaml
vars:
  # Untyped form — the value IS the default
  output_dir: "./output"
  base_url: "https://example.com"

  # Typed form — enables validation + schema generation
  topic:
    type: string                 # string · number · boolean · array · object
    required: true               # default false
    default: "Rust async 2026"   # used when the caller omits it
    description: "Subject to research"
```

Inputs available in every task via `${{ vars.<name> }}` substitution.

The **untyped form** (`name: value`) is the value's default — simplest for
a workflow you run yourself. The **typed form** (`name: { type, required,
default, description }`) lets the engine validate inputs and
**generate a callable schema** — this is what powers `nika.run_workflow`
over MCP (a caller like an agent host sees the typed inputs and knows
exactly what to pass) and UI generation. Simple stays simple; power is
there when a workflow becomes a reusable, callable unit.

See [04-variables.md](./04-variables.md) for the full substitution grammar.

### `env` · *optional · non-sensitive runtime config*

```yaml
env:
  LOG_LEVEL: info
  REGION: eu-west
```

Non-sensitive configuration available via `${{ env.<name> }}`. Values may
appear in logs and traces. For anything secret, use `secrets:` instead.

### `secrets` · *optional · vault-backed · masked*

```yaml
secrets:
  api_key:
    source: vault                 # a reference to a store · never an inline value
    key: prod/anthropic/api-key
```

Sensitive values available via `${{ secrets.<name> }}`. A secret is always
a **reference to a store** (the local `nika-vault` by default) — never an
inline literal. The engine **masks** resolved secret values in logs,
traces, and journal events. The `env` / `secrets` split is the modern
secure-workflow default: non-sensitive config in `env`, masked references
in `secrets`.

### `tasks` · **required · non-empty**

```yaml
tasks:
  - id: task_1
    ...
  - id: task_2
    ...
```

The DAG. See [03-dag.md](./03-dag.md) for the task model.

---

## YAML conventions · no traps

A Nika file is **YAML 1.2** (which is a strict superset of JSON — every Nika
workflow can also be written as JSON). YAML 1.2 is mandated specifically to
avoid the classic YAML 1.1 footguns that bite generated configs:

| Trap (YAML 1.1) | What happens | The rule |
|---|---|---|
| `region: no` | parsed as boolean `false` (the « Norway problem ») | YAML 1.2 keeps it a string · still, **quote** bare words that look boolean (`no` · `yes` · `on` · `off`) |
| `id: 0755` | parsed as octal `493` | **quote** numbers with leading zeros · `"0755"` |
| `at: 12:30` | parsed as sexagesimal `750` | **quote** colon-bearing scalars |
| `v: 1.10` | parsed as float `1.1` (trailing zero lost) | **quote** version-like strings · `"1.10"` |

**One rule that removes all of them** · when a scalar *could* be misread as a
number, boolean, or date, **quote it**. When in doubt, quote.

**Expressions** · a bare `${{ … }}` reference is a safe plain scalar
(`prompt: ${{ vars.topic }}` is fine). But **quote** any expression that
contains `:` `#` `[` `{` `,` or `>` so YAML does not misparse it ·

```yaml
when: "${{ tasks.x.status == 'ok' && tasks.y.count > 3 }}"   # quoted · contains > and :
prompt: ${{ vars.topic }}                                    # bare ok · no special chars
```

A conformant engine parses YAML 1.2. Authoring tools (and the AI writing
these files) should quote-by-default for the four ambiguous-scalar cases above.

---

## What the envelope is NOT

- It is NOT a place to inline credentials. Use `secrets:` with a `source` reference.
- It is NOT a place for engine runtime config (global timeouts · concurrency limits). Those live in engine config files, out of scope of the spec.
- It is NOT a place for imports / includes. v1 is single-file workflows. (Static composition is a candidate for a later additive minor — see [08-out-of-scope.md](./08-out-of-scope.md).)

---

## Examples

### Minimal

```yaml
nika: v1
workflow: hello

tasks:
  - id: greet
    infer:
      prompt: "Hello"
      model: anthropic/claude-haiku-4-5
```

### Full · with typed inputs (callable over MCP)

```yaml
nika: v1
workflow: research-pipeline
description: "Research a topic and write a markdown brief"

model: anthropic/claude-sonnet-4-6
vars:
  topic:
    type: string
    required: true
    description: "Subject to research"
  output_path:
    type: string
    default: "./brief.md"

tasks:
  - id: research
    infer:
      prompt: "Research the topic · ${{ vars.topic }} · in 5 paragraphs"

  - id: write
    depends_on: [research]
    with:
      content: ${{ tasks.research.output }}
    invoke:
      tool: "nika:write"
      args:
        path: "${{ vars.output_path }}"
        content: "${{ with.content }}"
```

---

## Conformance

A v1-compliant engine MUST ·

1. Reject any workflow missing `nika:` or `workflow:` with a clear error
2. Accept exactly `nika: v1` · reject any other value (`v1.0` · `1` · `v2` …) with a clear error
3. Validate `workflow` identifier kebab-case format
4. Make workflow-level `provider`, `model`, `vars`, `env`, `secrets` available to all tasks as defaults
5. Validate typed `vars` (type + required) before execution · reject missing required inputs
6. Mask resolved `secrets` values in all logs · traces · journal events

---

🦋 *Next · [02 · The 5 verbs](./02-verbs.md)*
