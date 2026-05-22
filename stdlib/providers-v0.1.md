# Stdlib v0.1 · Providers

> The canonical 9 providers shipped with v0.1-compliant engines. Each
> provider implements the same interface (LLM chat completion + optional
> streaming + vision + structured output) against a different backend.

---

## The 8 canonical providers (post pantheon · 2026-05-22 · native dropped)

| Provider | Backend | Local? | Notes |
|---|---|---|---|
| `anthropic` | Anthropic Claude API | no | Default for many v0.1 examples · canonical for tool-use + extended thinking |
| `openai` | OpenAI API | no | Industry standard · openai-compat endpoints route here (LM Studio · Ollama · etc.) |
| `mistral` | Mistral AI API | no | EU-based · sovereign-leaning · multi-model |
| `groq` | Groq Cloud | no | Fastest inference for open-weight models (Llama · Mixtral) |
| `deepseek` | DeepSeek API | no | Reasoning-strong · cost-efficient |
| `gemini` | Google Gemini API | no | Long context · multi-modal native |
| `xai` | xAI Grok API | no | Real-time data integration option |
| `mock` | Deterministic test fixture | yes | For workflow tests · no real LLM call |

A Stdlib v0.1-compliant engine MUST ship all **8** providers. The reference engine ships these 8.

**Note · the `native` provider (local GGUF via mistral.rs) was originally proposed for v0.1 but DEFERRED to stdlib v0.x post pantheon council 2026-05-22 (D-2026-05-22-N8 · 3-1 verdict drop)**. Empirical evidence · the mistral.rs implementation crashes the host machine in production loads (confirmed during the brouillon dynergie-scrap mission · canonical fallback is `--provider openai` with a local OpenAI-compatible URL). The `native` provider will re-enter stdlib v0.x when ·

1. mistral.rs stabilizes OR is replaced with candle/llama.cpp Rust binding
2. Empirical 30-day cohort runs without machine-crash incidents
3. Conformance test passes on Apple Silicon · Linux x86_64 · Linux ARM

**Local-first sovereign use cases for v0.1** · use the `openai` provider with a local OpenAI-compatible endpoint (LM Studio · Ollama compatibility mode · LocalAI · llama-server). Configure via the engine's provider config (`OPENAI_BASE_URL=http://localhost:11434/v1`). The workflow YAML doesn't need to know · it just says `provider: openai`.

---

## Common contract · all providers

Every provider supports ·

```yaml
infer:
  prompt: "..."                # required
  system: "..."                # optional
  provider: <name>             # this provider
  model: <provider-specific>   # see provider section
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
  provider: anthropic
  model: claude-3-5-sonnet
  prompt: "..."
```

**Models** · `claude-3-5-sonnet` · `claude-3-5-haiku` · `claude-3-opus` · (and any newer · model name pass-through).

**Auth** · `ANTHROPIC_API_KEY` env var · OR engine config.

**Features** · tool use · vision · extended thinking · structured output via JSON Schema.

**Specific fields** ·
```yaml
infer:
  provider: anthropic
  thinking:
    enabled: true
    budget_tokens: 4000
```

---

### `openai`

```yaml
infer:
  provider: openai
  model: gpt-4o
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
  provider: mistral
  model: mistral-large-latest
  prompt: "..."
```

**Models** · `mistral-large-latest` · `mistral-medium-latest` · `mistral-small-latest` · `codestral-latest` · `pixtral-large-latest` (vision) · (pass-through).

**Auth** · `MISTRAL_API_KEY` env var.

**Features** · tool use · vision (pixtral) · structured output.

---

### `groq`

```yaml
infer:
  provider: groq
  model: llama-3.3-70b-versatile
  prompt: "..."
```

**Models** · open-weight models on Groq LPU (Llama · Mixtral · Gemma · etc.) · pass-through.

**Auth** · `GROQ_API_KEY` env var.

**Features** · fast inference · tool use (some models) · structured output (some models).

---

### `deepseek`

```yaml
infer:
  provider: deepseek
  model: deepseek-chat
  prompt: "..."
```

**Models** · `deepseek-chat` · `deepseek-reasoner` · (pass-through).

**Auth** · `DEEPSEEK_API_KEY` env var.

**Features** · reasoning model · structured output.

---

### `gemini`

```yaml
infer:
  provider: gemini
  model: gemini-2.0-flash
  prompt: "..."
```

**Models** · `gemini-2.0-flash` · `gemini-2.0-pro` · `gemini-1.5-pro` · (pass-through).

**Auth** · `GOOGLE_API_KEY` env var · OR ADC.

**Features** · long context (1M+ tokens) · multimodal native (text · image · audio · video) · structured output.

---

### `xai`

```yaml
infer:
  provider: xai
  model: grok-2-latest
  prompt: "..."
```

**Models** · `grok-2-latest` · `grok-vision-latest` · (pass-through).

**Auth** · `XAI_API_KEY` env var.

**Features** · vision · real-time data option.

---

### `native` · **local-first sovereign**

```yaml
infer:
  provider: native
  model: hf://meta-llama/Llama-3.3-70B-Instruct      # or local path
  prompt: "..."
```

**Backend** · mistral.rs OR candle (engine choice · both pure Rust · no Python dep).

**Models** · any GGUF / safetensors model · resolved via `hf://` URI to HuggingFace OR direct local path.

**Auth** · none for public models · `HF_TOKEN` for gated models.

**Features** · GPU acceleration (Metal · CUDA · Vulkan) · structured output (varies by model) · 100% local · zero cloud egress.

**The sovereignty axis** · `native` is what makes Nika's 7-axis moat real. Workflows using `native` provider can run offline · in air-gapped environments · with model lock-in zero.

**Note** · the reference engine's `native` provider is empirically less stable than cloud providers (mistral.rs has crashed under load in some configurations). Engines MAY recommend `--provider openai` with a local OpenAI-compatible server (LM Studio · Ollama) as an alternative local path.

---

### `mock`

```yaml
infer:
  provider: mock
  model: mock-deterministic
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

A workflow can switch providers with one line change (`provider: anthropic` → `provider: openai`) for most use cases.

---

## Forward-compat

New providers MAY enter stdlib v0.x. Provider-specific options that don't map to the common contract are passed as `provider_options:` (forward-compat extension point · not in v0.1 conformance).

```yaml
# Forward-compat (post-v0.1)
infer:
  provider: anthropic
  model: claude-3-5-sonnet
  provider_options:
    cache_control: { type: "ephemeral" }
    beta: ["custom-feature"]
```

The reference engine implements `provider_options:` as best-effort pass-through.

---

🦋 *9 providers · 1 contract · sovereignty preserved.*
