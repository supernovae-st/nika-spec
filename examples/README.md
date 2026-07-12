# Examples · canonical Nika workflows

> The teaching corpus. **`01`–`07` is the path**: seven files, in order,
> covering the complete v0.1 construct space — an LLM (or a human)
> few-shot-prompted on these has seen every load-bearing pattern.
> Real jobs live in [`showcase/`](showcase/) (T1→T4); instantiable
> skeletons live in [`../templates/`](../templates/).

---

## The path · 01 → 07

```
examples/
├── 01-hello.nika.yaml             envelope · 1 infer task · local model (mock twin)
├── 02-parallel-fanout.nika.yaml   DAG fan-out + merge · depends_on · with
├── 03-exec-pipeline.nika.yaml     exec · capture:structured · timeout · when · on_finally
├── 04-schema-retry.nika.yaml      infer schema (JSON Schema) · retry · typed vars
├── 05-fetch-chain.nika.yaml       invoke nika:fetch · output: jq · on_error recover
├── 06-code-review.nika.yaml       agent loop · default-deny tools · max_turns · nika:done
└── 07-for-each-locales.nika.yaml  for_each · max_parallel · fail_fast · item/index
```

Together: all 4 verbs · `depends_on` · `when` · `for_each` (+
`max_parallel` + `fail_fast`) · `retry` · `on_error` · `on_finally` ·
`with` · `output:` jq bindings · `schema:` structured output · the 5
namespaces · `${{ item }}`/`${{ index }}` loop locals · tool refs.
The path is **complete** — new workflows join `showcase/` (real jobs)
or `../templates/` (skeletons), never this list.

## Every file promises

- `# SPDX-License-Identifier: Apache-2.0` header
- a top comment teaching WHAT it demonstrates and WHY it is shaped so
- a true `# Run ·` line — and a `# Needs ·` line whenever the file
  expects something from YOUR world (a file, a key, a live endpoint)
- v0.1 envelope (`nika: v1`) · stdlib v0.1 only · conformance-clean
  (one verb per task · snake_case ids · resolvable deps · no phantom tools)
- local-first models (`ollama/…` · `mock/echo` for the dry twin) — cloud
  providers appear as per-job swap hints, never as the default

## Run them

```bash
nika run examples/01-hello.nika.yaml                  # with the reference engine
nika run examples/01-hello.nika.yaml --model mock/echo  # zero-setup dry twin
```

---

🦋 *The 7-step path is complete and canonical for v0.1.0 GA · real jobs → `showcase/` · skeletons → `../templates/`.*
