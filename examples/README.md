# Examples · canonical Nika workflows

> The teaching corpus. **`01`–`07` is the path**: seven files, read in order,
> each introducing one theme and using nothing a later file introduces.
> An author who reads two of them writes their next workflow green.
> Real jobs live in [`showcase/`](showcase/) (T1→T4); instantiable
> skeletons live in [`../templates/`](../templates/).
>
> The contract every file here honours is written down in
> [`CONVENTIONS.md`](CONVENTIONS.md). Read that before you add or edit one.

---

## The path · 01 → 07

| File | Theme | Introduces |
|---|---|---|
| [`01-hello`](01-hello.nika.yaml) | the complete minimum | `nika: v1` · `workflow.id` · `model:` · `permits: {}` · `infer:` · `max_tokens:` · `outputs:` |
| [`02-parallel-fanout`](02-parallel-fanout.nika.yaml) | the DAG | implicit parallelism · `const:` · `with:` value edges · `${{ tasks.<id>.output }}` |
| [`03-exec-pipeline`](03-exec-pipeline.nika.yaml) | shells and gates | `exec:` (`shell:` + `command:`) · `capture: structured` · `timeout:` · `run.clock` · `when:` · `after:` control edges · `on_finally:` |
| [`04-schema-retry`](04-schema-retry.nika.yaml) | typed calls | typed `inputs:` + `default:` · `infer.schema:` · `additionalProperties: false` · `retry:` · the long `outputs:` form |
| [`05-fetch-chain`](05-fetch-chain.nika.yaml) | reaching outside | `invoke:` · `nika:fetch` · `permits.tools` + `permits.net.http` · `output:` jq bindings · `on_error: recover:` |
| [`06-code-review`](06-code-review.nika.yaml) | the agent loop | `agent:` · default-deny `tools:` · `max_turns:` + `max_tokens_total:` · `nika:done` · `permits.fs` inside the loop |
| [`07-for-each-locales`](07-for-each-locales.nika.yaml) | mapping | `for_each:` · `${{ item }}` / `${{ index }}` · `max_parallel:` · `fail_fast:` · array-preserving recovery |

All **4 verbs** appear: `infer` (01 · 02 · 04 · 05 · 07) · `exec` (03) ·
`invoke` (05) · `agent` (06). Everything callable is a tool under `invoke:`.

### What the path deliberately leaves out

Of the [6 value namespaces](../spec/04-variables.md) the path covers four —
`inputs` · `const` · `with` · `tasks`, plus the `item`/`index` loop locals.

`secrets:` and its `egress:` sanctions are **not** here on purpose: a secret
needs a real credential and a real host, which would cost every file in this
directory its zero-setup run. That subject belongs to a job with stakes —
see [`showcase/t2-support-triage`](showcase/t2-support-triage.nika.yaml) for
the reference shape (a secret that carries a webhook URL, an `egress:` that
sanctions the one send, and the `permits.net.http` that grants the reach —
you need both, and `CONVENTIONS.md` §3 explains why).

## Why some files name a real model and others do not

- **`ollama/qwen3.5:4b`** where the model IS the lesson — 01 (a real local
  call) and 06 (the loop needs a tool-calling model). Both say so on a
  `Needs ·` line.
- **`mock/echo`** where the SHAPE is the lesson — 02 · 04 · 05 · 07. The twin
  echoes each prompt back, which makes the graph visible in the output: you
  can read the three fan-out answers arriving inside the merge. Zero setup,
  deterministic, and `--model ollama/qwen3.5:4b` swaps a real model in
  without touching the file.

Cloud providers appear only as swap hints, never as a default.

## Every file promises

- `# SPDX-License-Identifier: Apache-2.0` + the `yaml-language-server` schema line
- a header that states the job, then `Demonstrates ·`, then `Needs ·`
  (**absent means: needs nothing**), then the exact `Run ·` command
- `nika check <file> --native-strict` → rc=0, **zero findings and zero hints**
- it has actually been RUN, and its `outputs:` parsed
- the tightest `permits:` block that covers the body — never widened to
  silence a message
- every comment true: measured, or citing a spec line

## Run them

```bash
nika run examples/01-hello.nika.yaml                     # as written
nika run examples/01-hello.nika.yaml --model mock/echo   # zero-setup dry twin
nika run examples/01-hello.nika.yaml --output json       # the typed outputs, as one JSON object
```

Run from the **repo root**: paths inside a workflow resolve against your
working directory, not the file's location. `06` reads a fixture from
[`fixtures/`](fixtures/) and expects exactly that.

---

🦋 *The 7-step path is canonical for v0.1.0 GA · real jobs → `showcase/` · skeletons → `../templates/`.*
