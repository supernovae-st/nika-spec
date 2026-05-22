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

---

## The 4 namespaces

```
${{ vars.X }}             workflow-level scope          (declared in envelope `vars:`)
${{ with.X }}             task-level scope               (declared per-task `with:` block)
${{ tasks.X.output }}      task output reference          (or .status · .error · .duration_ms)
${{ env.X }}              environment variable           (engine may restrict for security)
```

Four namespaces. That's it.

### `${{ vars.X }}` · workflow-level scope

Declared once in the envelope · immutable across the workflow run ·

```yaml
apiVersion: nika.sh/v1
workflow: research-pipeline

vars:
  topic: "Rust async runtimes 2026"
  output_dir: "./output"

tasks:
  - id: research
    infer:
      prompt: "Research · ${{ vars.topic }}"
```

### `${{ with.X }}` · task-level scope

Declared per-task · resolves at task dispatch time · often references upstream task outputs ·

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
headers:
  Authorization: "Bearer ${{ env.API_TOKEN }}"
```

The engine MAY restrict environment access (security policy).

---

## Output binding · `output:`

Use `output:` to define **named bindings** extracted from a task's raw response via **full JSONPath**. These bindings appear in the task's typed output and are referenced as `${{ tasks.X.<name> }}` ·

```yaml
- id: api_call
  fetch:
    url: "https://api.example.com/v1/users"
    mode: jsonpath
    jsonpath: "$"
  output:
    user_count: "$.data.users.length"
    first_user: "$.data.users[0]"
    user_emails: "$.data.users[*].email"
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

### Path grammar

JSONPath subset (v0.1 conformance) ·

```
$                          root
.<field>                   object field
[<index>]                  array index
[*]                        array wildcard
..                         recursive descent (optional engine support)
```

A v0.1-compliant engine MUST support the first four. Recursive descent is optional.

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

Earlier draft of this spec proposed two syntaxes (`$task_id` in value positions · `{{var}}` inside strings). User feedback during v0.1 design surfaced this as a confusion source. Pantheon council (Jobs · Rams · Hykes · Carmack lenses · 2026-05-22) ratified unanimous unification to `${{ }}`.

Reasons ·

- **One mental model** · same syntax everywhere · low cognitive load (Rams principle 4 understandable)
- **GitHub Actions familiarity** · 30M+ developers already know `${{ ... }}`
- **Composable in any position** · strings · object values · array elements · conditions
- **Unique enough** · escape rarely needed
- **Future-proof** · GitHub Actions has extended this syntax for 8+ years without breaking change

---

## Forward-compat

The `${{ ... }}` substitution surface and the 4 namespaces are locked at v1. Additional template helpers (e.g. `${{ vars.x | json }}` · `${{ vars.x | upper }}`) MAY be added in minor bumps. JSONPath grammar MAY extend (e.g. filters `?(@.field == value)`).

Out of scope for v0.1 (deferred · see [`08-out-of-scope.md`](./08-out-of-scope.md)) ·
- Expression language (no arithmetic in templates)
- User-defined functions in templates
- Multi-pass substitution

---

🦋 *Next · [05 · Errors](./05-errors.md)*
