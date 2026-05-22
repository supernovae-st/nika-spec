# 03 · DAG shape

> A Nika workflow is a **Directed Acyclic Graph** of tasks. Each node is a
> task (one of the 4 verbs). Each edge is a dependency.
>
> The DAG semantics are minimal · `depends_on` for order · `when` for
> conditional execution · output binding via JSONPath.

---

## Minimal DAG

```yaml
tasks:
  - id: a
    infer:
      prompt: "First"

  - id: b
    depends_on: [a]
    infer:
      prompt: "Second, after a"
```

`b` runs after `a` completes. If `a` fails (and no `on_error:` recovery), `b` does not run.

---

## Task shape · full

```yaml
- id: my_task                   # required · snake_case · unique within workflow
  depends_on: [task_a, task_b]  # optional · default []
  when: ${{ tasks.task_a.status == 'success' }}  # optional · conditional execution
  for_each: ${{ tasks.list.output }}  # optional · map this task over a collection
  retry:                        # optional · retry policy (see 05-errors.md)
    max_attempts: 3
    backoff_ms: 1000
  on_error:                     # optional · error recovery (see 05-errors.md)
    fallback: ${{ tasks.cache.output }}
  timeout: "60s"                # optional · task-level timeout (Go duration string)
  with:                         # optional · variable scope injection
    data: ${{ tasks.task_a.output }}
    config: { foo: "bar" }
  infer:                        # required · one of the 4 verbs
    prompt: "..."
  output:                       # optional · named JSONPath bindings
    result: "$.choices[0].message.content"
    tokens: "$.usage.total_tokens"
  output_format: structured     # optional · text | structured | bytes · default inferred
```

---

## Field-by-field

### `id` · **required · snake_case · unique**

```yaml
- id: research_topic
```

Match · `^[a-z][a-z0-9_]*$` (snake_case · no hyphens). Must be unique within
the workflow file.

**Why snake_case, not kebab** · task ids are referenced in CEL expressions as
`tasks.<id>.output`. In CEL (and almost every expression language) a hyphen is
the **subtraction operator** — `tasks.research-topic.output` would parse as
`tasks.research - topic.output`, a silent trap. Snake_case ids are always
clean CEL identifiers. (The workflow-level `workflow:` id stays kebab-case —
it is a resource name, never referenced inside an expression.)

### `depends_on` · *optional · default `[]`*

```yaml
- id: c
  depends_on: [a, b]
```

A list of task ids this task depends on. The engine MUST not start this task until ALL deps have completed (successfully OR with a recovered error via `on_error:`).

**Cycle detection** · the engine MUST reject any workflow with cyclic dependencies at parse time with a clear error.

**Parallel execution** · tasks with no deps between them MAY run in parallel. This is the default behavior · the engine SHOULD parallelize wherever possible.

### `when` · *optional · conditional execution*

```yaml
- id: notify
  depends_on: [build]
  when: ${{ tasks.build.status == 'success' }}
  exec:
    command: "./notify.sh"
```

#### Expression language · a documented subset of CEL

