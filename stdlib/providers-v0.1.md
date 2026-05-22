# Stdlib v0.1 · Providers

> The canonical 10 providers shipped with v0.1-compliant engines. Each
> provider implements the same interface (LLM chat completion + optional
> streaming + vision + structured output) against a different backend.
> You select one with a single `model: <provider>/<name>` field.

---

## Model selection · ONE field · `model: <provider>/<name>` (D-2026-05-22-N13)

You select an LLM with a **single `model:` field** in the form
`<provider>/<model-name>` — the de-facto standard convention (LiteLLM ·
OpenRouter · Vercel AI SDK · PydanticAI all converged on it). There is **no
separate `provider:` field** · the provider is the prefix.

```yaml
infer:
  model: anthropic/claude-sonnet-4-6     # cloud
  prompt: "..."

infer:
  model: ollama/llama3.1                 # local · same shape
  prompt: "..."
```

**Why one field, not two** · a model belongs to a provider · two separate
fields let you write the silent-nonsense combination `provider: anthropic` +
`model: gpt-4o`. One `<provider>/<name>` string is atomic, self-documenting,
trivially swappable, and the industry standard. The same open model served by
different backends disambiguates cleanly · `groq/llama-3.1-70b` vs
`ollama/llama-3.1-70b`.

**Parameterize it** · combine with typed inputs (D-N10) to run one workflow
against any backend ·

```yaml
vars:
  model: { type: string, default: "anthropic/claude-sonnet-4-6" }
tasks:
  - id: x
    infer: { model: "${{ vars.model }}", prompt: "..." }
# nika run flow.yaml --var model=ollama/llama3.1   ← same workflow, local
```

---

## The 10 canonical providers (D-2026-05-22-N13)

| Provider | Backend | Local? | Auth |
|---|---|---|---|
| `anthropic` | Anthropic Claude API | cloud | `${{ secrets.* }}` |
| `openai` | OpenAI API | cloud | `${{ secrets.* }}` |
| `mistral` | Mistral AI API (EU · sovereign-leaning) | cloud | `${{ secrets.* }}` |
| `groq` | Groq Cloud (fastest open-weight) | cloud | `${{ secrets.* }}` |
| `deepseek` | DeepSeek API (reasoning · cost-efficient) | cloud | `${{ secrets.* }}` |
| `gemini` | Google Gemini API (long context · multimodal) | cloud | `${{ secrets.* }}` |
| `xai` | xAI Grok API | cloud | `${{ secrets.* }}` |
| `ollama` | Ollama daemon (`localhost:11434`) | **local** | none |
| `lmstudio` | LM Studio (`localhost:1234/v1`) | **local** | none |
| `mock` | deterministic test fixture · no LLM call | test | none |

A Stdlib v0.1-compliant engine MUST ship all **10**.

## Local vs cloud · the prefix decides

The **provider prefix IS the local/cloud signal** — no separate `local:` flag,
no hidden config to read:

```
ollama/…     lmstudio/…          → LOCAL  · localhost · no API key · sovereign
anthropic/…  openai/…  groq/…    → CLOUD  · remote API · key via ${{ secrets.* }}
…  mistral/…  deepseek/…  gemini/…  xai/…
mock/…                            → TEST   · deterministic fixture
```

Sovereignty (Rule 1) · **local-first** · nothing leaves the machine unless a
cloud provider is *explicitly* selected. `ollama/llama3.1` makes a sovereign,
zero-cloud run trivial.

`ollama` and `lmstudio` are external **HTTP servers** (OpenAI-compatible API ·
the engine talks to them over localhost). They are NOT the in-process GGUF
runtime `native`, which was DEFERRED post pantheon (D-2026-05-22-N8 · mistral.rs
crashed the host) — re-enters stdlib v0.x when a candle/llama.cpp binding
stabilizes + 30-day crash-free cohort + cross-platform conformance.

## Provider config lives OUTSIDE the workflow

A workflow only *selects* (`model: <provider>/<name>`). It never inlines
`base_url` or keys. The engine resolves each provider's endpoint + auth from
**engine/provider config** (cloud → `${{ secrets.* }}` · local → localhost,
no key). This keeps workflows portable + secrets masked.

---

## Common contract · all providers

Every provider supports ·

```yaml
infer:
  prompt: "..."                # required
  system: "..."                # optional
  model: <provider>/<name>     # one field · e.g. anthropic/claude-sonnet-4-6
  temperature: 0.0 to 2.0      # optional
  max_tokens: <int>            # optional
  schema: { ... }              # optional · structured output
```

The engine MUST route the request to the provider's API, format the response, and return it as task output.

Errors map to `NIKA-PROVIDER-NNN` codes with the provider-specific status.

---

## Provider-by-provider

### `anthropic`

```yaml
infer:
  model: anthropic/claude-3-5-sonnet
  prompt: "..."
```

**Models** · `claude-3-5-sonnet` · `claude-3-5-haiku` · `claude-3-opus` · (and any newer · model name pass-through).

**Auth** · `ANTHROPIC_API_KEY` env var · OR engine config.

**Features** · tool use · vision · extended thinking · structured output via JSON Schema.

**Specific fields** ·
```yaml
infer:
  model: anthropic/claude-sonnet-4-6
  thinking:
    enabled: true
    budget_tokens: 4000
```

