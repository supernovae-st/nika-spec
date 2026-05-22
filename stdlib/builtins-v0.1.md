# Stdlib v0.1 · Builtins

> The canonical 42 builtins shipped with Stdlib v0.1-compliant engines
> (37 baseline · +5 amended D-2026-05-22-N26 ultrathink session · `notify` ·
> `uuid` · `date` · `hash` · `wait_until`). Invoked via
> `invoke: tool: "nika:<name>"`. Plus 24 media builtins deferred to
> stdlib v0.x (`opt-in feature flag`).

---

## Builtin categories

| Category | Count v0.1 | Status |
|---|---|---|
| Core | 7 | Required for any execution (sleep · log · emit · assert · prompt · done · **wait_until** D-N26) |
| File | 5 | I/O primitives |
| Data | 22 | Transformation + validation (+3 D-N26 · `uuid` · `date` · `hash`) |
| Introspection | 6 | Workflow self-awareness |
| Network | 2 | `nika:fetch` HTTP + extraction · **`nika:notify`** D-N26 |
| Media | — | **Deferred to stdlib v0.x** (opt-in feature flag · cf §Out of scope) |
| **Total v0.1 stdlib** | **42** | |

A Stdlib v0.1-compliant engine MUST ship the 42 builtins.

**Changes vs initial draft** ·
- `nika:complete` **renamed** to `nika:done` (avoid overlap with agent verb completion semantics · 4-0 council vote)
- `nika:run` (nested workflow builtin) **REMOVED** · deferred per §Out of scope(stack-overflow/recursion concerns)
- Media builtins **enumeration removed** from this spec · still feature-flag available in reference engine but not in canonical stdlib v0.1

---

## Core builtins (7) · required for execution

### `nika:sleep`

```yaml
invoke:
  tool: "nika:sleep"
  args:
    duration: "5s"             # Go-duration string · D-N23 consistency
```

Pause execution for the specified duration. Format · Go-duration / Kubernetes-style quoted string (`"500ms"` · `"30s"` · `"5m"` · `"1h30m"` etc. · see `03-dag.md` §timeout for full grammar).

**D-N26 drift fix** · `duration_ms: 5000` (numeric ms) → `duration: "5s"` (Go-duration string) · consistency with D-N23 task-level `timeout:` field · ONE duration format across the language · Rams 4 understandable.

### `nika:log`

```yaml
invoke:
  tool: "nika:log"
  args:
    level: info        # debug | info | warn | error
    message: "Processing user ${{ vars.user_id }}"
    data: { foo: "bar" }    # optional structured data
```

Emit a log entry to the workflow event stream.

### `nika:emit`

```yaml
invoke:
  tool: "nika:emit"
  args:
    event_type: custom.event
    payload: { ... }
```

Emit a custom workflow event (consumed by event subscribers · journal · etc.).

### `nika:assert`

```yaml
invoke:
  tool: "nika:assert"
  args:
    condition: $previous_task.output.count > 0
    message: "Expected non-empty result"
```

Fail the task if `condition` is false. Otherwise no-op.

### `nika:prompt`

```yaml
invoke:
  tool: "nika:prompt"
  args:
    message: "Approve deploying to production?"
    default: false
```

Interactive prompt. Blocks until human confirms (engine determines UX).

**v0.1 conformance** · engines MAY refuse interactive prompts in CI mode · use `default` value automatically.

### `nika:done`

```yaml
invoke:
  tool: "nika:done"
  args:
    result: { status: "complete", data: { ... } }
```

Mark the current `agent:` loop as complete and exit. Inside an agent's tool whitelist · this is the sentinel for graceful termination.

(The `nika:run` nested-workflow builtin was deferred per §Out of scope. Use `exec: command: "nika run subroutine.yaml"` as the v0.1 workaround.)

---

### `nika:wait_until`

```yaml
invoke:
  tool: "nika:wait_until"
  args:
    timestamp: "2026-05-23T09:00:00Z"     # ISO 8601 UTC · MAY be a CEL expression
    timeout: "1h"                          # optional safeguard · default unbounded
```

Pause execution until the specified absolute timestamp is reached. Distinct from `nika:sleep` (relative duration) · `wait_until` is for scheduled execution within a workflow (e.g. « wait until 9 AM UTC then process »).

**`timestamp:`** · required · ISO 8601 string (RFC 3339) · MUST include timezone (use `Z` for UTC) · MAY be a CEL expression that evaluates to a timestamp string.

**`timeout:`** · optional · Go-duration string · safeguard if `timestamp` is very far in the future · returns timeout error if elapsed before target reached.

