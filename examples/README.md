# Examples · canonical Nika workflows

> 26 canonical example workflows demonstrating the language. Each file
> is a complete, runnable workflow (with the reference engine) or a
> teaching example (with `mock` provider) that doesn't require API keys.

---

## Status · placeholder for v0.1.0-draft

The examples will be **recopied clean from the brouillon exploration era**
(supernovae-st/nika brouillon branch · `examples/` directory ships 26
canonical workflows that informed the v0.1 spec design).

**The recopy is a CRAFT operation** · the brouillon examples will be
re-authored to · (a) match the v0.1 envelope exactly (`apiVersion: nika.sh/v1`) · (b) use only stdlib v0.1 inclusions · (c) carry SPDX Apache-2.0 headers · (d) be testable against the conformance suite.

## Planned examples (recopied clean from brouillon)

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
├── 09-orchestrate-mock.nika.yaml         Use mock provider for testing
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
├── 24-diamond.nika.yaml                  Showcase complex DAG
├── 25-agents-preset.nika.yaml            Agent presets · model routing
├── 26-for-each-locales.nika.yaml         Locale iteration pattern
│
└── README.md                              this file
```

Plus a `showcase/` subdirectory for end-to-end project templates.

## Convention

Each example file ·

- Starts with `# SPDX-License-Identifier: Apache-2.0` comment
- Has a top comment explaining what it demonstrates
- Uses provider `mock` where possible (for portability + CI testability)
- References only stdlib v0.1 elements
- Is included in the conformance test suite as an input fixture

## How to run (planned)

```bash
# With the reference engine
nika run examples/01-hello.nika.yaml

# With any v0.1-compliant engine
<engine> run examples/01-hello.nika.yaml
```

## Sources

The examples derive from the 26 workflows in the brouillon exploration era
(`supernovae-st/nika` brouillon branch · `examples/` directory). The
brouillon is the source of empirical knowledge about what real workflows
look like · v0.1 distills that into a clean canonical set.

---

🦋 *26 examples · canonical · pending recopy from brouillon.*
