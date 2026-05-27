# Stdlib v0.1 · Builtins

> **26 canonical builtins** shipped with Stdlib v0.1-compliant engines.
> Invoked via `invoke: tool: "nika:<name>"`. Plus media builtins deferred to
> stdlib v0.x (opt-in feature flag).
>
> **Consolidation (« less but better »)** · was 42 →
> **26**. `nika:jq` is THE data language · 13 thin wrappers that jq subsumes
> were cut (incl. `json_merge` = jq's recursive `*` · jaq source-verified
> 2026-05-27 · `obj_merge` impl + test corpus + corelang docs) · the validators
> merged · `task_status`/`orchestrate`/`locale_lookup` cut. ZERO capability loss
> (jq ⊇ them all · jaq-verified). See §"What jq subsumes" below.

---

## Builtin categories

| Category | Count | Status |
|---|---|---|
| Core | 7 | Required for execution (sleep · log · emit · assert · prompt · done · wait_until) |
| File | 5 | I/O primitives (read · write · edit · glob · grep) |
| Data | 8 | `jq` (THE data language) + 7 capabilities jq can't express (json_diff · validate · json_merge_patch · csv_to_json · uuid · date · hash) |
| Introspection | 4 | Self-awareness (cost · records · dag_info · threads) |
| Network | 2 | fetch (HTTP+extraction) · notify (alerts out) |
| Media | — | **Deferred to stdlib v0.x** (opt-in feature flag) |
| **Total v0.1** | **26** | |

A Stdlib v0.1-compliant engine MUST ship these 26.

---

## Core builtins (7)

### `nika:sleep`
```yaml
invoke: { tool: "nika:sleep", args: { duration: "5s" } }   # Go-duration string
```
Pause for a relative duration (`"500ms"`/`"30s"`/`"5m"`/`"1h30m"` · see `03-dag.md` §timeout).

### `nika:log`
```yaml
invoke: { tool: "nika:log", args: { level: info, message: "Processing ${{ vars.user_id }}", data: { foo: "bar" } } }
```
Emit a log entry (`debug`/`info`/`warn`/`error`) to the workflow event stream (human-readable diagnostic).

### `nika:emit`
```yaml
invoke: { tool: "nika:emit", args: { event_type: custom.event, payload: { ... } } }
```
Emit a custom machine event (consumed by subscribers · journal). Distinct from `log` · `log` = human diagnostic · `emit` = machine event.

### `nika:assert`
```yaml
invoke: { tool: "nika:assert", args: { condition: "${{ tasks.X.output.count > 0 }}", message: "Expected non-empty result" } }
```
Fail the task if `condition` (a **CEL `${{ }}` boolean**) is false · else no-op. The **fail-fast guard** (distinct from `when:` which is the **skip-guard**). `condition:` uses the canonical `${{ }}` CEL surface — never a legacy `$task` syntax.

### `nika:prompt`
```yaml
invoke: { tool: "nika:prompt", args: { message: "Approve deploy to production?", default: false } }
```
Interactive human confirm · blocks until answered. v0.1 conformance · engines MAY use `default` in CI/non-interactive mode.

### `nika:done`
```yaml
invoke: { tool: "nika:done", args: { result: { status: "complete" } } }
```
Mark the current `agent:` loop complete and exit · the loop-completion sentinel (**valid only inside an `agent:` tool whitelist** · error elsewhere).

### `nika:wait_until`
```yaml
invoke: { tool: "nika:wait_until", args: { timestamp: "2026-05-23T09:00:00Z", timeout: "1h" } }
```
Pause until an **absolute** ISO 8601 timestamp (vs `sleep` = relative). `timestamp:` MAY be a CEL expression. Throws `NIKA-BUILTIN-WAIT-001` on timeout · `-002` if the timestamp is in the past.

---

## File builtins (5)

### `nika:read`
```yaml
invoke: { tool: "nika:read", args: { path: "./config.yaml", encoding: utf-8 } }
```
Read a file · returns string content.