**Returns** · null on success · throws `NIKA-BUILTIN-WAIT-001` on timeout · throws `NIKA-BUILTIN-WAIT-002` if `timestamp` is in the past.

**Why distinct from `nika:sleep`** · `sleep` is relative (`"5s"` from now) · `wait_until` is absolute (`"2026-05-23T09:00:00Z"`). Both compose · `wait_until` for cron-like scheduling within a workflow run.

---

## File builtins (5)

### `nika:read`

```yaml
invoke:
  tool: "nika:read"
  args:
    path: "./config.yaml"
    encoding: utf-8       # optional · default utf-8
```

Read a file. Returns string content.

### `nika:write`

```yaml
invoke:
  tool: "nika:write"
  args:
    path: "./output.md"
    content: "# Report\n\n..."
    create_dirs: true     # optional · create parent dirs
    overwrite: true       # optional · default true
```

Write to a file. Returns the path.

### `nika:edit`

```yaml
invoke:
  tool: "nika:edit"
  args:
    path: "./file.md"
    find: "old content"
    replace: "new content"
```

In-place find/replace. Returns the modified path.

### `nika:glob`

```yaml
invoke:
  tool: "nika:glob"
  args:
    pattern: "./src/**/*.rs"
    exclude: ["**/target/**", "**/test_*"]
```

Glob match. Returns array of paths.

### `nika:grep`

```yaml
invoke:
  tool: "nika:grep"
  args:
    pattern: "TODO:"
    path: "./src"
    case_insensitive: false
```

Recursive grep. Returns array of `{ path, line, match }`.

---

## Data builtins (22)

### `nika:jq`

```yaml
invoke:
  tool: "nika:jq"
  args:
    expression: ".items | map(.price) | add"
    input: $previous.data
```

Run a jq expression. Returns the result.

**Implementation** · reference engine uses `jaq` (Rust jq · full stdlib).

### `nika:json_merge`

```yaml
invoke:
  tool: "nika:json_merge"
  args:
    base: { foo: 1, bar: 2 }
    overlay: { bar: 99, baz: 3 }
    # → { foo: 1, bar: 99, baz: 3 }
```

Deep merge two JSON values. Overlay wins on conflicts.

### `nika:json_diff`

```yaml
invoke:
  tool: "nika:json_diff"
  args:
    before: { ... }
    after: { ... }
```

JSON diff. Returns RFC 6902 JSON Patch.

### `nika:json_verify`

```yaml
invoke:
  tool: "nika:json_verify"
  args:
    data: { ... }
    schema: { type: object, ... }    # JSON Schema
```

Validate data against a JSON Schema. Returns `{ valid: bool, errors: [...] }`.

### `nika:yaml_validate`

```yaml
invoke:
  tool: "nika:yaml_validate"
  args:
    yaml: "..."
    schema: { ... }
```

Parse YAML + validate against JSON Schema.

### `nika:map`

```yaml
invoke:
  tool: "nika:map"
  args:
    items: [1, 2, 3]
    expression: ". * 2"          # jq-style
```

Map each item via the expression. Returns array.

### `nika:filter`

```yaml
invoke:
  tool: "nika:filter"
  args:
    items: [1, 2, 3, 4]
    expression: ". > 2"
```

Filter. Returns array.

### `nika:group_by`

```yaml
invoke:
  tool: "nika:group_by"
  args:
    items: [{ k: "a", v: 1 }, { k: "b", v: 2 }, { k: "a", v: 3 }]
    key: ".k"
    # → { a: [...], b: [...] }
```

### `nika:chunk`

```yaml
invoke:
  tool: "nika:chunk"
  args:
    items: [1, 2, 3, 4, 5, 6, 7]
    size: 3
    # → [[1,2,3], [4,5,6], [7]]
```

### `nika:flatten`

```yaml
invoke:
  tool: "nika:flatten"
  args:
    data: { a: { b: { c: 1 } } }
    # → { "a.b.c": 1 }
```

### `nika:unflatten`

```yaml
invoke:
  tool: "nika:unflatten"
  args:
    data: { "a.b.c": 1 }
    # → { a: { b: { c: 1 } } }
```

### `nika:aggregate`

```yaml
invoke:
  tool: "nika:aggregate"
  args:
    items: [{ val: 1 }, { val: 2 }, { val: 3 }]
    expression: "map(.val) | add"      # → 6
```

### `nika:enrich`

```yaml
invoke:
  tool: "nika:enrich"
  args:
    item: { id: 1 }
    enrichments:
      - key: "fetched_at"
        value: "$now"
      - key: "source"
        value: "${{ vars.source_name }}"
```

Add fields to an object.

### `nika:locale_lookup`

