---
license: apache-2.0
task_categories: [text-generation]
tags: [workflow, dsl, llm-authorability, agents, nika]
pretty_name: Nika Authorability Bench
size_categories: [n<1K]
---

# Nika Authorability Bench (seed v0)

**The measured claim.** « A constrained workflow DSL is more reliably
LLM-authored than framework code » is Nika's central thesis. Anka
(arXiv:2512.23214) proved the class (+40 pts vs Python · 99.9% zero-shot
parse on an unseen DSL); the Kinaxis counter-study (arXiv:2601.00469)
proved it must be MEASURED per-language, not asserted. This dataset is
the measuring instrument for Nika — shaped as a Hugging Face dataset
from day 1 so anyone can reproduce or extend it.

## Protocol (Anka × ADK-Arena × pass^k)

1. **Input** · a model gets the docs bundle (`llms.txt` index or the
   full `llms-full.txt`) + one task intent from `tasks.jsonl` — zero
   few-shot Nika examples beyond what the docs carry.
2. **Generate** · the model writes a complete `*.nika.yaml`.
3. **Judge L1 (mechanical · no LLM)** · `nika check` — parse + static
   ladder (types · schema satisfiability · DAG · budget floor).
4. **Judge L2 (structural)** · the fixture's `expect` block: required
   verbs present · DAG shape (node/edge count bounds) · declared
   outputs consumed.
5. **Score** · pass^k over k independent generations (reliability, not
   single-run luck · per ReliabilityBench arXiv:2601.06112).

## Fields (`tasks.jsonl`)

| field | type | meaning |
|---|---|---|
| `id` | string | stable slug |
| `intent` | string | the natural-language ask (what a real user types) |
| `difficulty` | t1-t4 | mirrors the showcase tiers |
| `expect.verbs` | string[] | verbs the solution must use |
| `expect.min_tasks` / `max_tasks` | int | DAG size bounds |
| `expect.constructs` | string[] | required constructs (schema · for_each · depends_on · retry · permits …) |
| `reference` | string | path to one valid reference solution (not the only one) |

## Baselines to publish (v1)

Same protocol · same tasks · Nika vs LangGraph-Python vs raw-Python ·
k=5 · a local open-weight (qwen3.5:9b) + one frontier model — the
open-weight column is the sovereignty story.

## License

Apache-2.0 (matches the spec).
