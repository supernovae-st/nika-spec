# 05 · Errors

> Nika has a **typed error model**. Every error has a code · a category ·
> and structured details. Tasks may declare retry policies and fallback
> recovery. The workflow itself fails when an unrecovered terminal error
> reaches a task with no `on_error:` policy.

---

## Error structure

Every error is a typed structure ·

```json
{
  "code": "NIKA-VERB-INFER-001",
  "category": "provider_error",
  "message": "Anthropic API returned 503 service unavailable",
  "transient": true,
  "details": {
    "provider": "anthropic",
    "model": "claude-3-5-sonnet",
    "status_code": 503,
    "retry_after_secs": 30
  },
  "task_id": "research",
  "attempt": 2
}
```

### Fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `code` | yes | string | `NIKA-<NAMESPACE>-<NNN>` · stable identifier |
| `category` | yes | enum | See category list below |
| `message` | yes | string | Human-readable description |
| `transient` | yes | boolean | True if retry might succeed (network · 503 · rate limit) |
| `details` | no | object | Category-specific structured fields |
| `task_id` | yes (runtime) | string | Which task this error occurred in |
| `attempt` | yes (runtime) | integer | Which attempt failed (1-indexed) |

---

## Error code namespaces

Error codes follow the format `NIKA-<NAMESPACE>-<NNN>` where namespace is 2-5 uppercase letters and NNN is a 3-digit zero-padded number.

| Namespace | Scope | Reserved range |
|---|---|---|
| `NIKA-PARSE` | YAML parse + envelope validation | 001-099 |
| `NIKA-DAG` | DAG topology · cycles · invalid deps | 001-099 |
| `NIKA-VAR` | Variable resolution failures | 001-099 |
| `NIKA-INFER` | `infer:` verb errors | 001-099 |
| `NIKA-EXEC` | `exec:` verb errors | 001-099 |
| `NIKA-FETCH` | `fetch:` verb errors | 001-099 |
| `NIKA-INVOKE` | `invoke:` verb errors | 001-099 |
| `NIKA-AGENT` | `agent:` verb errors | 001-099 |
| `NIKA-PROVIDER` | Provider adapter errors | 001-099 per provider |
| `NIKA-BUILTIN` | Builtin tool errors | 001-099 per builtin |
| `NIKA-MCP` | MCP client errors | 001-099 |
| `NIKA-SEC` | Security policy violations (SSRF · blocklist) | 001-099 |
| `NIKA-TIMEOUT` | Task or step timeouts | 001-099 |
| `NIKA-CANCEL` | Task or workflow cancellation | 001-099 |
| `NIKA-IMPL` | Engine internal errors | 001-099 |

A v0.1-compliant engine MUST use these namespaces for the canonical categories. New error codes MAY be added in minor bumps (additive · never repurposed).

---

## Categories

The `category` field is a closed enum at v1 ·

| Category | Meaning | `transient` default |
|---|---|---|
| `parse_error` | Workflow YAML is malformed or invalid | false |
| `validation_error` | Workflow violates a spec rule (cycle · unknown field · etc.) | false |
| `variable_error` | Reference to undefined variable or invalid path | false |
| `provider_error` | LLM provider returned an error | true (engine assesses) |
| `network_error` | Network failure (DNS · TCP · TLS · timeout) | true |
| `tool_error` | Builtin or MCP tool returned an error | depends |
| `security_error` | SSRF · blocklist · capability denied | false |
| `timeout_error` | Task or step exceeded its timeout | false |
| `cancelled` | Workflow or task cancelled | false |
| `internal_error` | Engine bug · unexpected state | false |

---

## Retry policy

A task MAY declare a `retry:` block. Retries apply to **transient** errors only (`error.transient == true`).

### Syntax

```yaml
- id: flaky_api
  fetch:
    url: "https://flaky.example.com/data"
  retry:
    max_attempts: 5              # default 1 (no retry)
    backoff_ms: 1000             # initial backoff
    backoff_strategy: exponential  # linear | exponential | fixed
    backoff_max_ms: 30000        # cap on backoff (default 60000)
    on_codes:                    # optional · whitelist of codes to retry
      - NIKA-NETWORK-001
      - NIKA-PROVIDER-503
```

### Fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `max_attempts` | yes | integer ≥ 1 | Total attempts (including first try) |
| `backoff_ms` | no | integer | Initial backoff · default 1000 |
| `backoff_strategy` | no | enum | `fixed` · `linear` · `exponential` (default `exponential`) |
| `backoff_max_ms` | no | integer | Cap · default 60000 (1 min) |
| `on_codes` | no | array | If present · only retry on listed codes · else retry all transient |

### Backoff strategies

- `fixed` · `backoff_ms` between every attempt
- `linear` · `backoff_ms * attempt` between attempts (1s · 2s · 3s · …)
- `exponential` · `backoff_ms * 2^(attempt-1)` between attempts (1s · 2s · 4s · 8s · …) · capped at `backoff_max_ms`

### Conformance

A v0.1-compliant engine MUST ·

- Honor `max_attempts` strictly
- Use the configured backoff between attempts
- Only retry transient errors (`error.transient == true`) unless `on_codes` is configured
- Surface the LAST error if all retries fail

---

## Error recovery · `on_error:`

A task MAY declare an `on_error:` block to recover from non-transient errors (or retried-and-still-failing transient errors).

### Syntax

```yaml
- id: api_call
  fetch:
    url: "https://api.example.com/data"
  retry: { max_attempts: 3 }
  on_error:
    fallback: $cached_data                # use another task's output
    # OR
    # value: { default: "empty" }         # use a literal value
    # OR
    # skip: true                          # skip · downstream sees status = skipped
    # OR
    # fail_workflow: true                 # explicit · same as no on_error
```

### Fields (mutually exclusive)

| Field | Effect | Downstream sees |
|---|---|---|
| `fallback: $task` | Use another task's output as this task's output | `status: success` · output from fallback |
| `value: <literal>` | Use a literal value as this task's output | `status: success` · output = literal |
| `skip: true` | Skip this task on error | `status: skipped` |
| `fail_workflow: true` | Fail the whole workflow (default behavior) | n/a (workflow fails) |

### Examples

```yaml
# Use cached data on API failure
- id: api_call
  fetch: { url: "https://api.example.com/data" }
  on_error:
    fallback: $cached_data

# Use a default on error
- id: get_count
  invoke:
    tool: "mcp:db::count_users"
  on_error:
    value: 0

# Skip on error · downstream may handle
- id: optional_step
  exec: { command: "./optional.sh" }
  on_error:
    skip: true

- id: next
  depends_on: [optional_step]
  when: $optional_step.status == "success"   # only run if not skipped
  exec: { command: "..." }
```

---

## Structured output validation

The `infer:` and `agent:` verbs may declare a JSON Schema for structured output. If the model returns invalid JSON or fails schema validation, an error of category `validation_error` is raised.

The engine MAY auto-retry validation failures internally (transparent to the workflow) before surfacing the error. This behavior is engine-configurable.

```yaml
- id: extract
  infer:
    prompt: "Extract entities from · {{var.text}}"
    schema:
      type: object
      required: [entities]
      properties:
        entities:
          type: array
          items:
            type: object
            properties:
              name: { type: string }
              type: { type: string, enum: [person, place, organization] }
  retry:
    max_attempts: 3            # retry on transient errors
  # validation failures may be retried internally · engine choice
```

---

## Workflow-level error semantics

If a task fails with no `on_error:` recovery · the **whole workflow is marked failed** and remaining tasks are cancelled (status `cancelled`).

A workflow's final state is one of ·

| State | Meaning |
|---|---|
| `success` | All tasks reached terminal state · no unrecovered failures |
| `failure` | At least one task failed with no recovery |
| `cancelled` | The workflow was cancelled (Ctrl+C · API call · etc.) |

The engine MUST emit a typed completion event with this state.

---

## Forward-compat

The error structure (fields · categories · namespaces · retry shape · on_error shape) is locked at v1. Additional categories MAY be added in minor bumps (additive only · existing categories never repurposed). Additional retry strategies MAY be added.

Out of scope for v0.1 · structured retry conditions (e.g. `retry_when: $error.details.status_code == 503`) · global on_error handlers · workflow-level circuit breakers. See [08-out-of-scope.md](./08-out-of-scope.md).

---

🦋 *Next · [06 · Stdlib contract](./06-stdlib-contract.md)*