```yaml
invoke:
  tool: "nika:locale_lookup"
  args:
    code: "fr-FR"
```

Returns ISO 639/3166 metadata · name · region · script · etc.

### `nika:json_merge_patch`

RFC 7396 merge patch. Lighter alternative to `json_merge`.

### `nika:inject`

```yaml
invoke:
  tool: "nika:inject"
  args:
    template: "Hello {{name}}, age {{age}}"
    values: { name: "Alice", age: 30 }
```

Template substitution (independent of `{{var}}` task substitution).

### `nika:csv_to_json`

```yaml
invoke:
  tool: "nika:csv_to_json"
  args:
    csv: "name,age\nAlice,30\nBob,25"
    has_header: true
```

### `nika:json_to_csv`

```yaml
invoke:
  tool: "nika:json_to_csv"
  args:
    data: [{ name: "Alice", age: 30 }]
    headers: ["name", "age"]
```

### `nika:base64_encode` / `nika:base64_decode`

Base64 encode/decode. (Counts as 2 builtins in some engine inventories · counts as 1 here for simplicity.)

---

### `nika:uuid` · D-N26

```yaml
invoke:
  tool: "nika:uuid"
  args:
    version: v7                # default v7 (timestamped · sortable · RFC 9562) · or v4 (random)
```

Generate a UUID. Default **v7** (timestamped + sortable per RFC 9562 · 2024 SOTA · DB-friendly insertion order) · `v4` available for legacy compat (purely random · no time ordering).

**Returns** · canonical hex string (e.g. `"01975a8c-7f3d-7c2e-9a4b-5f8e6d3c1a2b"` for v7).

**Use cases** · workflow run IDs · resource identifiers · trace correlation · idempotency keys (cf v0.2 G8 candidate).

### `nika:date` · D-N26

```yaml
invoke:
  tool: "nika:date"
  args:
    op: now                    # now | add | subtract | format | parse | diff
    # op-specific args ·
    # now    · { tz: "UTC" | "America/New_York" | "Europe/Paris" }    default UTC
    # add    · { base: "2026-05-22T12:00:00Z", duration: "1h30m" }    returns ISO 8601
    # subtract · { base: "...", duration: "..." }                      returns ISO 8601
    # format · { input: "...", format: "RFC3339" | "%Y-%m-%d" }        returns string
    # parse  · { input: "May 22 2026", format: "%b %d %Y" }            returns ISO 8601
    # diff   · { start: "...", end: "...", unit: "seconds"|"hours"|... } returns number
```

Timestamp arithmetic. Op-discriminated single builtin (Rams 10 less but better · vs 6 separate builtins).

**Returns** · ISO 8601 string for `now`/`add`/`subtract`/`parse` · arbitrary format string for `format` · number for `diff`.

**Timezone-aware** · all timestamps include timezone offset (default UTC). Specify `tz:` per IANA timezone DB name.

**Use cases** · log timestamps · scheduling logic · cron-like workflows · duration calculations · TZ conversion for human-readable output.

### `nika:hash` · D-N26

```yaml
invoke:
  tool: "nika:hash"
  args:
    algo: blake3               # default blake3 (studio standard · faster than sha256) · or sha256 · sha512
    content: "${{ tasks.X.output }}"   # string OR bytes (use output_format: bytes upstream)
    encoding: hex              # default hex · or base64
```

Cryptographic content hashing. Default **blake3** (studio canonical · faster than SHA-2 · used by olympus-os-brand-core content-addressed storage). Alternatives · sha256 · sha512.

**Explicitly NOT supported** · md5 · sha1 (legacy · broken for crypto · use a separate non-crypto-hash tool if needed for compatibility).

**Returns** · hex string by default (lowercase) · base64 if `encoding: base64`.

**Use cases** · cache keys (cf v0.2 G9 candidate) · content addressing · idempotency tokens (cf v0.2 G8) · diff detection · provenance audit trails.

---

## Network builtins (2)

### `nika:fetch`

HTTP request + content extraction. Reached via `invoke` — fetching a URL is
*calling a tool*, not a distinct execution model (see
[../spec/02-verbs.md](../spec/02-verbs.md)).

```yaml
- id: scrape
  invoke:
    tool: "nika:fetch"
    args:
      url: "https://example.com/article"
      mode: article            # optional · default = markdown
```

| Arg | Required | Type | Notes |
|---|---|---|---|
| `url` | yes | string | Target URL · may use `${{ ... }}` |
| `method` | no | enum | `GET` (default) · `POST` · `PUT` · `DELETE` · `PATCH` · `HEAD` |
| `headers` | no | object | Extra request headers |
| `body` | no | string\|object | Request body · objects auto-serialized to JSON |
| `mode` | no | enum | Extraction mode · see [extract-modes-v0.1.md](./extract-modes-v0.1.md) · default `markdown` |
| `jsonpath` | no | string | RFC 9535 JSONPath · only with `mode: jsonpath` |