### `nika:write`
```yaml
invoke: { tool: "nika:write", args: { path: "./out.md", content: "...", create_dirs: true, overwrite: true } }
```
Write a file · returns the path. A binary `content` value (an opaque bytes output from an upstream tool · e.g. MCP image content) is written as-is · no `output_format` declaration needed (the value carries its own type).

### `nika:edit`
```yaml
invoke: { tool: "nika:edit", args: { path: "./file.md", find: "old", replace: "new" } }
```
In-place find/replace · returns the modified path.

### `nika:glob`
```yaml
invoke: { tool: "nika:glob", args: { pattern: "./src/**/*.rs", exclude: ["**/target/**"] } }
```
Glob match · returns array of paths.

### `nika:grep`
```yaml
invoke: { tool: "nika:grep", args: { pattern: "TODO:", path: "./src", case_insensitive: false } }
```
Recursive grep · returns array of `{ path, line, match }`.

---

## Data builtins (8) · `jq` is THE data language

### `nika:jq` · the transform + extraction primitive
```yaml
invoke: { tool: "nika:jq", args: { expression: ".items | map(.price) | add", input: "${{ tasks.X.output }}" } }
```
Run a jq expression. **The single data-transform-and-extraction language** — map · filter · select · group_by · reshape · string-interpolation `"\(.x)"` · `@base64`/`@base64d`/`@csv` encoders · array `flatten` · `leaf_paths`/`getpath`/`setpath`. The same jq used in `output:` bindings (see `04-variables.md`).

**Implementation** · reference engine uses `jaq` (Rust jq).

