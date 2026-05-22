# Quickstart · your first Nika workflow (5 minutes)

> Nika is just YAML. If you can read YAML, you can read Nika. This page
> builds up a real workflow in 5 small steps — copy each block, run it,
> watch it grow.
>
> **Status** · v0.1.0-draft · run with the reference engine (`cargo install
> nika` → the `nika` binary) or any v0.1-compliant engine.

---

## 1 · The smallest workflow

Two header lines + one task ·

```yaml
nika: v1
workflow: hello

model: anthropic/claude-haiku-4-5

tasks:
  - id: greet
    infer:
      prompt: "Say hello in French"
```

- `nika: v1` — the language contract (one line · forever).
- `workflow:` — a name for this file.
- `model:` — the default model · `<provider>/<name>` (the prefix picks the provider).
- one task · `infer:` calls the model.

---

## 2 · Chain two steps (a DAG)

Add a second task that uses the first one's output. `depends_on` builds the
graph · `${{ tasks.<id>.output }}` reads a prior task's result ·

```yaml
nika: v1
workflow: summarize-and-translate

model: anthropic/claude-haiku-4-5

tasks:
  - id: summarize
    infer:
      prompt: "Summarize in one sentence: Nika is a declarative YAML language for AI workflows."

  - id: translate
    depends_on: [summarize]
    infer:
      prompt: "Translate to French: ${{ tasks.summarize.output }}"
```

Tasks with no dependency between them run in parallel · the engine resolves
the order from `depends_on`.

---

## 3 · Parameterize with variables

Declare inputs once in `vars:` · reference them anywhere with `${{ vars.X }}`
(the same `${{ }}` syntax as GitHub Actions · it's [CEL](https://cel.dev)
inside) ·

```yaml
nika: v1
workflow: translate-anything

vars:
  text: "Hello, world"
  target_lang: "French"

model: anthropic/claude-haiku-4-5

tasks:
  - id: translate
    infer:
      prompt: "Translate to ${{ vars.target_lang }}: ${{ vars.text }}"
```

There are 5 variable namespaces · `vars` · `with` · `tasks` · `env` ·
`secrets`. See [spec/04-variables.md](./spec/04-variables.md).

---

## 4 · Use the other verbs

There are exactly **5 verbs** — `infer` (call a model) · `exec` (run a
command) · `fetch` (get + extract a URL) · `invoke` (call a tool) · `agent`
(run an agentic loop). Here's `fetch` + `invoke` working with `infer` ·

```yaml
nika: v1
workflow: fetch-and-summarize

model: anthropic/claude-haiku-4-5

tasks:
  - id: fetch_page
    fetch:
      url: "https://example.com"
      mode: article             # extract readable article text

  - id: summarize
    depends_on: [fetch_page]
    infer:
      prompt: "Summarize: ${{ tasks.fetch_page.output }}"

  - id: save
    depends_on: [summarize]
    invoke:
      tool: "nika:write"        # a stdlib builtin (nika: namespace)
      args:
        path: "./summary.md"
        content: "${{ tasks.summarize.output }}"
```

Tools are `<namespace>:<path>` · `nika:*` are stdlib builtins ·
`mcp:<server>/<tool>` are external MCP tools. See [spec/02-verbs.md](./spec/02-verbs.md).

---

## 5 · Run it

```bash
nika run summarize-and-translate.nika.yaml
```

The same file runs on **any** v0.1-compliant engine — the language is the
contract, the runtime is an implementation detail.

---

## What you just learned

You touched all 5 pillars · the **envelope** (`nika: v1` + `workflow:`) · the
**5 verbs** · the **DAG** (`depends_on` + task outputs) · **variables**
(`${{ }}` · 5 namespaces) · and the start of the **error model** (engines
return `NIKA-<NS>-<NNN>` codes · see [spec/05-errors.md](./spec/05-errors.md)).

## Zero-cloud · local-first

Swap the model prefix to run fully local · no API key, nothing leaves your
machine ·

```yaml
model: ollama/llama3.1        # or lmstudio/... · llamacpp/... · vllm/...
```

## Where to go next

- **[spec/](./spec/)** — the full specification (~30 pages · the contract)
- **[stdlib/](./stdlib/)** — the 13 providers · 9 extract modes · 36 builtins
- **[examples/](./examples/)** — canonical workflows (pending for GA)
- **[README.md](./README.md)** — why a language · repo layout · governance

---

🦋 *Less but better · one file · runs anywhere.*
