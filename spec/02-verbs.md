# 02 · The 5 verbs

> Every task in a Nika workflow binds to **exactly one** of 5 verbs.
> No 4. No 6. Five forever.
>
> The verbs are the **operations** the workflow performs. Everything
> else (providers · builtins · extract modes · etc.) lives in the
> stdlib and is invoked through the 5 verbs.

---

## The 5 verbs · summary

| Verb | What it does | Stdlib it consumes |
|---|---|---|
| `infer:` | Single LLM call · text · structured · vision · thinking | providers |
| `exec:` | Shell command with sandboxing | (none · pure effect) |
| `fetch:` | HTTP request + content extraction | extract modes |
| `invoke:` | Call a builtin tool OR an MCP tool | builtins · MCP servers |
| `agent:` | Multi-turn agentic loop with tool calls | providers · builtins · MCP |

A task **must** specify exactly one of these. Multiple verbs on a single task is a validation error.

---

## `infer:` · LLM call

A single LLM call. The result is the model's response.

### Minimal

```yaml
- id: greet
  infer:
    prompt: "Say hello in French"
```

### Full

```yaml
- id: research
  infer:
    prompt: "Research Rust async runtimes 2026 in 5 paragraphs"
    system: "You are a senior software architect."
    provider: anthropic               # override workflow default
    model: claude-3-5-sonnet
    temperature: 0.3
    max_tokens: 2000
    schema:                            # optional · structured output
      type: object
      required: [summary, paragraphs]
      properties:
        summary: { type: string }
        paragraphs: { type: array, items: { type: string } }
    thinking:                          # optional · extended thinking
      enabled: true
      budget_tokens: 4000
    vision:                            # optional · vision input
      - source: file
        path: "./diagram.png"
```

### Fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `prompt` | yes | string | User prompt · may use `${{ ... }}` substitution |
| `system` | no | string | System prompt |
| `provider` | no | string | Override workflow default · see stdlib/providers-v0.1.md |
| `model` | no | string | Override workflow default · provider-specific |
| `temperature` | no | number 0-2 | Sampling temperature |
| `max_tokens` | no | integer | Max output tokens · provider-dependent default |
| `schema` | no | object | JSON Schema · structured output validation |
| `thinking` | no | object | Extended thinking · `{ enabled, budget_tokens }` |
| `vision` | no | array | Image inputs · each `{ source: file|url, path|url, … }` |

### Conformance

A v0.1-compliant engine MUST ·

- Call the configured provider with the given prompt + system + parameters
- Return the model's response as the task output
- Validate the response against `schema` if present · retry up to N times on validation failure (engine config)
- Reject any unknown field with a clear error (forward-compat) · or accept + warn (engine choice)

---

## `exec:` · shell command

Run a shell command. The result is the command's stdout (default) or a structured output.

### Minimal

```yaml
- id: build
  exec:
    command: "cargo build --release"
```

### Full

```yaml
- id: test
  exec:
    command: "cargo test --workspace --lib"
    cwd: "./engine"
    timeout_ms: 60000
    env:
      RUST_LOG: "debug"
    stdin: "${{ vars.input_data}}"
    capture: structured            # stdout | stderr | structured | combined
```

### Fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `command` | yes | string | Command to run · may use `${{ ... }}` substitution |
| `cwd` | no | string | Working directory · default = engine's cwd |
| `timeout_ms` | no | integer | Default 30000 (30s) · max engine-configurable |
| `env` | no | object | Extra env vars · merged with engine env |
| `stdin` | no | string | Stdin data · may use `${{ ... }}` |
| `capture` | no | enum | `stdout` (default) · `stderr` · `combined` · `structured` (= `{ stdout, stderr, exit_code }`) |

### Security

A v0.1-compliant engine MUST ·

- Implement a shell **blocklist** for dangerous commands (see reference impl `nika-policy` for canonical list · 100+ patterns including `rm -rf /` · `chmod 777` · `curl … | sh` · etc.)
- Reject blocklist matches with a clear error
- Honor `timeout_ms` with a hard kill
- Sandbox `cwd` if configured (engine-specific)

### Conformance

The engine MUST ·

- Run the command via the OS shell (`/bin/sh -c` on Unix · `cmd /c` on Windows, OR a sandboxed equivalent)
- Capture stdout/stderr as configured
- Return exit code in `structured` capture mode
- Fail the task on non-zero exit (unless `on_error:` overrides · see [05-errors.md](./05-errors.md))

---

## `fetch:` · HTTP request + extraction

Make an HTTP request, extract content. The result is the extracted text (or structured data depending on mode).

### Minimal

```yaml
- id: scrape
  fetch:
    url: "https://example.com/article"
```

Defaults · `method: GET` · `mode: markdown`.

### Full

```yaml
- id: api_call
  fetch:
    url: "https://api.example.com/v1/users"
    method: POST
    headers:
      Authorization: "Bearer ${env:API_TOKEN}"
      Content-Type: "application/json"
    body:
      query: "${{ vars.search_term}}"
    mode: jsonpath
    jsonpath: "$.data.users[*].name"
    timeout_ms: 10000
    retry:
      max_attempts: 3
      backoff_ms: 1000
```

### Fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `url` | yes | string | Target URL · may use `${{ ... }}` |
| `method` | no | enum | `GET` (default) · `POST` · `PUT` · `DELETE` · `PATCH` · `HEAD` |
| `headers` | no | object | Extra request headers |
| `body` | no | string\|object | Request body · objects auto-serialized to JSON |
| `mode` | no | enum | See [stdlib/extract-modes-v0.1.md](../stdlib/extract-modes-v0.1.md) · default `markdown` |
| `jsonpath` | no | string | JSONPath expression · only with `mode: jsonpath` |
| `timeout_ms` | no | integer | Default 10000 (10s) |
| `retry` | no | object | See [05-errors.md](./05-errors.md) |

### Security

A v0.1-compliant engine MUST ·

- Implement **SSRF defense** · reject URLs targeting private networks (`10.0.0.0/8` · `172.16.0.0/12` · `192.168.0.0/16` · `127.0.0.0/8` · IPv6 link-local · cloud-metadata `169.254.169.254`) unless engine config explicitly allows
- Enforce `timeout_ms` with hard kill
- Honor TLS · reject self-signed by default

### Conformance

The engine MUST ·

- Issue the HTTP request as specified
- Apply the configured extraction mode (see stdlib)
- Return the extracted content as task output
- Fail with a typed error on network failure · timeout · non-2xx (unless `on_error:` overrides)

---

## `invoke:` · builtin or MCP tool call

Call a builtin (`nika:*` namespace) or an MCP tool (`server::tool` namespace). The result is the tool's response.

### Builtin call

```yaml
- id: read_config
  invoke:
    tool: "nika:read"
    args:
      path: "./config.yaml"
```

See [stdlib/builtins-v0.1.md](../stdlib/builtins-v0.1.md) for the canonical builtin list (61 tools in v0.1).

### MCP call

```yaml
- id: query_db
  invoke:
    tool: "mcp:postgres::query"
    args:
      sql: "SELECT * FROM users WHERE id = $1"
      params: ["${{ vars.user_id}}"]
```

The namespace prefix · `mcp:` · then `<server>::<tool>`. The MCP server `postgres` must be configured in the engine's MCP server registry.

### Fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `tool` | yes | string | Tool identifier · `nika:<builtin>` OR `mcp:<server>::<tool>` |
| `args` | no | object | Tool arguments · schema is tool-specific |

### Conformance

The engine MUST ·

- Resolve the tool identifier to its implementation (builtin or MCP server)
- Reject unknown tools with a clear error
- Pass `args` to the tool · validate against tool's schema if known
- Return the tool's response as task output

---

## `agent:` · multi-turn agentic loop

Run an agentic loop · the model + a set of tools · iterating until completion or budget exhausted.

### Minimal

```yaml
- id: research
  agent:
    system: "You are a research assistant."
    user: "Research the topic · ${{ vars.topic}}"
```

### Full

```yaml
- id: research
  agent:
    system: "You are a research assistant. Use tools to gather info."
    user: "Research the topic · ${{ vars.topic}} · and produce a markdown brief"
    provider: anthropic
    model: claude-3-5-sonnet
    tools:                            # whitelist
      - "nika:fetch"
      - "nika:write"
      - "mcp:browser::*"              # all tools from browser MCP server
    max_turns: 20
    max_tokens_total: 100000
    temperature: 0.3
```

### Fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `system` | no | string | System prompt |
| `user` | yes | string | Initial user message |
| `provider` | no | string | Provider override |
| `model` | no | string | Model override |
| `tools` | no | array | Tool whitelist · glob patterns supported · if absent · all engine tools allowed (engine config) |
| `max_turns` | no | integer | Loop limit · default 10 |
| `max_tokens_total` | no | integer | Cumulative token budget · default engine-configurable |
| `temperature` | no | number 0-2 | Sampling temperature |

### Loop semantics

The agent loops · model response → if tool calls present, execute tools → feed results back to model → repeat. The loop terminates when ·

1. Model returns a final response with no tool calls, OR
2. `max_turns` reached, OR
3. `max_tokens_total` exhausted, OR
4. A tool returns the canonical completion sentinel `nika:done` (the builtin tool · see [stdlib/builtins-v0.1.md](../stdlib/builtins-v0.1.md))

### Tool whitelist · glob semantics

The `tools:` whitelist uses **gitignore-style globs** for matching ·

```yaml
tools:
  - "nika:read"                  # exact match
  - "nika:*"                     # any nika builtin
  - "mcp:browser::*"             # any tool from the `browser` MCP server
  - "mcp:postgres::query"        # exact match · postgres query only
```

Match rules (canonical) ·

- `*` matches any sequence of characters EXCEPT `:` (so `nika:*` does NOT match `nika:read::sub`)
- `**` matches any sequence including `:` (rare · use sparingly)
- Order matters · later rules override earlier rules
- Negation via `!` prefix · `tools: ["mcp:browser::*", "!mcp:browser::navigate"]`

A v0.1-compliant engine MUST implement these glob semantics canonically · NOT engine-specific. This is a portability invariant.

The task output is the final model response.

### Conformance

The engine MUST ·

- Honor the `tools` whitelist · reject tool calls not in the whitelist
- Enforce `max_turns` and `max_tokens_total` budgets · terminate on exhaustion
- Detect the `nika:done` completion sentinel and exit gracefully
- Return the final model response as task output

---

## Forward-compat

The 5 verb names are **immutable forever**. Field additions to each verb are **additive minor bumps** (`schema: nika/workflow@v1.X`). Field removal NEVER happens at v1.

A v0.1-compliant engine that encounters an unknown field on a verb may ·

- **Reject** with a clear error (strict mode · default for tests)
- **Warn + ignore** the field (lenient mode · default for production)

Engine config picks which mode.

---

🦋 *Next · [03 · DAG shape](./03-dag.md)*