### `nika:json_diff`
```yaml
invoke: { tool: "nika:json_diff", args: { before: { ... }, after: { ... } } }
```
JSON diff · returns **RFC 6902** JSON Patch. (jq can't diff.)

### `nika:validate` · schema validation (json OR yaml)
```yaml
invoke: { tool: "nika:validate", args: { data: { ... }, schema: { type: object, ... }, format: json } }
# format: json (default · validate a value) | yaml (parse a YAML string first, then validate)
```
Validate data against a **JSON Schema** · returns `{ valid: bool, errors: [...] }`. Merges the former `json_verify` + `yaml_validate` (`format:` arg · one validator).

### `nika:json_merge_patch`
```yaml
invoke: { tool: "nika:json_merge_patch", args: { target: { ... }, patch: { ... } } }
```
**RFC 7396** merge patch (`null` deletes a key) · the delete-on-null semantics jq's `*` recursive-merge does NOT provide (so this stays a genuine builtin). Plain recursive merge (no delete) is just `jq '.[0] * .[1]'` on a `[base, overlay]` input · no builtin needed.

### `nika:csv_to_json`
```yaml
invoke: { tool: "nika:csv_to_json", args: { csv: "name,age\nAlice,30", has_header: true } }
```
Parse CSV (quoting-aware) → JSON array. (CSV parsing is not jq's job · the reverse direction is `jq @csv`.)

### `nika:uuid`
```yaml
invoke: { tool: "nika:uuid", args: { version: v7 } }   # v7 default (timestamped/sortable · RFC 9562) | v4 (random)
```
Generate a UUID. (Generators are not jq · jq is pure transform.)

### `nika:date`
```yaml
invoke: { tool: "nika:date", args: { op: now } }
# op: now { tz } | add { base, duration } | subtract | format { input, format } | parse | diff { start, end, unit }
```
Timestamp arithmetic · op-discriminated single builtin · timezone-aware (IANA · default UTC) · ISO 8601 out.

### `nika:hash`
```yaml
invoke: { tool: "nika:hash", args: { algo: blake3, content: "${{ tasks.X.output }}", encoding: hex } }
```
Content hashing · default **blake3** (fastest modern cryptographic hash · parallel · secure) · or `sha256`/`sha512`. md5/sha1 NOT supported (cryptographically broken). Use cases · cache keys · content addressing · provenance.

---

## Network builtins (2)

### `nika:fetch`
HTTP request + content extraction (reached via `invoke:` — fetching a URL is *calling a tool*, not a verb · see `02-verbs.md`).
```yaml
invoke: { tool: "nika:fetch", args: { url: "https://example.com/article", mode: article } }
```
| Arg | Notes |
|---|---|
| `url` | required · may use `${{ ... }}` |
| `method` | `GET` (default) · `POST` · `PUT` · `DELETE` · `PATCH` · `HEAD` |
| `headers` · `body` | extra headers · body (objects auto-JSON) |
| `mode` | extraction mode · see `extract-modes-v0.1.md` · default `markdown` |
| `jq` | a jq expression · only with `mode: jq` (structured JSON extraction · replaces the former JSONPath mode) |

**Security (engine MUST)** · SSRF defense (reject private-net + cloud-metadata `169.254.169.254` unless configured) · honor task-level `timeout` · reject self-signed TLS by default.

### `nika:notify`
```yaml
invoke: { tool: "nika:notify", args: { channel: webhook, target: "https://hooks.slack.com/...", message: "Done · ${{ tasks.X.status }}", severity: info } }
```
Send notifications · `channel:` enum (`webhook`/`slack`/`email`/`discord`/`sms` · one builtin not 5). v0.81 engine MUST support `webhook` · others MAY be feature-gated (`NIKA-BUILTIN-NOTIFY-001` if unconfigured).

---

## Introspection builtins (4)

### `nika:cost`
`invoke: { tool: "nika:cost" }` → `{ total_usd, by_task, by_provider }`. Running workflow cost.

### `nika:records`
`invoke: { tool: "nika:records" }` → `{ tasks: [{ id, status, duration_ms, ... }] }`. Full execution record. (Per-task status is read directly via the `${{ tasks.X.status }}` namespace — no separate `task_status` builtin.)

### `nika:dag_info`
`invoke: { tool: "nika:dag_info" }` → `{ nodes, edges, waves }`. DAG topology.

### `nika:threads`
`invoke: { tool: "nika:threads" }` → `{ active, queued, completed }`. Engine task-pool state.

---

## What jq subsumes (cut from v0.1)

These 13 former builtins are **expressible in `nika:jq`** (jaq-verified) · cut to
keep ONE data language (« no two ways to transform data »). Canonical recipes ·

| Former builtin | jq recipe |
|---|---|
| `nika:map` | `map(EXPR)` |
| `nika:filter` | `map(select(EXPR))` |
| `nika:group_by` | `group_by(.key)` |
| `nika:aggregate` | `map(.val) \| add` |
| `nika:enrich` | `. + { fetched_at: $now }` |
| `nika:chunk` | `[range(0; length; N) as $i \| .[$i:$i+N]]` |
| `nika:flatten` (object dot-path) | `[leaf_paths as $p \| {($p\|join(".")): getpath($p)}] \| add` |
| `nika:unflatten` | `reduce to_entries[] as $e (.; setpath($e.key/"."; $e.value))` |
| `nika:inject` (template) | `"Hello \(.name), age \(.age)"` (string interpolation) |
| `nika:base64_encode` / `_decode` | `@base64` / `@base64d` |
| `nika:json_to_csv` | `@csv` |
| `nika:json_merge` (recursive `*`) | `.[0] * .[1]` on a `[base, overlay]` input (jaq `obj_merge` · source-verified 2026-05-27) |

Also cut · `nika:task_status` (use `${{ tasks.X.status }}`) · `nika:orchestrate`
(use `for_each` for bounded fan-out · sub-workflow composition is deferred per
`08-out-of-scope.md`) · `nika:locale_lookup` (niche i18n → stdlib-extended).

---

## Media builtins · DEFERRED to stdlib v0.x

Not enumerated in v0.1 (feature-flag in the reference engine · MAY graduate as a
separate doc). Deliberate « less but better » (Rams 10).

---

## Cross-builtin invariants

A v0.1-compliant builtin · takes a single `args` object · returns a
JSON-serializable value · reports errors as typed `NIKA-BUILTIN-NNN` codes ·
honors task-level `timeout` · respects engine security policies.

---

## Forward-compat

New builtins MAY enter stdlib v0.x. Builtin removal is never allowed within a
stdlib v0.x lifetime (removal requires a new stdlib major). The v0.1 → 26
consolidation happened **pre-public** (0 external users · before the forever-clock).

---

🦋 *26 builtins canonical · jq = the data language · clear forever.*
