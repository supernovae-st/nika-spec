# Examples · canonical Nika workflows

> 26 canonical example workflows demonstrating the language. Each file
> is a complete, runnable workflow (with the reference engine) or a
> teaching example (with the `mock/` model) that doesn't require API keys.

---

## Status · placeholder for v0.1.0-draft

The examples are pending for v0.1.0 GA. They distill **26 workflows from an
earlier Nika prototype** — the empirical source of what real workflows look
like — into a clean canonical set.

Each will be re-authored to · (a) match the v0.1 envelope exactly
(`nika: v1`) · (b) use only stdlib v0.1 inclusions · (c) carry an SPDX
Apache-2.0 header · (d) pass the conformance suite.

## Planned examples

```
examples/
├── 01-hello.nika.yaml                    "Hello world" · 1 task · infer
├── 02-minimal.nika.yaml                  Most minimal workflow possible
├── 03-multi-provider.nika.yaml           Compare 3 providers on same prompt
├── 04-multi-locale.nika.yaml             Multi-language fan-out
├── 05-exec-only.nika.yaml                Workflow with only exec: verbs
├── 06-parallel-fanout.nika.yaml          DAG fan-out + merge
├── 07-mcp-invoke.nika.yaml               Call an MCP tool
├── 08-multi-locale-mcp.nika.yaml         Combine locale loop + MCP
├── 09-orchestrate-mock.nika.yaml         Use mock model for testing
├── 10-orchestrate-openai.nika.yaml       Use openai · structured output
├── 11-orchestrate-simple.nika.yaml       Sequential 3-task workflow
├── 12-provider-structured-parity.nika.yaml  Structured output across providers
├── 13-quickstart-mcp.nika.yaml           First MCP tool call
├── 14-quickstart-multilang.nika.yaml     Translation pipeline
├── 15-test-extended-thinking.nika.yaml   Anthropic extended thinking
├── 16-test-file-output-shell.nika.yaml   exec + file write
├── 17-test-file-output.nika.yaml         infer + nika:write
├── 18-test-full-pipeline-mcp.nika.yaml   End-to-end pipeline
├── 19-test-schema-retry.nika.yaml        Structured output + retry on validation
├── 20-travel-planner.nika.yaml           Realistic multi-step agent
├── 21-use-output-demo.nika.yaml          output: binding showcase
├── 22-weather-chain.nika.yaml            API chain · fetch + infer
├── 23-code-review.nika.yaml              Code review agent
├── 24-complex-dag.nika.yaml              Showcase a complex DAG
├── 25-agents-preset.nika.yaml            Agent presets · model routing
├── 26-for-each-locales.nika.yaml         Locale iteration pattern
│
└── README.md                              this file
```

Plus a `showcase/` subdirectory for end-to-end project templates.

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

🦋 *26 examples · canonical · pending for v0.1.0 GA.*
