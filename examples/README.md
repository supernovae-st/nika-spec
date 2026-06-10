# Examples · canonical Nika workflows

> 26 canonical example workflows demonstrating the language. Each file
> is a complete, runnable workflow (with the reference engine) or a
> teaching example (with the `mock/` model) that doesn't require API keys.

---

## Status · 7 foundation examples shipped · 19 pending

The **7-example foundation set** (✅ below) is shipped — it covers the
*complete v0.1 construct space* so an LLM few-shot-prompted on these has seen
every load-bearing pattern: all 4 verbs · `depends_on` · `when` · `for_each`
(+ `max_parallel` + `fail_fast`) · `retry` · `on_error` · `on_finally` ·
`with` · `output:` jq binding · `schema:` structured output · the 5
namespaces · `${{ item }}`/`${{ index }}` loop locals · tool refs. This is the
**Phase L2 few-shot library** seed (per `nika/hq/blueprint/NIKA_EXECUTION_PHASES.md`):
the literal training signal that teaches an LLM to author Nika correctly.

The remaining 19 distill **26 workflows from an earlier Nika prototype** — the
empirical source of what real workflows look like — into a clean canonical set.

Every example · (a) matches the v0.1 envelope exactly (`nika: v1`) · (b) uses
only stdlib v0.1 inclusions · (c) carries an SPDX Apache-2.0 header · (d) is
authored to pass the conformance suite (YAML-parse + spec-lint verified ·
one-verb-per-task · snake_case ids · resolvable deps · zero phantom builtins).

## Shipped · the 7-example foundation set

```
examples/
├── 01-hello.nika.yaml            ✅  envelope · 1 infer task · mock model
├── 06-parallel-fanout.nika.yaml  ✅  DAG fan-out + merge · depends_on · with
├── 16-exec-pipeline.nika.yaml    ✅  exec · capture:structured · timeout · when · on_finally
├── 19-schema-retry.nika.yaml     ✅  infer schema (JSON Schema) · retry · typed vars
├── 22-fetch-chain.nika.yaml      ✅  invoke nika:fetch · output: jq · on_error recover
├── 23-code-review.nika.yaml      ✅  agent loop · default-deny tools · max_turns · nika:done
└── 26-for-each-locales.nika.yaml ✅  for_each · max_parallel · fail_fast · item/index
```

Together these exercise every v0.1 construct an LLM must learn to author Nika.

## Full planned set (26)

```
examples/
├── 01-hello.nika.yaml                    ✅ "Hello world" · 1 task · infer
├── 02-minimal.nika.yaml                  Most minimal workflow possible
├── 03-multi-provider.nika.yaml           Compare 3 providers on same prompt
├── 04-multi-locale.nika.yaml             Multi-language fan-out
├── 05-exec-only.nika.yaml                Workflow with only exec: verbs
├── 06-parallel-fanout.nika.yaml          ✅ DAG fan-out + merge
├── 07-mcp-invoke.nika.yaml               Call an MCP tool
├── 08-multi-locale-mcp.nika.yaml         Combine locale loop + MCP
├── 09-orchestrate-mock.nika.yaml         Use mock model for testing
├── 10-orchestrate-openai.nika.yaml       Use openai · structured output
├── 11-orchestrate-simple.nika.yaml       Sequential 3-task workflow
├── 12-provider-structured-parity.nika.yaml  Structured output across providers
├── 13-quickstart-mcp.nika.yaml           First MCP tool call
├── 14-quickstart-multilang.nika.yaml     Translation pipeline
├── 15-test-extended-thinking.nika.yaml   Anthropic extended thinking
├── 16-exec-pipeline.nika.yaml            ✅ exec · capture · when · on_finally (shipped name)
├── 17-test-file-output.nika.yaml         infer + nika:write
├── 18-test-full-pipeline-mcp.nika.yaml   End-to-end pipeline
├── 19-schema-retry.nika.yaml             ✅ structured output + retry (shipped name)
├── 20-travel-planner.nika.yaml           Realistic multi-step agent
├── 21-use-output-demo.nika.yaml          output: binding showcase
├── 22-fetch-chain.nika.yaml              ✅ fetch → bind → summarize (shipped name)
├── 23-code-review.nika.yaml              ✅ code-review agent loop
├── 24-complex-dag.nika.yaml              Showcase a complex DAG
├── 25-agents-preset.nika.yaml            Agent presets · model routing
├── 26-for-each-locales.nika.yaml         ✅ locale iteration pattern
│
└── README.md                              this file
```

Plus the [`showcase/`](showcase/) subdirectory — real-job workflows,
tiered T1→T4. (Instantiable SKELETONS live separately in
[`../templates/`](../templates/) — copy one instead of starting blank.)

## Convention

Each example file ·

- Starts with a `# SPDX-License-Identifier: Apache-2.0` comment
- Has a top comment explaining what it demonstrates
- Uses the `mock/` model where possible (for portability + CI testability)
- References only stdlib v0.1 elements
- Is included in the conformance test suite as an input fixture

## How to run (planned)

```bash
# With the reference engine
nika run examples/01-hello.nika.yaml

# With any v0.1-compliant engine
<engine> run examples/01-hello.nika.yaml
```

---

🦋 *7 foundation examples shipped (full v0.1 construct coverage) · 19 pending · canonical for v0.1.0 GA.*
