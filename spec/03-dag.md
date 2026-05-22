# 03 · DAG shape

> A Nika workflow is a **Directed Acyclic Graph** of tasks. Each node is a
> task (one of the 5 verbs). Each edge is a dependency.
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
- id: my-task                   # required · kebab-case · unique within workflow
  depends_on: [task_a, task_b]  # optional · default []
  when: ${{ tasks.task_a.status == 'success' }}  # optional · conditional execution
  retry:                        # optional · retry policy (see 05-errors.md)
    max_attempts: 3
    backoff_ms: 1000
  on_error:                     # optional · error recovery (see 05-errors.md)
    fallback: "$cached_data"
  timeout_ms: 60000             # optional · task-level timeout
  with:                         # optional · variable scope injection
    data: $task_a
    config: { foo: "bar" }
  infer:                        # required · one of the 5 verbs
    prompt: "..."
  output:                       # optional · output binding
    result: "$.choices[0].message.content"
    tokens: "$.usage.total_tokens"
```

---

## Field-by-field

### `id` · **required · kebab-case · unique**

```yaml
- id: research-topic
```

Match · `^[a-z][a-z0-9_-]*$`. Must be unique within the workflow file.

Underscores **and** hyphens allowed (kebab + snake), but pick one style per workflow for readability.

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

#### Expression grammar (custom minimal DSL · v0.1)

Per pantheon council ratification (2026-05-22 · D-2026-05-22-N8) the `when:` expression language is a **small custom DSL** · NOT jq · NOT jsonpath-filter · NOT a full expression language. The rationale · keep the surface tiny so engines have no parser drift and workflows stay grep-able.

The grammar (closed at v1) ·

```
expr        := literal
            |  reference
            |  expr binary_op expr
            |  unary_op expr
            |  ( expr )

literal     := boolean | number | string         # true · false · 42 · "foo"
reference   := ${{ namespace.path }}              # vars.x · with.x · tasks.X.field · env.X

binary_op   := == | != | < | <= | > | >= | && | ||
unary_op    := !

string      := single or double quoted
number      := integer or decimal
```

That's the full grammar. No arithmetic · no function calls · no regex · no string operators (use `==` for equality only). If you need richer logic · do it in a `nika:assert` task or in an `infer:` task that returns a boolean.

A boolean expression wrapped in `${{ ... }}`. If `false`, the task is **skipped** (not failed). Skipped tasks have status `skipped` · downstream tasks see them as if they completed.

Common patterns ·

```yaml
when: ${{ tasks.build.status == 'success' }}
when: ${{ tasks.test.output.coverage > 80 }}
when: ${{ vars.env == 'production' }}
when: ${{ tasks.a.status == 'success' && tasks.b.status == 'success' }}
when: ${{ !(tasks.test.status == 'failure') }}
```

A v0.1-compliant engine MUST implement this DSL canonically · NOT engine-specific. The conformance suite verifies this.

### `timeout_ms` · *optional · task-level timeout*

```yaml
- id: long-task
  timeout_ms: 300000        # 5 minutes
  exec:
    command: "./long-running.sh"
```

Hard timeout for the entire task (including any retries). If exceeded · task fails with a typed timeout error.

### `with` · *optional · variable scope injection*

```yaml
- id: summarize
  depends_on: [research]
  with:
    content: $research                # task output reference
    style: "concise"                  # literal value
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
  fetch:
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
      a: $analyze_a
      b: $analyze_b
      c: $analyze_c
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

---

## Forward-compat

v0.1 ships with these task fields · `id` · `depends_on` · `when` · `retry` · `on_error` · `timeout_ms` · `with` · `output` · plus the verb selector. Additional fields may be added in minor schema bumps (additive only).

Out of scope for v0.1 · `parallel:` for explicit parallelism control · `loop:` / `for_each:` constructs · `include:` for sub-workflow composition. See [08-out-of-scope.md](./08-out-of-scope.md).

---

🦋 *Next · [04 · Variables](./04-variables.md)*
