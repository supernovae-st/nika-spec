# 08 · Out of scope for v0.1

> The 5 pillars are immutable forever. The stdlib evolves. But the
> following items are **deliberately deferred** from the v0.1 spec ·
> they will land in later spec versions OR stay forever out of scope.
>
> Explicit deferral is canon · prevents drift · prevents premature lock-in.

---

## Why explicit defer matters

Every workflow language faces pressure to grow features. Without an
explicit defer list · the spec accretes accidental complexity · the
"forever" commitment becomes "until next quarter".

This document is the canonical defer list. If you find yourself missing
a feature here · it is intentional · not a forgotten gap. Most of these
items are tracked in design discussions and may land in `nika.sh/v2` or
in stdlib v0.x extensions.

---

## Workflow composition · DEFERRED

### Multi-file workflows (`include:` · `import:`)

```yaml
# NOT supported in v0.1
import:
  - ./shared/auth.nika.yaml
tasks: ...
```

**Why deferred** · single-file workflows are simpler · linter/LSP works without resolving paths · examples are self-contained. Composition may land in v0.2 with explicit import grammar.

### Sub-workflow invocation · `nika:run` builtin · `import:`

```yaml
# NOT supported in v0.1
- id: sub
  workflow: ./subroutine.nika.yaml

# Also deferred · the nika:run builtin (previously proposed)
- id: sub
  invoke:
    tool: "nika:run"
    args:
      workflow: ./subroutine.nika.yaml
```

**Why deferred** · subroutine calling needs scope/binding rules that need thought · plus risks of stack overflow (recursion) and scheduler complexity. The proposed `nika:run` builtin is therefore deferred from v0.1 · use `exec: command: "nika run subroutine.yaml"` as the workaround.

Workaround in v0.1 · use `exec: command: "nika run subroutine.yaml"` to launch a sibling workflow process.

### Macros / templates

```yaml
# NOT supported in v0.1
macro retry_with_backoff:
  retry: { max_attempts: 5, backoff_ms: 1000 }

- id: task
  use_macro: retry_with_backoff
  invoke: { tool: "nika:fetch", ... }
```

**Why deferred** · macros are a powerful but dangerous primitive (expansion order · debugging · drift). Most needs are met by `with:` scope + structured retry. Revisit only if empirical demand emerges.

---

## Control flow · DEFERRED