**Output** · extracted content · **string** for text modes (`markdown`/`article`/`text`) · **array/object** for `jsonpath`/`metadata`/`feed`/`links`.

**Security (engine MUST)** · SSRF defense — reject private-network targets (`10.0.0.0/8` · `172.16.0.0/12` · `192.168.0.0/16` · `127.0.0.0/8` · IPv6 link-local · cloud-metadata `169.254.169.254`) unless engine config allows. Honor task-level `timeout_ms`. TLS · reject self-signed by default.

---

### `nika:notify` · D-N26

```yaml
invoke:
  tool: "nika:notify"
  args:
    channel: webhook           # webhook | slack | email | discord | sms
    target: "https://hooks.slack.com/services/..."  # endpoint · email · phone number
    message: "Task completed · ${{ tasks.X.status }}"
    severity: info             # info | warning | error (optional · default info)
    metadata: { trace_id: "${{ tasks.X.trace_id }}" }  # optional structured data
```

Send notifications to external channels. Single builtin · `channel:` enum (Rams 10 less but better · vs 4-5 separate builtins `nika:slack_send` · `nika:email_send` · `nika:webhook_send` · etc.).

**Supported channels (v0.81 engine MAY support subset · MUST gracefully degrade)** ·
- `webhook` · POST JSON to URL · universal (works with Slack · Discord · Teams · custom)
- `slack` · native Slack Web API (richer · requires bot token in secrets)
- `email` · SMTP (requires SMTP config in engine settings)
- `discord` · native Discord webhook (richer than generic webhook)
- `sms` · SMS gateway (requires gateway config · typically Twilio/Vonage)

**Returns** · `{ delivered: bool, channel: string, target: string, timestamp: ISO8601 }`.

**Use cases** · workflow completion alerts · error escalation · human-in-the-loop notifications · pipeline status updates · monitoring integration.

**Conformance** · v0.81 engine MUST support at least `webhook` channel · other channels MAY be feature-gated · unsupported channel returns `NIKA-BUILTIN-NOTIFY-001` (channel-not-configured).

---

## Introspection builtins (6)

### `nika:cost`

```yaml
invoke:
  tool: "nika:cost"
  # → { total_usd: 0.012, by_task: { ... }, by_provider: { ... } }
```

Returns running workflow cost.

### `nika:records`

```yaml
invoke:
  tool: "nika:records"
  # → { tasks: [{ id, status, duration_ms, ... }] }
```

Returns the workflow's execution record so far.

### `nika:dag_info`

```yaml
invoke:
  tool: "nika:dag_info"
  # → { nodes: [...], edges: [...], waves: [...] }
```

Returns the DAG topology.

### `nika:task_status`

```yaml
invoke:
  tool: "nika:task_status"
  args:
    task_id: "some_task"
  # → { status: "success", duration_ms: 1234 }
```

Returns a specific task's status.

### `nika:threads`

```yaml
invoke:
  tool: "nika:threads"
  # → { active: 3, queued: 1, completed: 8 }
```

Returns engine task pool state.

### `nika:orchestrate`

```yaml
invoke:
  tool: "nika:orchestrate"
  args:
    plan: [...]      # dynamic sub-DAG
```

Spawn a dynamic sub-DAG. Returns when all spawned tasks complete.

**v0.1 conformance** · engines MAY restrict `orchestrate` to limited budgets.

---

## Media builtins · **DEFERRED to stdlib v0.x · enumeration not in v0.1 spec**

The media builtins are NOT enumerated in v0.1. They exist in the reference engine under a feature flag · they MAY graduate to stdlib v0.x as a separate document · but the v0.1 spec stays focused on the 37 canonical builtins above.

This is a deliberate **less-but-better** decision (Rams principle 10) · enumeration of 24 media-specific tools would inflate the spec surface 40% without serving the 80% audience.

---

## Cross-builtin invariants

A v0.1-compliant builtin ·

- Takes a single `args` object · returns a JSON-serializable value
- Reports errors as typed `NIKA-BUILTIN-NNN` codes
- Honors task-level `timeout_ms`
- Respects engine security policies (file access · network access · etc.)

---

## Forward-compat

New builtins MAY enter stdlib v0.x. Builtin removal is **never** allowed within stdlib v0.x lifetime · removal requires a new stdlib major version.

---

🦋 *42 builtins canonical · 24 media deferred · clear forever.*
