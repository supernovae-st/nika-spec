# 04 · Variables

> Nika uses **one substitution syntax everywhere** · `${{ ... }}` ·
> matching GitHub Actions. Inside strings · inside object values ·
> inside array elements · inside conditions. One syntax · one mental
> model.

---

## The one syntax · `${{ ... }}`

```yaml
# Inside a string
prompt: "Summarize · ${{ vars.topic }}"

# Inside a value position
with:
  data: ${{ tasks.research.output }}

# Inside a condition
when: ${{ tasks.test.status == 'success' }}

# Inside an array
tools:
  - ${{ vars.tool_a }}
  - ${{ vars.tool_b }}
```

If you have used GitHub Actions, this is the same. If you have not, the rule is simple · **anywhere you want a value resolved at task dispatch time, wrap it in `${{ }}`**.

**What's inside `${{ }}` is [CEL](https://cel.dev)** (Common Expression
Language · the validated, non-Turing-complete standard used by Kubernetes,
Envoy, and gRPC). A bare reference like `${{ vars.topic }}` is a CEL identifier
path that evaluates to its value; a condition like `${{ tasks.test.coverage > 80 }}`
is a CEL boolean. One expression language, everywhere — Nika does not invent a
DSL. See [03-dag.md](./03-dag.md#expression-language--a-documented-subset-of-cel) for the v0.1 CEL subset.

---

## The 5 namespaces

```
${{ vars.X }}             workflow inputs               (declared in envelope `vars:` · untyped or typed)
${{ with.X }}             task-level scope               (declared per-task `with:` block)
${{ tasks.X.output }}      task output reference          (or .status · .error · .duration_ms)
${{ env.X }}              environment variable           (non-sensitive runtime config)
${{ secrets.X }}          masked secret reference        (vault-backed · never in logs)
```

Five namespaces. That's it.

> **Loop-locals are not a 6th namespace.** Inside a `for_each` task body, two
> extra identifiers are in scope — `${{ item }}` (the current element) and
> `${{ index }}` (its 0-based position). They are **loop-scoped locals**, alive
> only within that task's body — not global namespaces. So the count stays
> « 5 namespaces » + the for-each locals where a loop is present.

### `${{ vars.X }}` · workflow inputs

Declared once in the envelope · immutable across the workflow run · may be
**untyped** (the value is the default) or **typed** (enables validation +
schema generation for callable workflows · see [01-envelope.md](./01-envelope.md#vars--optional--workflow-inputs--untyped-or-typed)) ·

```yaml
nika: v1
workflow: research-pipeline

vars:
  topic: "Rust async runtimes 2026"    # untyped · value is the default
  output_dir: "./output"

tasks:
  - id: research
    infer:
      prompt: "Research · ${{ vars.topic }}"
```

### `${{ with.X }}` · task-level scope

Declared per-task · resolves at task dispatch time · often references upstream task outputs ·

> **`with:` is optional sugar.** You can always reference `${{ tasks.X.output }}`
> directly inside any verb field. `with:` exists to (a) pre-bind + **alias**
> upstream values to short local names for readable prompts/commands, and (b)
> make a task's inputs explicit at a glance. Use it when it helps readability;
> skip it when a direct `${{ tasks.X.output }}` is clearer.

```yaml
- id: summarize
  depends_on: [research]
  with:
    content: ${{ tasks.research.output }}
    style: "concise"
  infer:
    prompt: "Summarize in ${{ with.style }} style · ${{ with.content }}"
```

### `${{ tasks.X.output }}` · task output reference

Reference any upstream task's output (or status · error · duration_ms) ·

```yaml
- id: deploy
  depends_on: [build, test]
  when: ${{ tasks.test.status == 'success' && tasks.test.output.coverage > 80 }}
  exec:
    command: "./deploy.sh ${{ tasks.build.output.artifact_path }}"
```

Implicit properties on every task ·

```
${{ tasks.X }}                       whole output (alias for tasks.X.output)
${{ tasks.X.output }}                the typed output
${{ tasks.X.status }}                success | failure | skipped | cancelled
${{ tasks.X.error }}                 error structure (present if status == failure)
${{ tasks.X.duration_ms }}           execution time
```

### `${{ env.X }}` · environment variable

```yaml
env:
  LOG_LEVEL: info
infer:
  prompt: "Running at ${{ env.LOG_LEVEL }} verbosity"
```

`env` holds **non-sensitive** runtime config. Values may appear in logs +
traces. For anything secret, use `secrets:` (below) instead — never put a
credential in `env`.

### `${{ secrets.X }}` · masked secret reference

```yaml
secrets:
  api_key:
    source: vault
    key: prod/anthropic/api-key
headers:
  Authorization: "Bearer ${{ secrets.api_key }}"
```

A secret is always a **reference to a store** (the local `nika-vault` by
default), declared in the envelope `secrets:` block — never an inline
literal. The engine **masks** every resolved `secrets.X` value in logs,
traces, and journal events (it renders as `••••••`). This `env` / `secrets`
split is the modern secure-workflow default: non-sensitive config in `env`,
masked references in `secrets`.

---

## Output binding · `output:`

Use `output:` to define **named bindings** extracted from a task's raw response via a **jq expression** (the one data language). These bindings appear in the task's typed output and are referenced as `${{ tasks.X.<name> }}` ·

```yaml
- id: api_call
  invoke:
    tool: "nika:fetch"
    args:
      url: "https://api.example.com/v1/users"   # returns JSON · output: jq extracts
  output:
    user_count: ".data.users | length"
    first_user: ".data.users[0]"
    user_emails: ".data.users[].email"
```

Downstream ·

```yaml
- id: notify
  depends_on: [api_call]
  infer:
    prompt: |
      We have ${{ tasks.api_call.user_count }} users.
      Emails · ${{ tasks.api_call.user_emails }}
```

#### Raw output vs named bindings · dual-accessible

When a task has an `output:` block defining named bindings · downstream
access is **dual-accessible** ·

```yaml
- id: api_call
  invoke:
    tool: nika:fetch
    args: { url: "..." }
  output:
    body: .body
    status: .status
```

Downstream ·

```yaml
# Raw output (whole structure · pre-binding extraction)
${{ tasks.api_call.output }}             # full raw JSON · including all fields the verb returned

# Named bindings (defined in output: block above)
${{ tasks.api_call.body }}               # extracted via $.body
${{ tasks.api_call.status }}             # extracted via $.status
```

**Rules** ·
- `tasks.X.output` ALWAYS returns the raw output (unmodified value
  returned by the verb · before any binding extraction)
- `tasks.X.<name>` for any `<name>` declared in `output:` block returns
  the extracted jq result
- `<name>` collisions with reserved words `output` · `status` · `error` ·
  `started_at` · `ended_at` · `duration_ms` are forbidden at parse time
- If no `output:` block · only `tasks.X.output` is accessible (named
  bindings are an opt-in convenience)

### Path grammar · jq (the one data language)

Output binding uses a **jq expression** — the SAME jq as the `nika:jq` builtin.
Nika has ONE data extraction-and-transform language (jq), **not two**: the former
RFC 9535 JSONPath was dropped because jq is a superset (any JSONPath query + more)
and a workflow language must not force the author — or an LLM — to choose between
two extraction syntaxes (SOTA « one obvious way · ≤2 expression layers »). The two
expression layers are **CEL** (inside `${{ }}` · conditions + value substitution)
and **jq** (inside `output:` bindings + `nika:jq` · extraction + transform).
Reference engines use `jaq` (Rust jq) so paths behave identically everywhere.

v0.1 jq conformance subset (every engine MUST support) ·

```
.<name>                    object member
.<name>[<index>]           array index
.<name>[]                  iterate all elements (jq `.[]` · was JSONPath `[*]`)
.a.b.c                     deep path
. | map(...) | select(...) jq pipeline for reshaping / filtering
```

The subset above is the portability floor every engine MUST support. Full jq
(the `jaq` Rust impl · « full stdlib ») MAY be used — it is the single data
extraction-and-transform language (`output:` bindings + the `nika:jq` builtin).

---

## Resolution order

When a task is about to run · the engine resolves `${{ ... }}` references in this order ·

1. **Parse** the expression inside `${{ }}` (one of · `vars.X` · `with.X` · `tasks.X.field` · `env.X` · or a `when:` condition expression)
2. **Lookup** the value from the appropriate namespace
3. **Substitute** the value into the position
4. **Single-pass** · substitution result is NOT re-evaluated (no nested substitution)

If a reference is unresolved · the engine raises a `NIKA-VAR-001` (undefined variable) error.

---

## Escaping

To embed a literal `${{` in a string · use `\${{` (backslash escape). The engine MUST honor this.

```yaml
infer:
  prompt: "The syntax \\${{ var.x }} is how you reference variables."
```

(Note · YAML escaping of backslash · `\\` in double-quoted strings · `\` in single-quoted or block scalars.)

---

## Why one syntax everywhere

An earlier draft proposed two syntaxes (`$task_id` in value positions · `{{var}}` inside strings). That was a confusion source · v0.1 unifies on a single `${{ }}` syntax for everything.

Reasons ·

- **One mental model** · same syntax everywhere · low cognitive load (Rams principle 4 understandable)
- **GitHub Actions familiarity** · 30M+ developers already know `${{ ... }}`
- **Composable in any position** · strings · object values · array elements · conditions
- **Unique enough** · escape rarely needed
- **Future-proof** · GitHub Actions has extended this syntax for 8+ years without breaking change

---

## Forward-compat

The `${{ ... }}` substitution surface and the 5 namespaces are locked at v1. **Template pipe-filters (`${{ vars.x | json }}` · `| upper`) are NOT a growth path** (they would duplicate builtins + push CEL toward a string-DSL). Data transforms live in the `nika:jq` builtin; the `${{ }}` surface grows only with CEL-native features (macros `has`/`all`/`exists` · reserved · additive). jq is the single extraction-and-transform language (`output:` + `nika:jq`).

Out of scope for v0.1 (deferred · see [`08-out-of-scope.md`](./08-out-of-scope.md)) ·
- Expression language (no arithmetic in templates)
- User-defined functions in templates
- Multi-pass substitution

---

🦋 *Next · [05 · Errors](./05-errors.md)*