> **Note** · bounded map iteration (`for_each:`) is **IN v1** — it ships as a
> task field, see [03-dag.md](./03-dag.md#for_each--optional--map-a-task-over-a-collection).
> What remains deferred is **unbounded** iteration (`while:`).

### Unbounded loops (`while:`)

```yaml
# NOT supported in v1 — unbounded iteration
- id: poll_until
  while: ${{ tasks.check.output.ready == false }}
  exec:
    command: "./check.sh"
```

**Why deferred** · unbounded loops break the « acyclic » guarantee of the DAG
and the static-analyzability that makes Core conformance possible (you cannot
bound the work statically). Workaround in v1 · use the `agent:` verb with a
tool + `max_turns` budget (bounded), OR `for_each:` over a known collection
(bounded fan-out).

### Goto / jumps

Never supported. Anti-pattern.

### Try / catch blocks

`on_error:` is the v0.1 mechanism. Block-scoped try/catch is deferred.

---

## Streaming · DEFERRED

### Streaming output binding

```yaml
# NOT supported in v0.1
- id: stream_chat
  infer:
    prompt: "..."
    stream: true
  output:
    chunks: $.stream                # not in v0.1
```

**Why deferred** · streaming semantics in a YAML/DAG model are tricky · tasks are nominally synchronous. Engines MAY stream internally as an implementation detail · workflows see the final assembled response.

### Pub/sub / event-driven workflows

```yaml
# NOT supported in v0.1
- id: listen
  subscribe: "events://orders.created"
```

**Why deferred** · v0.1 is finite-DAG. Long-running event listeners belong in the daemon layer or external orchestrators.

---

## Persistence · DEFERRED

### Scheduled execution (cron)

```yaml
# NOT supported in v0.1
schedule: "0 */6 * * *"             # every 6 hours
tasks: ...
```

**Why deferred** · scheduling is an engine-runtime concern · not a language concern. A conformant engine handles cron at runtime · workflows themselves stay schedule-agnostic.

### Workflow checkpointing / resumption

```yaml
# NOT supported in v0.1
checkpoint:
  after: [task_a, task_b]
  storage: sqlite://./checkpoints.db
```

**Why deferred** · persistence is an engine-runtime concern. A conformant engine handles this internally · workflows don't declare it.

### Workflow versioning / migration

If a workflow needs to be re-runnable across spec versions · use a version
pin in the envelope (`nika: v1` already does this for the language contract). Per-workflow stdlib version pinning may land in v0.2.

### Idempotency keys / step deduplication

```yaml
# NOT supported in v0.1
- id: charge
  idempotency_key: "${{ vars.order_id }}"   # dedup retried side effects
  invoke: { tool: "mcp:stripe/charge", args: { ... } }
```

**Why deferred** · idempotency keys are **table-stakes for the durable-execution
class** (Temporal · Inngest · Restate · at-least-once delivery systems) — but
**not** for a finite single-run DAG (GitHub Actions · Argo single-run have no
idempotency keys either). They earn their keep alongside **durable execution +
resumption** (retries that survive a process restart), which is itself deferred
(engine/daemon · v0.3). A v0.1 `retry:` re-runs in-process · a side-effecting
task handles its own dedup via its tool args. Idempotency lands in v0.2
together with the durable-execution waypoint · NOT before. *(2025-2026 SOTA
gap-check · the only near-universal capability v1 lacks · and it is correctly
durable-class, not finite-DAG-class.)*

---

## The Connectome · DEFERRED capability · NOT a deferred verb

### Cognitive recall in workflows

```yaml
# The CAPABILITY is deferred (engine waypoint) · the SHAPE is already decided
- id: recall
  invoke:
    tool: "nika:connectome/recall"
    args:
      query: "Previous conversations about · ${{ vars.topic }}"
      top_k: 5
```

**No 6th verb — ever.** When the Connectome (the engine's cognitive subsystem)
ships, recall and ingest are exposed as **builtin tools under
`invoke:`** — `nika:connectome/recall` · `nika:connectome/ingest` — NOT as a
new verb. The 4 verbs are absolute: a new verb would
require a `nika: v2` contract, which forever-v0.x makes effectively never. So
the *shape* of cognitive access is already final today; only the *capability*
waits on the engine.

For v1 today · workflows that need recall use `invoke: mcp:memory-server/recall`
with an external MCP memory server, then swap the tool id to
`nika:connectome/recall` when the native Connectome admits — zero workflow-shape
change (same `invoke:` verb).

---

## Advanced agent features · DEFERRED

### Multi-agent coordination (supervisor / worker)

```yaml
# NOT supported in v0.1
agents:
  supervisor:
    role: "Plan and delegate"
  workers:
    type: pool
    count: 3
    role: "Execute tasks"
```

**Why deferred** · multi-agent topology is hard to standardize. The v0.1 `agent:` verb is single-loop. Patterns like supervisor/worker can be expressed in v0.1 via multiple `agent:` tasks with explicit hand-off via `with:` scope.

### Persistent agent state across workflow runs

```yaml
# NOT supported in v0.1
- id: ongoing
  agent:
    persistent_state_id: "user-123"
```

**Why deferred** · ties into memory subsystem.

---

## Tooling extensibility · STDLIB v0.x

### 24 media builtins

`pdf_extract` · `svg_render` · `chart` · `phash` · `compare` · `optimize` · `provenance` · `qr_validate` · `thumbhash` · `dominant_color` · `image_diff` · `import` · `thumbnail` · `provenance_verify` · `text_extract` · `ocr` · `transcribe` · `tts` · `mediainfo` · `dimensions` · `colorize` · `palette_extract` · `qr_generate` · `barcode`

**Why deferred** · 24 builtins is a third of the total builtin surface · they target a specific audience (media pipelines). Splitting them into stdlib v0.x reduces v0.1 scope by ~40% without losing core capability.

The reference engine ships them (opt-in feature flag) but they don't count toward Stdlib v0.1 conformance.

### Pluggable provider adapters

```yaml
# NOT supported in v0.1
providers:
  custom_xyz:
    type: openai-compatible
    base_url: "https://custom.example.com/v1"
```

**Why deferred** · provider config belongs in engine config · not in workflow YAML. v0.2 may introduce a `provider_config:` envelope field for openai-compatible custom endpoints.

### MCP server dependency declaration (`requires_mcp:`)

```yaml
# NOT supported in v0.1
requires_mcp: [postgres, browser]    # engine pre-flight-validates these servers exist
tasks: ...
```

**Why deferred** · a workflow references MCP tools by `mcp:<server>/<tool>` · the
server set lives in **engine config** (like provider config · not workflow YAML).
A `requires_mcp:` manifest would let the engine *pre-flight* (« no `postgres`
server configured » *before* the run) and document intent — but it is a
convenience, **not a v0.1 incompleteness** · a missing server already fails with
a clear `NIKA-MCP` error at first call. Single-file v0.1 stays free of
external-resolution declarations (the same rationale that defers `import:`).
May land in v0.2 alongside the composition / import grammar.

---

## Observability · DEFERRED

### OpenTelemetry export

Not in language spec. Engines MAY emit OpenTelemetry traces · this is engine concern · not workflow concern.

### Cost tracking annotations

```yaml
# NOT supported in v0.1
budget:
  max_cost_usd: 1.00
  warn_at_pct: 80
```

**Why deferred** · budget enforcement is engine concern · the `nika:cost` introspection builtin gives workflows access to running cost. Hard caps may land in v0.2.

---

## Multi-workflow orchestration · NEVER (separate language)

Pipeline-of-workflows orchestration · cross-workflow dependencies · workflow registries · service mesh integration · ALL out of scope **forever**. Nika is a single-workflow language. Multi-workflow orchestration is a different problem (cf Temporal · Airflow · etc.).

If you need that · the reference engine's HTTP server exposes a per-workflow run API · build your orchestrator on top of it.

---

## Why this list exists

The defer list is canonical · grep-able · forever. Future contributors who think "should we add X?" can check this doc · X is either ·

- (a) explicitly deferred · with rationale · won't enter v0.1
- (b) absent from this doc · meaning it's never been considered · open an issue

This is the spec's structural protection against feature creep · Rams principle 10 in literary form.

---

🦋 *End of the v0.1 spec. The 5 pillars are locked. The defer list is canon.*
