# Showcase · industry workflows, simplest → epic

> Complete, spec-correct workflows (the count lives in [`../manifest.yaml`](../manifest.yaml)) that answer one question per
> industry · **« what would MY Monday look like with this? »** Every
> file passes the same conformance gate as the foundation examples
> (`python conformance/runner.py all`) — schema + DAG cross-refs +
> stdlib surface. Together with the foundation set they exercise
> **every stdlib builtin** (verified by the conformance + coverage sweep).

The [foundation examples](../README.md) teach the *language*
construct-by-construct. The showcase teaches the *life* — real jobs,
tiered by complexity so a newcomer climbs from a 4-task starter to a
multi-agent swarm without ever leaving validated ground.

---

## The ladder · 4 tiers

```
T1 STARTER     ≤4 tasks · one chain or one diamond · your first wow
T2 CHAIN       4-6 tasks · typed outputs · human gates · data builtins
T3 FAN-OUT     runtime collections · for_each · retry · jq zips · swarms
T4 EPIC        multi-stage pipelines · agents under budget · self-reporting runs
```

## The workflows

| File | Industry | The wow | Key constructs |
|---|---|---|---|
| `t1-standup-digest` | engineering | the standup note writes itself from real commits | parallel start · `nika:date` · exec→infer |
| `t1-meeting-actions` | every office | transcript → tracker-ready typed action items | `infer.schema:` · typed vars |
| `t1-price-watch` | e-commerce / personal | a price alert with **zero** model calls | `output:` jq · CEL `when:` · secrets |
| `t1-social-repurpose` | marketing / creators | one post → thread + LinkedIn + newsletter, in parallel | diamond DAG · `with:` aliasing |
| `t1-og-images` | marketing / content | brief in → OG PNG + provenance manifest out, one task | `nika:image_generate` · provenance |
| `t1-image-fx-batch` | creators / media | a folder of photos → deterministic art, byte-identical forever | `nika:glob` · `for_each` · `nika:image_fx` ops chain |
| `t2-release-notes` | engineering / devrel | git log → typed notes → CHANGELOG edited in place | `nika:edit` · schema · notify |
| `t2-seo-content-brief` | SEO / content | a brief that beats the competitor's best page | chained fetch modes · CEL indexing |
| `t2-invoice-chaser` | finance / freelance | overdue reminders drafted · NOTHING sent without a yes | `nika:convert` · `nika:prompt` gate · `size()` |
| `t2-support-triage` | customer support | the overnight queue triaged before coffee | schema-over-list · jq post-filter · `nika:uuid` |
| `t2-contract-guard` | legal / compliance | the contract **never leaves the machine** (local model) | `ollama/…` · `nika:validate` + `nika:assert` |
| `t2-etl-quarantine` | data engineering | bad batches degrade to quarantine · the pipeline lives | `on_error: recover:` · `nika:validate` · jq group_by |
| `t2-model-bench` | engineering / model selection | the same question, three local models, one MEASURED table | per-task `infer.model:` · `duration_ms` as data · jq fan-in |
| `t2-release-radar` | devops / dependencies | only the NEW ships reach you | `mode: feed` · state-file diff · RFC 6902 |
| `t2-csv-chart-report` | data → picture | paste the spreadsheet, get the slide — offline, deterministic | `nika:convert` · jq group_by · `nika:chart` |
| `t2-transcript-shownotes` | podcasts / meetings | raw transcript → typed show-notes, ONE bounded infer | `infer.schema:` strict · typed→markdown |
| `t2-bookmark-triage` | personal / research | the bookmark pile triaged — dead links survive the batch | `mode: metadata` · resilient `for_each` · recover |
| `t3-competitor-radar` | strategy / PMM | everything they shipped last week, one brief | `for_each` · `max_parallel` · retry · fan-in |
| `t3-localization-factory` | product / i18n | the whole docs tree translated, voice intact | chained fan-outs · jq `transpose` zip |
| `t3-config-drift-sentinel` | SRE / platform | only UNSANCTIONED prod drift wakes anyone | RFC 7396 merge + RFC 6902 diff · blake3 |
| `t3-pr-review-fanout` | engineering | one read-only review agent **per changed file** | `for_each`+`agent:` swarm · default-deny tools |
| `t3-resume-screener` | HR / recruiting | one local-model rubric per candidate · PII stays home | `ollama/…` · `for_each` · schema enums · jq sort_by |
| `t4-deep-research-brief` | research / VC | plan → budgeted agent → thinking synthesis | plan-then-execute · budgets · `thinking:` |
| `t4-incident-war-room` | SRE / on-call | the postmortem drafts itself — after recovery is PROVEN | `nika:wait` settle · assert · `on_finally:` |
| `t4-ceo-monday-brief` | founders / execs | the brief that reports its own LLM bill | 3-branch gather · `nika:inspect` cost |
| `t4-release-train` | devops / release | gates → human GO → hold until the window → ship · verify | `nika:wait until:` · `nika:date diff` · `nika:prompt` |

## Conventions (same gate as the foundation set)

- `# SPDX-License-Identifier: Apache-2.0` header + schema hint line
- `ollama/qwen3.5:4b` is the showcase model: every file leads local,
  with one deliberate exception class — strict-schema showcases pick a
  NON-thinking model (`ollama/llama3.2:3b`): a thinking model can burn
  the whole `max_tokens` in its think block before the JSON (engine#428).
  zero key, recorded-as-run. Cloud providers appear only as per-task
  overrides or swap hints, never as the envelope default. Where the
  data is sensitive the local model is the point: sovereignty is a
  feature, show it
- the offline story, honestly: `nika check` needs zero network on every
  file, and any `infer:` showcase dry-runs with `--model mock/echo`
  (deterministic, zero model). The `agent:` showcases
  (`t3-pr-review-fanout` · `t4-deep-research-brief`) are the exception —
  mock echoes text and never *calls* a tool, so the ReAct loop does zero
  rounds under it: exercising the agent needs a real tool-calling model
  (the pinned local `qwen3.5` qualifies)
- every file is a conformance input · `python conformance/runner.py all`
  MUST stay green · one verb per task · snake_case ids · every
  `${{ tasks.X }}` reference backed by `depends_on`
- these files are the **single source** for the YAML shown in the
  public docs (`nika-docs` examples pages) and the website use-cases
  explorer — projected, never hand-copied
  (`scripts/showcase-projector.py` · `--check` is the drift gate)

🦋 *The showcase pack · 4 tiers · every stdlib builtin exercised across the example corpus · manifest = the contract.*