---

### `openai`

```yaml
infer:
  model: openai/gpt-4o
  prompt: "..."
```

**Models** · `gpt-4o` · `gpt-4o-mini` · `gpt-4-turbo` · `o1` · (pass-through).

**Auth** · `OPENAI_API_KEY` env var.

**Features** · tool use · vision · structured output (JSON mode).

**Compat endpoints** · the openai provider also routes any openai-compatible endpoint (`OPENAI_BASE_URL` override). Used by · LM Studio · Ollama compatibility mode · LocalAI · Groq's OpenAI-compat endpoint · OpenRouter · etc.

---

### `mistral`

```yaml
infer:
  model: mistral/mistral-large-latest
  prompt: "..."
```

**Models** · `mistral-large-latest` · `mistral-medium-latest` · `mistral-small-latest` · `codestral-latest` · `pixtral-large-latest` (vision) · (pass-through).

**Auth** · `MISTRAL_API_KEY` env var.

**Features** · tool use · vision (pixtral) · structured output.

---

### `groq`

```yaml
infer:
  model: groq/llama-3.3-70b-versatile
  prompt: "..."
```

**Models** · open-weight models on Groq LPU (Llama · Mixtral · Gemma · etc.) · pass-through.

**Auth** · `GROQ_API_KEY` env var.

**Features** · fast inference · tool use (some models) · structured output (some models).

---

### `deepseek`

```yaml
infer:
  model: deepseek/deepseek-chat
  prompt: "..."
```

**Models** · `deepseek-chat` · `deepseek-reasoner` · (pass-through).

**Auth** · `DEEPSEEK_API_KEY` env var.

**Features** · reasoning model · structured output.

---

### `gemini`

```yaml
infer:
  model: gemini/gemini-2.0-flash
  prompt: "..."
```

**Models** · `gemini-2.0-flash` · `gemini-2.0-pro` · `gemini-1.5-pro` · (pass-through).

**Auth** · `GOOGLE_API_KEY` env var · OR ADC.

**Features** · long context (1M+ tokens) · multimodal native (text · image · audio · video) · structured output.

---

### `xai`

```yaml
infer:
  model: xai/grok-2-latest
  prompt: "..."
```

**Models** · `grok-2-latest` · `grok-vision-latest` · (pass-through).

**Auth** · `XAI_API_KEY` env var.

**Features** · vision · real-time data option.

---

### `ollama` · **local-first sovereign**

```yaml
infer:
  model: ollama/llama3.1                 # or any pulled Ollama model
  prompt: "..."
```

**Backend** · the Ollama daemon (`http://localhost:11434`) · OpenAI-compatible API · the engine talks to it over HTTP.

**Models** · any model pulled into Ollama (`llama3.1` · `qwen2.5` · `mistral` · `gemma2` · etc.) · pass-through.

**Auth** · none (localhost).

**Features** · 100% local · zero cloud egress · GPU-accelerated by Ollama. The sovereign default — `model: ollama/<x>` runs offline / air-gapped, zero vendor lock-in. (NOT the in-process `native` GGUF runtime, which is deferred — Ollama is an external server, stable.)

---

### `lmstudio` · **local-first sovereign**

```yaml
infer:
  model: lmstudio/qwen2.5-14b-instruct
  prompt: "..."
```

**Backend** · LM Studio's local server (`http://localhost:1234/v1`) · OpenAI-compatible API.

**Models** · whatever you load in LM Studio · pass-through.

**Auth** · none (localhost · dummy key tolerated).

**Features** · 100% local · zero cloud egress · GUI model management.

---

### `mock`

```yaml
infer:
  model: mock/mock-deterministic
  prompt: "..."
```

**Backend** · deterministic test fixture · returns a configured response.

**Models** ·
- `mock-deterministic` · returns the prompt verbatim (echo)
- `mock-error` · returns a configured error
- `mock-streaming` · streams a configured response
- `mock-json` · returns structured JSON matching a configured schema

**Auth** · none.

**Use case** · workflow tests · CI · conformance suite · zero LLM cost · deterministic.

---

## Cross-provider semantics

When using the same workflow with different providers ·

- The **prompt** is provider-agnostic (raw text)
- The **system message** is provider-agnostic
- The **temperature** is normalized to 0.0-2.0 (engine maps to provider-specific scale)
- The **structured output** uses JSON Schema (engine adapts to provider's native mechanism · JSON mode · function calling · etc.)
- The **vision input** is provider-agnostic in the workflow · the engine adapts

A workflow can switch providers with one line change (`model: anthropic/claude-sonnet-4-6` → `model: openai/gpt-4o`, or → `model: ollama/llama3.1` to go fully local) for most use cases.

---

## Forward-compat

New providers MAY enter stdlib v0.x. Provider-specific options that don't map to the common contract are passed as `provider_options:` (forward-compat extension point · not in v0.1 conformance).

```yaml
# Forward-compat (post-v0.1)
infer:
  model: anthropic/claude-3-5-sonnet
  provider_options:
    cache_control: { type: "ephemeral" }
    beta: ["custom-feature"]
```

The reference engine implements `provider_options:` as best-effort pass-through.

---

🦋 *10 providers · 1 contract · sovereignty preserved.*