Everything inside `${{ ... }}` — both value substitution and `when:`
conditions — is **[CEL](https://cel.dev) (Common Expression Language)**, the
validated, non-Turing-complete, side-effect-free expression standard used by
Kubernetes (ValidatingAdmissionPolicy), Kyverno, Envoy, and gRPC. Nika does
**not** invent an expression DSL — it adopts the standard. (This supersedes the « custom minimal DSL » framing.)

**Why CEL** · it is *common* (millions of K8s users), *comprehensible*
(reads like a boolean expression), *validated* (a published spec + multiple
conformant implementations), *safe* (non-Turing-complete · bounded · no side
effects) and *portable* (zero parser drift between engines). A hand-rolled
DSL would be none of those.

**The v0.1 subset** (the only CEL features a conformant engine must support) ·

```
identifier / field access   vars.topic · tasks.build.status · with.content
index access                tasks.list.output[0] · obj['key-with-dash']
comparison                  == · != · < · <= · > · >=
boolean                     && · || · !
membership                  in            (e.g. status in ['success','skipped'])
literals                    true · false · 42 · 3.14 · 'str' · "str" · null
grouping                    ( … )
```

Arithmetic, CEL macros (`has()`, `all()`, `exists()`), and string functions
are **reserved** — not in the v0.1 subset, addable in a later minor (CEL is a
superset, so growth is additive and never breaking). If you need richer logic
today, compute it in a `nika:assert` builtin or an `infer:` task.

**Namespaces are CEL variables** · the 5 namespaces (`vars` · `with` · `tasks`
· `env` · `secrets`) are bound as top-level CEL variables. `tasks.<id>.status`
etc. resolve against the live DAG state.

#### Referencing a task requires an explicit `depends_on`

If a task's `when:` **or** `with:` references `tasks.<id>` (any field), that
task **MUST** declare `<id>` in its `depends_on:`. The engine **rejects the
workflow at parse time** otherwise (`validation_error` · `NIKA-DAG` namespace) —
it does **not** silently infer the edge.

```yaml
# ❌ REJECTED at parse — `when:` reads tasks.test but no depends_on
- id: deploy
  when: ${{ tasks.test.status == 'success' }}
  exec: { command: "./deploy.sh" }

# ✅ CORRECT — the reference is backed by an explicit edge
- id: deploy
  depends_on: [test]
  when: ${{ tasks.test.status == 'success' }}
  exec: { command: "./deploy.sh" }
```

**Why explicit, not inferred** · an inferred edge is an invisible edge — it
makes the DAG harder to read and lets a typo (`tasks.tset`) silently change
ordering. Requiring the declaration keeps the graph honest: every dependency
is visible in `depends_on`, and a dangling reference is a loud parse error, not
a race. (This is the one rule an LLM most often gets wrong — so it fails fast.)

**Implementation** · an engine MAY embed a CEL library (e.g. the Rust
`cel-interpreter` crate) OR hand-roll the small v0.1 subset above — both are
conformant because the subset is exactly CEL. The Core conformance suite tests
the subset against the CEL spec.

A `when:` expression evaluates to a boolean. If `false`, the task is
**skipped** (not failed) · status `skipped` · downstream sees it as completed.

Common patterns ·

```yaml
when: ${{ tasks.build.status == 'success' }}
when: ${{ tasks.test.output.coverage > 80 }}
when: ${{ vars.env == 'production' }}
when: ${{ tasks.a.status == 'success' && tasks.b.status == 'success' }}
when: ${{ tasks.deploy.status in ['success', 'skipped'] }}
when: ${{ !(tasks.test.status == 'failure') }}
```


### `when:` · *MUST be a CEL boolean expression*

```yaml
- id: send_alert
  when: ${{ tasks.check.alert_count > 0 }}     # CEL expression evaluating to bool
  invoke: { ... }
```

The engine **rejects non-boolean `when:` expressions at parse time**
(`NIKA-PARSE-WHEN-001`).

**Valid** · expressions that return a bool ·
```yaml
when: ${{ vars.env == "production" }}          # bool comparison
when: ${{ tasks.upstream.status == "success" }}
when: ${{ tasks.scan.alerts.size() > 0 }}
when: ${{ vars.dry_run == false && tasks.check.passed }}
when: ${{ tasks.X.output != null }}            # null check
```

**Invalid** · rejected at parse time ·
```yaml
when: ${{ vars.threshold }}                    # ❌ returns integer · not bool
when: ${{ tasks.X.output }}                    # ❌ returns object · not bool
when: ${{ vars.message }}                      # ❌ returns string · not bool
when: "literal string"                          # ❌ not a ${{ }} expression
```

For non-boolean values · use explicit comparison ·
```yaml
when: ${{ vars.threshold > 0 }}                # explicit > comparison
when: ${{ vars.message != "" }}                # empty string check
when: ${{ size(vars.items) > 0 }}              # collection size check
```

---

### `for_each` · *optional · map a task over a collection*

```yaml
- id: scrape_all
  for_each: ${{ vars.urls }}                  # a static list OR a prior task's array output
  max_parallel: 5                              # optional · cap concurrent iterations · default unbounded
  fail_fast: false                             # optional · false = keep going on errors · default true
  with:
    page: ${{ item }}                          # ${{ item }} = the current element
  invoke:
    tool: nika:fetch
    args: { url: "${{ with.page }}" }
```

`for_each` runs the task **once per element** of the collection. Inside the
task body, `${{ item }}` resolves to the current element (and `${{ index }}`
to its zero-based position). The collection is either a literal list or a
reference to an upstream task's array output — this is the **matrix /
fan-out** pattern familiar from GitHub Actions.

#### ⚠️ Parallel by default

By default · `for_each` iterations run **in parallel** (engine spawns all
iterations concurrently · bounded by `max_parallel:` if set).

This is **different from Python's sequential `for` loop**. If you need
sequential iteration · set `max_parallel: 1` ·

```yaml
- id: process_in_order
  for_each: ${{ vars.items }}
  max_parallel: 1                              # iterations run one-at-a-time, in order
  exec:
    command: "process ${{ item }}"
```

#### `max_parallel:` · *optional · cap concurrent iterations*

```yaml
for_each: ${{ vars.urls }}     # 1000 URLs
max_parallel: 5                # at most 5 in-flight at any time
```

- **Default · unbounded** (subject to engine-wide concurrency budget · v0.3
  daemon adds workflow-level cap).
- **Positive integer** · `1` to `n`. `1` = sequential.
- **Engine impl** · `tokio::sync::Semaphore` (or equivalent) · iterations
  acquire a permit before executing · release on completion.
- **Use cases** · rate-limiting provider APIs · avoiding resource
  exhaustion · compliance with concurrency limits.

#### `fail_fast:` · *optional · abort-on-error policy*

```yaml
for_each: ${{ vars.urls }}
fail_fast: false                # default true · false = process all even if some fail
```

- **Default · `true`** · first iteration error aborts remaining iterations ·
  parent task transitions to `failed` status immediately.
- **`fail_fast: false`** · iteration errors are collected · remaining
  iterations keep running · parent task transitions to `failed` (with
  per-iteration error details) ONLY after all iterations complete.
- **Use cases** · « process N URLs · report which failed but don't abort »
  (false) vs « if any LLM call fails, the whole batch is invalid » (true).

#### Semantics (closed at v1)

- The task's output is the **array of per-iteration outputs**, in input
  order · referenced downstream as `${{ tasks.scrape_all.output }}`
  (an array) · `${{ tasks.scrape_all.output[0] }}` for one element.
- `for_each` is **bounded fan-out**, not recursion · a task cannot
  `for_each` over its own output. The DAG stays acyclic.
- If the collection is empty · the task is `skipped` (status `skipped`).
- `when:` is evaluated **once** before the fan-out · `retry:` /
  `on_error:` / `timeout:` apply **per iteration**.
- `max_parallel:` + `fail_fast:` apply uniformly across all iterations.
- `on_finally:` (see below) runs **once** after all iterations complete
  (success OR failure).

This is the one construct that lets a v1 workflow process a
runtime-computed number of items (N files · N search hits · N pages)
without statically enumerating tasks.

### `timeout` · *optional · task-level timeout (Go duration string)*

```yaml
- id: long_task
  timeout: "5m"             # 5 minutes
  exec:
    command: "./long-running.sh"
```

Hard timeout for the entire task (including any retries). If exceeded · task fails with a typed timeout error (`NIKA-TIMEOUT-001`).

**Format · Go-duration / Kubernetes-style string** `[0-9]+(\.[0-9]+)?(ns|us|µs|ms|s|m|h)`.

```yaml
timeout: "500ms"           # half a second
timeout: "30s"             # 30 seconds
timeout: "5m"              # 5 minutes
timeout: "1h30m"           # compound · 1.5 hours
timeout: "2.5s"            # fractional · 2500 ms
```

**Rules** ·
- MUST be a **quoted YAML string** · unquoted reject (`30s` unquoted parses as string OK but `30` unquoted parses as integer · ambiguous · forbidden).
- Positive · `> 0`.
- Maximum · `24h`. Tasks needing longer should split into a workflow chain.
- Compound units · combine in descending order (`1h30m500ms` ✓ · `30m1h` ✗).
- Unit suffixes (case-sensitive) · `ns` · `us` (or `µs`) · `ms` · `s` · `m` · `h`. No `d`/`w` (use compound · `48h` instead of `2d`).

**Why a duration string (not `timeout_ms: 30000`)** ·
- Industry standard · Go `time.ParseDuration` · Kubernetes resource limits · Prometheus rules.
- Reads naturally · `"5m"` beats `300000`.
- One field for all granularities · `ns` to `h`.
- Quoted-string requirement defeats YAML 1.2 numeric traps (Norway · sexagesimal · float drift).

### `with` · *optional · variable scope injection*

```yaml
- id: summarize
  depends_on: [research]
  with:
    content: ${{ tasks.research.output }}   # task output reference
    style: "concise"                        # literal value
    config:                           # nested object
      max_words: 100
  infer:
    prompt: "Summarize · style ${{ with.style }} · ${{ with.content }}"
```

Injects variables into the task's scope. The variables are referenced
via `${{ with.<name> }}` substitution within the task body.

See [04-variables.md](./04-variables.md) for the full substitution grammar.

### `retry` · *optional · retry policy*

See [05-errors.md](./05-errors.md).

### `on_error` · *optional · error recovery*

See [05-errors.md](./05-errors.md).

### `output` · *optional · output binding*

```yaml
- id: api_call
  invoke:
    tool: "nika:fetch"
    args:
      url: "https://api.example.com/data"
      mode: raw
  output:
    user_count: "$.data.users.length"
    first_user: "$.data.users[0]"
    raw: "$"
```

Defines named bindings extracted from the verb's raw response via JSONPath. These bindings are available downstream as `${{ tasks.task_id.user_count }}`, `${{ tasks.task_id.first_user }}`, etc.

If `output` is absent · the task output defaults to the verb's raw response, referenced as `${{ tasks.task_id.output }}`.

---

## DAG execution model

A v0.1-compliant engine MUST ·

1. **Parse** · validate envelope · validate task ids unique · validate verbs · validate `depends_on` references resolve
2. **Topology** · compute topological order · detect cycles · reject with error if cyclic
3. **Schedule** · group tasks into waves (each wave = tasks whose deps are all done) · execute each wave in parallel (engine MAY use a thread/task pool · configurable concurrency)
4. **Evaluate `when`** · before starting each task · skip if false
5. **Execute** · run the verb · capture output · bind via JSONPath
6. **Propagate** · on success · advance · on failure · honor `retry:` · then `on_error:` · then fail downstream
7. **Complete** · workflow done when all tasks reached terminal state (success · failure · skipped)

---

## Task states

| State | Meaning |
|---|---|
| `pending` | Task has not started · waiting on deps |
| `running` | Task is currently executing |
| `success` | Task completed successfully |
| `failure` | Task failed (after retries · no `on_error:` recovery) |
| `skipped` | Task was skipped (`when` evaluated false) |
| `cancelled` | Task was cancelled (workflow cancellation or upstream failure) |

A downstream task sees an upstream's status via `${{ tasks.task_id.status }}`. The default `depends_on` behavior is to run only when all deps have `success` or `skipped` status. To run regardless · use `when: true`.

---

## Examples

### Linear chain

```yaml
tasks:
  - id: a
    infer: { prompt: "Step 1" }
  - id: b
    depends_on: [a]
    infer: { prompt: "Step 2 · prev was ${{ with.prev }}" }
    with: { prev: ${{ tasks.a.output }} }
  - id: c
    depends_on: [b]
    infer: { prompt: "Step 3 · prev was ${{ with.prev }}" }
    with: { prev: ${{ tasks.b.output }} }
```

### Parallel fan-out

```yaml
tasks:
  - id: setup
    exec: { command: "./prepare.sh" }
  - id: analyze_a
    depends_on: [setup]
    infer: { prompt: "Analyze A" }
  - id: analyze_b
    depends_on: [setup]
    infer: { prompt: "Analyze B" }
  - id: analyze_c
    depends_on: [setup]
    infer: { prompt: "Analyze C" }
  - id: merge
    depends_on: [analyze_a, analyze_b, analyze_c]
    with:
      a: ${{ tasks.analyze_a.output }}
      b: ${{ tasks.analyze_b.output }}
      c: ${{ tasks.analyze_c.output }}
    infer:
      prompt: "Merge · ${{ with.a }} · ${{ with.b }} · ${{ with.c }}"
```

`analyze_a` · `analyze_b` · `analyze_c` run in parallel after `setup` · `merge` runs after all three.

### Conditional branch

```yaml
tasks:
  - id: check
    exec: { command: "./check-env.sh", capture: structured }

  - id: build_prod
    depends_on: [check]
    when: ${{ tasks.check.output.env == 'production' }}
    exec: { command: "./build.sh --release" }

  - id: build_dev
    depends_on: [check]
    when: ${{ tasks.check.output.env != 'production' }}
    exec: { command: "./build.sh --debug" }

  - id: deploy
    depends_on: [build_prod, build_dev]
    exec: { command: "./deploy.sh" }
```

Exactly one of `build_prod` or `build_dev` runs · the other is skipped · `deploy` runs after both (one success + one skipped).

### Map fan-out (`for_each`)

```yaml
tasks:
  - id: discover
    invoke:
      tool: "nika:fetch"
      args:
        url: "https://example.com/sitemap.xml"
        mode: sitemap
    output:
      pages: "$.urls[*]"

  - id: summarize
    depends_on: [discover]
    for_each: ${{ tasks.discover.pages }}
    with:
      page: ${{ item }}
    invoke:
      tool: "nika:fetch"
      args:
        url: ${{ with.page }}
        mode: article

  - id: digest
    depends_on: [summarize]
    with:
      summaries: ${{ tasks.summarize.output }}      # array of per-page outputs
    infer:
      prompt: "Write a digest from these summaries · ${{ with.summaries }}"
```

`discover` finds N pages · `summarize` runs once per page (parallel,
bounded) · `digest` consumes the array of all summaries. N is computed at
runtime — no static enumeration.

### `output_format` · *optional · type hint*

```yaml
- id: fetch_image
  invoke:
    tool: nika:fetch
    args:
      url: "https://example.com/diagram.png"
      mode: bytes
  output_format: bytes
```

Declares the **raw shape** of the task's output. Optional · default **inferred per verb** ·

| Verb | Default `output_format` |
|---|---|
| `infer:` (no `schema:`) | `text` (raw LLM response · string) |
| `infer:` (with `schema:`) | `structured` (validated JSON object/array) |
| `exec:` | `structured` (always `{stdout, stderr, exit_code}`) |
| `invoke:` | `structured` (tool-determined · check tool spec) |
| `agent:` | `structured` (always `{result, steps_taken, ...}`) |

**Closed enum** · `text` · `structured` · `bytes`.

**Why explicit override** ·
- **`bytes`** · the only way to declare binary output. Downstream consumers must be binary-aware (e.g. `nika:write` with `mode: binary` · NOT `${{ … }}` string substitution which would corrupt binary data with UTF-8 coercion).
- **`structured`** · forces validation that raw output is a JSON object/array. Catches the « text-leak » bug where a tool returns text when caller expected JSON.
- **`text`** · explicit string treatment · downstream `${{ … }}` substitution is verbatim.

**Conformance** · the engine MUST honor explicit `output_format:` and reject mismatches at parse time (structured demand on a text-only verb · etc.).

**Why a top-level task field (not nested inside `output:`)** ·
- `output:` is a **map of named JSONPath bindings** (existing semantics · downstream `${{ tasks.X.<name> }}` access).
- `output_format:` is a **type hint on the raw output** (before bindings extract from it).
- Two distinct concerns → two distinct fields → Rams 4 understandable.

### `on_finally` · *optional · cleanup hook · ALWAYS runs*

```yaml
- id: process
  exec:
    command: "./process.sh > /tmp/output.json"
  on_finally:                                  # runs always · success/fail/timeout/cancel
    - exec:
        command: "rm -f /tmp/output.json"
    - invoke:
        tool: nika:emit
        args: { event: "task_completed", task_id: "process" }
```

`on_finally:` declares **cleanup tasks** that run after the parent task
completes · REGARDLESS of outcome (success · failure · timeout · cancel).

#### Semantics (closed at v1)

- **List of mini-tasks** · zero or more · each with its own verb (`exec:` ·
  `invoke:` · or `infer:` · `agent:` rarely used here).
- **Runs sequentially** in declared order · cleanup-task-N starts after
  cleanup-task-(N-1) completes.
- **Cleanup errors are LOGGED but DO NOT propagate** · the parent task's
  final status reflects ONLY the main verb's outcome · NOT the cleanup
  outcomes (best-effort semantics).
- **Cleanup tasks have access to** `${{ tasks.<parent>.status }}` and
  `${{ tasks.<parent>.error }}` to branch behavior (e.g. only-on-error
  notification).
- **Default cleanup timeout** · 30 seconds per cleanup task (overridable
  per cleanup task via `timeout:` field).
- **Failed parent task's `on_finally:` runs BEFORE** the error propagates
  upward in the DAG (gives cleanup a chance to undo side effects).
- **Engine MUST execute** `on_finally:` on cancel (Ctrl+C) and timeout.
- **Engine MAY skip** `on_finally:` only if the workflow process itself
  crashes (SIGSEGV · OOM · hard kill).

#### Use cases

```yaml
# 1 · cleanup temp files
on_finally:
  - exec: { command: "rm -rf /tmp/workflow-${{ workflow_run_id }}" }

# 2 · always-emit completion event
on_finally:
  - invoke:
      tool: nika:emit
      args: { event: "task_done", status: "${{ tasks.process.status }}" }

# 3 · on-error notification only
on_finally:
  - when: ${{ tasks.process.status == 'failed' }}
    invoke:
      tool: nika:fetch
      args:
        url: "https://hooks.slack.com/..."
        method: POST
        body: { text: "Task failed · ${{ tasks.process.error }}" }
```

---

## Forward-compat

v1 ships with these task fields · `id` · `depends_on` · `when` · `for_each` · `max_parallel` · `fail_fast` · `retry` · `on_error` · `timeout` · `on_finally` · `with` · `output` · `output_format` · plus the verb selector. Additional fields may be added in minor bumps (additive only).

Out of scope for v1 · `parallel:` for explicit concurrency control · `include:` for sub-workflow composition (workaround · `exec: nika run sub.yaml`). See [08-out-of-scope.md](./08-out-of-scope.md).

---

🦋 *Next · [04 · Variables](./04-variables.md)*
