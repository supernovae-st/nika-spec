# 01 · Envelope

> Every Nika workflow starts with a header. This is the envelope. It
> identifies the language version, the schema version, and gives the
> workflow an id + sensible defaults.

---

## Minimal envelope

```yaml
apiVersion: nika.sh/v1
schema: nika/workflow@v1
workflow: my-workflow-id

tasks:
  - id: ...
    ...
```

That's the **minimum required** to be a valid Nika workflow.

---

## Full envelope

```yaml
apiVersion: nika.sh/v1                  # required · immutable forever
schema: nika/workflow@v1                # required · minor bumps allowed
workflow: scrape-and-summarize          # required · kebab-case · unique within file
description: "Fetch + summarize"        # optional · human-readable

# Workflow-level defaults · any task may override
provider: anthropic                     # optional · default LLM provider
model: claude-3-5-sonnet                # optional · default model

# Workflow-level variables · available as ${{ vars.<name> }} in every task
vars:
  output_dir: "./output"
  base_url: "https://example.com"

# Tasks (the DAG)
tasks:
  - id: ...
    ...
```

---

## Field-by-field

### `apiVersion` · **required · immutable forever**

```yaml
apiVersion: nika.sh/v1
```

The **major version of the language**. `nika.sh/v1` is the only value
for the entire lifetime of v1. A future `nika.sh/v2` would be a
deliberate breaking-change generation, with its own spec and not
backward-compatible with v1.

**Anti-pattern** · do not write `apiVersion: nika.sh/v1.0` or similar.
The value is exactly `nika.sh/v1`.

### `schema` · *optional · default `nika/workflow@v1`*

```yaml
schema: nika/workflow@v1     # OPTIONAL · defaults to this value if absent
```

The **schema version + document type discriminator**. Minor additions (e.g. a new optional field on a verb) get a minor bump (`@v1.1` · `@v1.2` · …). Breaking changes never happen at this level · they require an `apiVersion` major bump.

A conformant engine MUST accept any `schema: nika/workflow@v1.X` value where X is less than or equal to the engine's supported minor. **If absent · the engine MUST treat the document as `nika/workflow@v1`**.

**Why optional** · in v0.1 we have ONLY ONE document type (workflow). The `schema:` field is forward-compat for future document types (e.g. `nika/agent@v1` for agent definitions · `nika/skill@v1` for skill manifests). Today · omitting it is the simpler default.

Pantheon council ratified this simplification 2026-05-22 (D-2026-05-22-N8 · convergent across Jobs+Rams lens · contested by Hykes+Carmack who prefer K8s pattern · final lean to less-but-better Rams 10).

### `workflow` · **required · kebab-case · unique within file**

```yaml
workflow: scrape-and-summarize
```

A stable identifier for the workflow. Kebab-case. Used in journal events
+ traces + error messages.

Must match · `^[a-z][a-z0-9-]*$`.

### `description` · *optional · human-readable*

```yaml
description: "Fetch article, summarize in 3 bullets, write to disk"
```

Free-form text. Not used by the engine for execution. Useful for `nika ls` listings + LSP hover hints.

### `provider` · *optional · default LLM provider*

```yaml
provider: anthropic
```

Default LLM provider for any `infer:` or `agent:` verb in this workflow.
A task may override this. See [stdlib/providers-v0.1.md](../stdlib/providers-v0.1.md) for the canonical list.

If absent · each task with `infer:` or `agent:` must specify its own `provider:`.

### `model` · *optional · default model*

```yaml
model: claude-3-5-sonnet
```

Default model name. Provider-specific. See provider docs for valid names.

### `vars` · *optional · workflow-level variable scope*

```yaml
vars:
  output_dir: "./output"
  base_url: "https://example.com"
  api_token: "${env:MY_TOKEN}"        # env var reference
```

Variables available in every task via `${{ vars.<name> }}` substitution. See
[04-variables.md](./04-variables.md) for the full substitution grammar.

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

## What the envelope is NOT

- It is NOT a place to declare credentials. Use `${env:VAR_NAME}` substitution + an external env or vault.
- It is NOT a place for runtime config (timeouts · retry policies · etc.). Those belong on individual tasks or in engine config files (out of scope of the spec).
- It is NOT a place for imports / includes. v0.1 is single-file workflows only.

---

## Examples

### Minimal

```yaml
apiVersion: nika.sh/v1
schema: nika/workflow@v1
workflow: hello

tasks:
  - id: greet
    infer:
      prompt: "Hello"
      provider: anthropic
      model: claude-3-5-haiku
```

### Full

```yaml
apiVersion: nika.sh/v1
schema: nika/workflow@v1
workflow: research-pipeline
description: "Research a topic and write a markdown brief"

provider: anthropic
model: claude-3-5-sonnet

vars:
  topic: "Rust async runtimes 2026"
  output_path: "./brief.md"

tasks:
  - id: research
    infer:
      prompt: "Research the topic · ${{ vars.topic }} · in 5 paragraphs"

  - id: write
    depends_on: [research]
    with:
      content: $research
    invoke:
      tool: "nika:write"
      args:
        path: "${{ vars.output_path }}"
        content: "${{ with.content }}"
```

---

## Conformance

A v0.1-compliant engine MUST ·

1. Reject any workflow without an `apiVersion`, `schema`, or `workflow` field with a clear error
2. Accept any `apiVersion: nika.sh/v1`
3. Accept any `schema: nika/workflow@v1.X` where X is supported
4. Reject `apiVersion` or `schema` values not matching the strict format
5. Validate `workflow` identifier kebab-case format
6. Make workflow-level `provider`, `model`, `vars` available to all tasks as defaults

---

🦋 *Next · [02 · The 5 verbs](./02-verbs.md)*
