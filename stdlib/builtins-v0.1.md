# Stdlib v0.1 · Builtins

> The canonical 36 builtins shipped with Stdlib v0.1-compliant engines.
> Invoked via `invoke: tool: "nika:<name>"`. Plus 24 media builtins
> deferred to stdlib v0.x (`opt-in feature flag`).

---

## The 5 builtin categories

| Category | Count v0.1 | Status |
|---|---|---|
| Core | 6 | Required for any execution |
| File | 5 | I/O primitives |
| Data | 19 | Transformation + validation |
| Introspection | 6 | Workflow self-awareness |
| Media | — | **Deferred to stdlib v0.x** (opt-in feature flag · cf §Out of scope) |
| **Total v0.1 stdlib** | **36** | |

A Stdlib v0.1-compliant engine MUST ship the 36 builtins.

**Changes vs initial draft** ·
- `nika:complete` **renamed** to `nika:done` (avoid overlap with agent verb completion semantics · 4-0 council vote)
- `nika:run` (nested workflow builtin) **REMOVED** · deferred per §Out of scope(stack-overflow/recursion concerns)
- Media builtins **enumeration removed** from this spec · still feature-flag available in reference engine but not in canonical stdlib v0.1

---

## Core builtins (6) · required for execution

### `nika:sleep`

```yaml
invoke:
  tool: "nika:sleep"
  args:
    duration_ms: 5000
```

Pause execution for N milliseconds.

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

## Data builtins (19)

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

The media builtins are NOT enumerated in v0.1. They exist in the reference engine under a feature flag · they MAY graduate to stdlib v0.x as a separate document · but the v0.1 spec stays focused on the 36 canonical builtins above.

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

🦋 *36 builtins canonical · 24 media deferred · clear forever.*
