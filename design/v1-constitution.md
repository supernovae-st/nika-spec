# The v1 constitution — surface tournament (RFC)

> **Status · RATIFIED — operator ruling 2026-07-13.** Candidate A is the ONLY
> canonical public surface of nika v1; B's tagged-record elegance is absorbed
> into the internal IR (the verb key promotes to a tag at lowering); C is
> rejected as a normative surface and survives only as a possible
> sugar-by-lowering hypothesis post-1.0, never a second semantics. The four
> forms are ratified under the hierarchy **three atomic calls and one bounded
> controller** (§11). Nothing in this document changes the grammar yet — the
> breaking windows open only after the W0 exit gates are green.
>
> Method · three candidate surfaces, each expressing the SAME fixed semantic
> model, each written out in full on the SAME seven witness workflows, scored
> on twelve criteria and one cost function. The tournament's output is a
> normative choice, the rejected alternatives with their counterexamples, and
> the list of error classes the chosen surface makes inexpressible.

---

## 1 · The question this document answers

The mandatory question for every element of syntax:

> **What error does this construction make impossible to express?**

If the answer is "none", the construction must justify itself some other way —
or die. The surface we freeze at engine 1.0.0 must minimize:

```
TotalCost = Ambiguity + Duplication + HiddenAuthority + InvalidStates
          + LspComplexity + AgentComplexity + FutureDebt
```

Everything kept must justify its existence. Every duplication must have a
single owner. Every unknown must stay unknown (never coerced to zero, never
guessed). Every normative rule must carry a positive fixture, a negative
fixture and a ratchet. Every replaced design must disappear completely.

## 2 · The fixed semantic model (surface-independent)

All three candidates express EXACTLY this model. The tournament judges
spelling, not semantics. These invariants come from the refonte rulings and
are not re-litigated here:

1. **Tasks form a map** — the task name is its key; duplicate keys are a parse
   error; source order is presentation, never execution truth.
2. **`workflow:` is an object** `{id, description, …}` — a stable place for
   metadata.
3. **Data dependencies exist exactly once.** A task introduces upstream data
   through named local bindings; the binding IS the edge. Cross-task
   references inside operation bodies are illegal. The reference-without-edge
   error class becomes inexpressible.
4. **Edges carry roles derived from the projection read**:
   `.output` → *value* edge (predicate: a usable value exists) ·
   `.status` / `.duration_ms` → *terminal-observation* edge (predicate: the
   producer reached ANY terminal state) · `.error` → *failure-observation*
   edge (predicate: the producer failed). One expression with N references
   creates N static edges. The graph is what MAY be needed; the trace is what
   was.
5. **Control-only waiting is its own construct** (wait for a state, consume no
   data). **Business conditions are local**: a gate expression may read
   inputs/config/bindings/loop-locals — never task states.
6. **Four graphs**: data (bindings) · control (waits) · recovery (fallback
   sources; parked, never scheduling edges) · finalization (cleanup on any
   terminal outcome). Main precedence = data ∪ control.
7. **`returns:` is the task-level output CONTRACT** (one per task, from a
   `types:` block — a decidable core that lowers to JSON Schema 2020-12).
   Decoding raw bytes into a typed value is explicit verb mechanics, never
   inferred from the type.
8. **Four authorities**: `inputs:` (caller) · `config:` (deployment) ·
   `const:` (author) · `secrets:` (opaque store-refs with explicit egress
   declassification). No ambient environment authority exists.
9. **Policy separates hard from soft**: require/forbid/allow/limits define the
   feasible set; prefer/optimize rank inside it. Effects are computed; permits
   are their projection.
10. **Agents are bounded** (turns · time · spend); unproven bounds stay
    Unknown, never fake-Exact. **Unknown ≠ 0 · Unpriced ≠ Free.**
11. **The four forms are ratified — not inherited** (the old freeze predates
    the pre-1.0 stability contract, so W0 re-ratifies them) under the
    hierarchy **three atomic calls and one bounded controller**:
    `infer` = one logical model call (no tools, no loop — probabilistic by
    nature, which is why `invoke` never absorbs it) · `invoke` = one
    application of a **typed, statically identifiable callable** ·
    `exec` = one explicit host-process call under a capability boundary ·
    `agent` = a **bounded controller** over a closed set of pre-approved
    calls (its IR is composition, not a peer atomic). Everything
    request-response and typable belongs to `invoke`; everything about
    ordering is a DAG construct; auditable decisions are a pure callable
    (`nika:decide`), and the LLM never decides: it emits closed, cited
    facts. No fifth verb — ever.
12. **`assert:` states workflow-level properties** (secret egress · eventual
    states · ordering · resource ceilings) with honest proof levels.

## 3 · The seven witnesses

Chosen so that every 2060 decision is exercised at least once:

| # | Witness | What it stresses |
|---|---|---|
| T1 | research-report | types · returns · four authorities · secrets+egress · policy · assert |
| T2 | locales fan-out | for_each · per-item recovery · fan-in typing |
| T3 | bounded agent | stop bounds · agent returns contract · downstream typed read |
| T4 | exec diamond | argv vs shell doors · explicit decoder · control-only joins · business gate |
| T5 | resilience | retry · recovery edge off the main chain · terminal-observation read · finalization |
| T6 | auditable decision | evidence typing · closed LLM facts · deterministic decide · governance gate |
| T7 | composition | child workflow call · typed boundary · permits fit · cost summation |

---

## 4 · Candidate A — verb-keyed typed dataflow

The operation is named by which verb KEY the task carries (exactly one of
`infer:` / `exec:` / `invoke:` / `agent:`). Task-level contracts (`with:` ·
`after:` · `when:` · `returns:` · `retry:` · `on_error:` · `on_finally:` ·
`limits:`) sit beside the verb block; the verb block holds only the
operation's own parameters. This is the continuity candidate: today's corpus
already thinks in verb keys.

### A·T1 — research-report

```yaml
nika: v1

workflow:
  id: research-report
  description: Fetch, summarize and publish a report

types:
  Article:
    object:
      title: string
      body: string
      url: uri
  Summary:
    object:
      title: string
      bullets: { array: string }
      confidence: { number: { min: 0, max: 1 } }

inputs:
  url: { type: uri, required: true }

config:
  out_dir: { type: path, default: ./out }

secrets:
  provider_key:
    from: env:PROVIDER_API_KEY
    allow:
      - provider: openai

policy:
  allow:
    net: [arxiv.org]
    fs:
      write: ["./out/**"]
  limits:
    cost_usd: 0.20

tasks:
  fetch:
    invoke:
      tool: nika:fetch
      args: { url: ${{ inputs.url }}, mode: article }
    returns: Article

  summarize:
    with:
      article: ${{ tasks.fetch.output }}          # ← the value edge
    infer:
      prompt: |
        Summarize the article.
        Title: ${{ with.article.title }}
        Body: ${{ with.article.body }}
    returns: Summary
    limits: { timeout: 30s, cost_usd: 0.05 }

  publish:
    with:
      summary: ${{ tasks.summarize.output }}
    invoke:
      tool: nika:write
      args:
        path: ${{ config.out_dir }}/report.md
        content: ${{ with.summary }}
    returns: artifact<text/markdown>

outputs:
  report: { from: ${{ tasks.publish.output }}, type: artifact<text/markdown> }

assert:
  - no_secret_egress
  - eventually: { task: publish, state: succeeded }
```

### A·T2 — locales fan-out

```yaml
nika: v1

workflow:
  id: locale-bundle
  description: Translate one text into every locale, bundle the results

types:
  Translation:
    object: { locale: string, text: string }
  Bundle:
    object: { count: integer, items: { array: Translation } }

inputs:
  text: { type: string, required: true }

const:
  locales: { type: { array: string }, value: [fr, de, ja] }

tasks:
  translate:
    for_each: ${{ const.locales }}
    max_parallel: 2
    fail_fast: false
    infer:
      prompt: "Translate into ${{ item }} · ${{ inputs.text }}"
    on_error:
      recover: null            # a failed locale yields null, the map continues
    returns: Translation

  bundle:
    with:
      translations: ${{ tasks.translate.output }}   # fan-in: the whole collection
    invoke:
      tool: nika:jq
      args:
        input: ${{ with.translations }}
        expression: "{count: (map(select(. != null)) | length), items: map(select(. != null))}"
    returns: Bundle

outputs:
  bundle: { from: ${{ tasks.bundle.output }}, type: Bundle }
```

### A·T3 — bounded agent

```yaml
nika: v1

workflow:
  id: bounded-research
  description: An agent researches, a model digests, bounds are proven

types:
  ResearchLog:
    object:
      findings: { array: string }
      sources: { array: uri }
  Digest:
    object: { headline: string, body: string }

inputs:
  topic: { type: string, required: true }

policy:
  forbid:
    unbounded_agents: true

tasks:
  researcher:
    agent:
      model: ollama/qwen3:8b
      tools: [nika:fetch, nika:write]
      stop:
        max_turns: 8
        timeout: 2m
        max_cost_usd: 0.10
      prompt: "Research ${{ inputs.topic }}; log findings with sources."
    returns: ResearchLog

  digest:
    with:
      log: ${{ tasks.researcher.output }}
    infer:
      prompt: "Write a two-line digest of: ${{ with.log.findings }}"
    returns: Digest

outputs:
  digest: { from: ${{ tasks.digest.output }}, type: Digest }
```

### A·T4 — exec diamond (argv · shell door · decoder · control joins)

```yaml
nika: v1

workflow:
  id: build-test-bench-deploy
  description: Build once, test and bench in parallel, deploy behind both

types:
  BenchReport:
    object: { p50_ms: number, p95_ms: number }

config:
  deploy_enabled: { type: bool, default: false }

tasks:
  build:
    exec:
      command: [make, release]          # argv — execve, no shell

  test:
    after: { build: succeeded }         # control edge: no data consumed
    exec:
      command: [make, test]

  bench:
    after: { build: succeeded }
    exec:
      shell: "./bench --json | tee bench.log"   # the explicit dangerous door
      decode: json                               # explicit decoder, not type magic
    returns: BenchReport

  deploy:
    after:
      test: succeeded
      bench: succeeded
    when: ${{ config.deploy_enabled }}  # business gate: local authority only
    exec:
      command: [./deploy.sh]
```

### A·T5 — resilience (recovery edge · terminal observation · finalization)

```yaml
nika: v1

workflow:
  id: fetch-with-fallback
  description: Live fetch with cache fallback, status notification, cleanup

types:
  CacheDoc:
    object: { body: string, stale: bool }

tasks:
  cache_read:
    exec:
      command: [cat, cache.json]
      decode: json
    returns: CacheDoc

  live:
    invoke:
      tool: nika:fetch
      args: { url: "https://example.com/data", mode: json }
    timeout: 30s
    retry:
      max_attempts: 3
      backoff_strategy: exponential
    on_error:
      recover: ${{ tasks.cache_read.output }}   # recovery edge — parked, not scheduling

  notify:
    with:
      outcome: ${{ tasks.live.status }}          # terminal-observation edge
    infer:
      prompt: "Write a one-line ops note · live fetch ended '${{ with.outcome }}'."

  cleanup:
    on_finally:
      - invoke:
          tool: nika:cleanup
          args: { path: ./tmp }
```

### A·T6 — auditable decision (evidence → closed facts → deterministic decide)

```yaml
nika: v1

workflow:
  id: pr-triage
  description: Facts are collected, the model speaks closed facts, the kernel decides

types:
  Evidence:
    object:
      checks_failed: integer
      diff_lines: integer
      has_tests: bool
  SemanticFacts:
    object:
      scope_ok: { enum: [yes, no, unknown] }
      tests_adequate: { enum: [insufficient, partial, adequate] }
      claims_supported: { enum: [yes, no, unknown] }
  Decision:
    object:
      lane: { enum: [fast_review, standard_review, deep_review, human_required] }
      scores: { map: { key: string, value: integer } }
      uncertainty: string

inputs:
  pr: { type: integer, required: true }

tasks:
  gather:
    invoke:
      tool: mcp:github/pr-facts
      args: { pr: ${{ inputs.pr }} }
    returns: Evidence

  judge:
    with:
      evidence: ${{ tasks.gather.output }}
    infer:
      prompt: |
        Judge ONLY these closed criteria for the PR facts below; cite the
        fact for each answer. Facts: ${{ with.evidence }}
    returns: SemanticFacts        # closed enums — the model cannot decide

  decide:
    with:
      evidence: ${{ tasks.gather.output }}
      facts: ${{ tasks.judge.output }}
    invoke:
      tool: nika:decide
      args:
        bundle: registry:linkml/pr-triage@1.2.0
        evidence: [${{ with.evidence }}, ${{ with.facts }}]
    returns: Decision

  apply_label:
    with:
      decision: ${{ tasks.decide.output }}
    after: { decide: succeeded }
    when: ${{ with.decision.lane != 'human_required' }}
    invoke:
      tool: mcp:github/add-label
      args: { pr: ${{ inputs.pr }}, label: ${{ with.decision.lane }} }

outputs:
  decision: { from: ${{ tasks.decide.output }}, type: Decision }

assert:
  - eventually: { task: decide, state: succeeded }
```

### A·T7 — composition

```yaml
nika: v1

workflow:
  id: topic-brief
  description: A parent calls a typed child workflow and digests its report

types:
  ResearchReport:
    object:
      title: string
      findings: { array: string }

inputs:
  topic: { type: string, required: true }

tasks:
  research:
    invoke:
      tool: nika:workflow
      args:
        path: ./research.nika.yaml
        inputs: { query: ${{ inputs.topic }} }
    returns: ResearchReport      # checked against the child's outputs contract

  summarize:
    with:
      report: ${{ tasks.research.output }}
    infer:
      prompt: "Three-line brief of ${{ with.report.title }}: ${{ with.report.findings }}"

outputs:
  brief: { from: ${{ tasks.summarize.output }}, type: string }
```

### A · self-critique (12 criteria)

1. **Readability** — strong: the verb key is the first thing the eye finds;
   task contracts read as a stable frame around one verb block. Weakness: two
   nesting levels (task keys vs verb params) must be learned.
2. **Agent generability** — strong: matches the corpus every model has seen
   (GitHub-Actions-like). One shape per verb = four templates.
3. **Analyzability** — strong: the verb is structural (a key), so the parser
   dispatches without reading values; exactly-one-verb is a keyset check.
4. **Typing** — neutral: `returns:` sits at task level regardless of
   candidate; no surface advantage or penalty.
5. **Security** — strong: `shell:` vs `command:` stays a FIELD distinction
   inside `exec:` (the 0.103 law); the dangerous door is greppable.
6. **Git diff** — good: adding a field touches one line inside a stable
   frame. Weakness: renaming a verb (never planned) would be structural.
7. **LSP complexity** — low: completion keysets are per-verb-block; hover
   targets are keys; the keysets door already models this exactly.
8. **Concision** — middling: the verb key adds one nesting level vs B-flat;
   chains carry explicit bindings C would elide.
9. **Extensibility** — a fifth operation would be a new top-level key in the
   task keyset — additive, feature-detectable.
10. **Provability** — the task judgment Γ ⊢ t reads directly off the shape:
    contracts outside, operation inside.
11. **Performance** — no measurable parse difference between candidates at
    these scales; keyset dispatch is O(keys).
12. **2060 fit** — the verb set is locked; a surface that makes the verb
    STRUCTURAL encodes the lock in the grammar itself.

Counter-example where A hurts: a tool that wants to be "verb-like"
(`nika:decide`) will always read as `invoke:` + `tool:` — two lines of
ceremony B or C could sugar away. A accepts this cost deliberately: the verb
set is closed, and sugar is how closed sets rot.

---

## 5 · Candidate B — unified tagged-operation (`op:` + `params:`)

*Authored independently against the same fixed model and witnesses; self-critique preserved verbatim.*

Every task is one uniform record whose operation is selected by a data field, not by a structural key. Committed spellings: the discriminant is **`op:`**; operation parameters are **nested under `params:`** (flattening would merge four vocabularies plus the task envelope into one keyspace, making the legal key set of a task a function of a sibling value — dissolving the very uniformity B exists to provide).

### B · grammar summary

```yaml
tasks:                       # MAP · key = task id · duplicate keys rejected
  <id>:
    op: infer | exec | invoke | agent      # REQUIRED · closed enum · the discriminant
    params: { ... }                        # REQUIRED · the op's closed field table —
                                           #   the ONLY op-variant subtree of a task
    with:  { name: ${{ tasks.X.output }} } # data edges · role by projection
    after: { task_id: succeeded | failed | skipped | terminal }   # control edges
    when: ${{ ... }}                       # local gate
    for_each: ${{ ... }} | [ ... ]
    max_parallel: <int >= 1>
    fail_fast: <bool>
    retry: { max_attempts, backoff, ... }
    on_error: { recover | skip | fail_workflow, on_codes }
    limits: { timeout: "30s", cost_usd: 0.05 }
    on_finally:
      <id>: { op: ..., params: { ... }, when: ..., limits: ... }
    returns: <TypeName | inline type>
```

Per-op `params:` tables (closed, strict-mode rejects unknowns):

| op | required | optional |
|---|---|---|
| `infer` | `prompt` | `system` · `model` · `temperature` · `max_tokens` · `thinking` · `vision` |
| `exec` | `argv` XOR `shell` | `cwd` · `env` · `stdin` · `decoder` (`text`\|`json`\|`jsonl`\|`bytes`) |
| `invoke` | `tool` | `args` |
| `agent` | `prompt` · `stop` (>= 1 of `max_turns` / `timeout` / `max_cost_usd` / `max_tokens`) | `system` · `model` · `tools` · `skills` |

Cross-task references are forbidden inside `params:` — they live only in `with:` / `after:` / `on_error.recover` / `on_finally` gating.

### B·T1 — research-report

```yaml
nika: v1
workflow:
  id: research-report
  description: Fetch one article, summarize it, publish a markdown report.

inputs:
  url: { type: uri, required: true }

config:
  out_dir: { type: path, default: ./out }

secrets:
  provider_key:
    ref: vault:prod/openai/api-key
    egress: [provider:openai]          # declassifies to this provider sink only

types:
  Article:
    title: string
    body: string
    url: uri
  Summary:
    title: string
    bullets: list<string>
    confidence: float(0..1)

policy:
  allow:
    net: [arxiv.org]
    fs: { write: ["./out/**"] }
  limits:
    cost_usd: 0.20

tasks:
  fetch:
    op: invoke
    params:
      tool: nika:fetch
      args: { url: "${{ inputs.url }}", mode: article }
    returns: Article

  summarize:
    op: infer
    params:
      prompt: |
        Summarize this article for a technical reader.

        ${{ with.article }}
    with:
      article: ${{ tasks.fetch.output }}       # value edge · fetch -> summarize
    limits: { timeout: "30s", cost_usd: 0.05 }
    returns: Summary

  publish:
    op: invoke
    params:
      tool: nika:write
      args:
        dir: ${{ config.out_dir }}
        content: ${{ with.summary }}
    with:
      summary: ${{ tasks.summarize.output }}
    returns: artifact<text/markdown>

outputs:
  report: { from: ${{ tasks.publish.output }}, type: artifact<text/markdown> }

assert:
  static:
    - no_secret_egress
  trace:
    - eventually: { task: publish, state: succeeded }
```

### B·T2 — locales fan-out / fan-in

```yaml
nika: v1
workflow:
  id: locale-fanout
  description: Translate one source text into three locales, then bundle.

inputs:
  text: { type: string, required: true }

const:
  locales: [fr, de, ja]

types:
  Translation:
    locale: string
    text: string
  Bundle:
    entries: list<Translation>

tasks:
  translate:
    op: infer
    params:
      prompt: |
        Translate into locale ${{ item }}. Return only the translation.

        ${{ inputs.text }}
    for_each: ${{ const.locales }}
    max_parallel: 2
    fail_fast: false
    on_error: { recover: null }        # a failed locale yields null, the fan-out survives
    returns: Translation

  bundle:
    op: invoke
    params:
      tool: nika:compose
      args:
        entries: ${{ with.translations }}
    with:
      translations: ${{ tasks.translate.output }}   # fan-in · the per-item output array
    returns: Bundle
```

### B·T3 — bounded agent

```yaml
nika: v1
workflow:
  id: bounded-research
  description: A tool-bounded research agent, then a digest of its log.

inputs:
  topic: { type: string, required: true }

types:
  ResearchLog:
    findings: list<string>
    sources: list<uri>
  Digest:
    summary: string

tasks:
  researcher:
    op: agent
    params:
      prompt: Research ${{ inputs.topic }} and log findings with sources.
      model: ollama/qwen3.5:4b
      tools: [nika:fetch, nika:write]
      stop:                            # required · an agent is bounded or it is invalid
        max_turns: 8
        timeout: "2m"
        max_cost_usd: 0.10
    returns: ResearchLog

  digest:
    op: infer
    params:
      prompt: |
        Digest this research log into one paragraph.

        ${{ with.log }}
    with:
      log: ${{ tasks.researcher.output }}
    returns: Digest
```

### B·T4 — exec pipeline

```yaml
nika: v1
workflow:
  id: build-test-bench-deploy
  description: Argv builds and tests, one explicit shell bench, gated deploy.

config:
  deploy_enabled: { type: bool, default: false }

types:
  BenchReport:
    p50_ms: float
    p99_ms: float

tasks:
  build:
    op: exec
    params:
      argv: [make, release]

  test:
    op: exec
    params:
      argv: [make, test]
    after: { build: succeeded }

  bench:
    op: exec
    params:
      shell: "./bench --json | tee bench.json"   # the explicit shell door · pipes live here
      decoder: json
    returns: BenchReport

  deploy:
    op: exec
    params:
      argv: [./deploy.sh]
    after:
      test: succeeded
      bench: succeeded
    when: ${{ config.deploy_enabled }}
```

### B·T5 — resilience

```yaml
nika: v1
workflow:
  id: fetch-with-fallback
  description: Live fetch with cached fallback, status notification, cleanup.

config:
  cache_path: { type: path, default: ./cache/doc.json }
  feed_url: { type: uri, default: "https://example.org/feed" }

types:
  CacheDoc:
    body: string
    stale: bool

tasks:
  cache_read:
    op: exec
    params:
      argv: [cat, "${{ config.cache_path }}"]
      decoder: json
    returns: CacheDoc

  live:
    op: invoke
    params:
      tool: nika:fetch
      args: { url: "${{ config.feed_url }}" }
    limits: { timeout: "30s" }
    retry:
      max_attempts: 3
      backoff: exponential
    on_error:
      recover: ${{ tasks.cache_read.output }}    # recovery edge · cache_read parks as fallback
    returns: CacheDoc

  notify:
    op: infer
    params:
      prompt: |
        Write a one-line status note for operators.
        Live fetch terminal status: ${{ with.live_status }}
    with:
      live_status: ${{ tasks.live.status }}      # terminal-observation edge
    on_finally:
      cleanup:
        op: invoke
        params: { tool: nika:cleanup }
```

### B·T6 — auditable decision

```yaml
nika: v1
workflow:
  id: pr-triage
  description: Facts from the forge, closed semantic judgments, deterministic decision.

inputs:
  pr: { type: int, required: true }

types:
  Evidence:
    checks_failed: int
    diff_lines: int
    has_tests: bool
  SemanticFacts:
    scope_ok: enum(yes, no, unknown)
    tests_adequate: enum(yes, no, unknown)
    claims_supported: enum(yes, no, unknown)
    citations: list<string>
  Decision:
    lane: enum(auto_merge, needs_review, human_required)
    scores: map<string, fixed>
    uncertainty: fixed

tasks:
  gather:
    op: invoke
    params:
      tool: mcp:github/pr_facts
      args: { pr: ${{ inputs.pr }} }
    returns: Evidence

  judge:
    op: infer
    params:
      prompt: |
        Judge the pull request evidence below on the closed criteria only.
        Cite the evidence field behind every judgment. If the evidence
        does not settle a criterion, answer unknown.

        ${{ with.evidence }}
    with:
      evidence: ${{ tasks.gather.output }}
    returns: SemanticFacts        # closed, cited facts — the model never decides

  decide:
    op: invoke
    params:
      tool: nika:decide
      args:
        bundle: registry:linkml/pr-triage@1.2.0
        evidence:
          - ${{ with.evidence }}
          - ${{ with.facts }}
    with:
      evidence: ${{ tasks.gather.output }}
      facts: ${{ tasks.judge.output }}
    returns: Decision             # the deterministic kernel decides

  apply_label:
    op: invoke
    params:
      tool: mcp:github/add_label
      args:
        pr: ${{ inputs.pr }}
        label: ${{ with.decision.lane }}
    with:
      decision: ${{ tasks.decide.output }}
    after: { decide: succeeded }
    when: ${{ with.decision.lane != 'human_required' }}

assert:
  trace:
    - receipt: { task: decide, kind: decision }
```

### B·T7 — composition

```yaml
nika: v1
workflow:
  id: research-then-summarize
  description: Compose a child research workflow, then summarize its report.

inputs:
  topic: { type: string, required: true }

types:
  ResearchReport:
    findings: list<string>
    sources: list<uri>

tasks:
  research:
    op: invoke
    params:
      tool: nika:workflow
      args:
        path: ./research.nika.yaml
        inputs: { query: ${{ inputs.topic }} }
    returns: ResearchReport       # child permits must fit inside the parent's ·
                                  # child costs sum into the parent's limits
  summarize:
    op: infer
    params:
      prompt: |
        Summarize the research report for a general reader.

        ${{ with.report }}
    with:
      report: ${{ tasks.research.output }}
    returns: string

outputs:
  summary: { from: ${{ tasks.summarize.output }}, type: string }
```

### B · self-critique (12 criteria · authored by the candidate)

1. **Readability.** Uniformity is also monotony: in a 30-task file every task opens with the same two lines, so the eye navigates by task ids alone, whereas verb-as-key gives varied left-margin landmarks (`exec:` vs `infer:`) while skimming. Concrete hurt: what a task *is* sits one indent deeper and one token to the right (`op: exec`) than a verb key puts it.
2. **Agent generability.** Strongest criterion for B: one skeleton (`{op, params, envelope}`) covers all tasks, and tagged records are the JSON-mode-native shape every structured-output stack emits reliably. Honest counter: current-generation models carry a verb-as-key prior (GitHub Actions `uses:`/`run:`, Ansible module-as-key), so few-shot generation without the schema in context will drift toward A-shaped output that the checker must teach back.
3. **Analyzability.** The DAG/policy/limits extractor reads the envelope without knowing any operation vocabulary — the op-variant subtree is exactly one key, and a single internally-tagged union models the whole task. Counter: this is quarantine, not reduction — a "no shell pipes" analysis still opens `params:` and must know exec's table; and because `op` is data, a file can legally place it after 12 other keys (only a style lint restores op-first reading order).
4. **Typing.** JSON Schema becomes a textbook discriminated union: `oneOf` branches keyed on `op.const` select the `params` schema, while the envelope is one shared object schema. Counter: cross-field laws remain checker-side in both surfaces (e.g. `op: exec` with a record `returns:` requiring `params.decoder: json` is not expressible in the schema alone).
5. **Security.** `policy: { forbid: [exec] }` compiles to a one-field scan, and an auditor enumerates every agentic loop with `grep 'op: agent'` — no parser needed for triage. Counter: tasks-as-map lets a task *id* shadow an op name; the lint must flag ids drawn from the op vocabulary.
6. **Git diff.** Upgrading a task's mechanics (`infer` -> `agent`) diffs as one discriminant line plus a params delta while `with:`/`after:`/`returns:`/`retry:` show zero churn. Concrete cost: two boilerplate lines and one extra indent level per task; the one-time migration re-indents essentially every operation line in the corpus, and a 3-line diff hunk under `params:` no longer reveals *which* op it belongs to without widening context.
7. **LSP.** Completion inside `params:` resolves by one deterministic sibling lookup (`op`'s value -> table); completing `op:` itself is a closed 4-item enum. Concrete hurt: the mid-edit state where `params:` is typed before `op:` has no resolvable table (offer the 34-key union of four tables or stay silent), and *generic* `yaml-language-server` diagnostics on discriminated `oneOf` degrade to "does not match any of 4 schemas" noise, whereas verb keys anchor generic tooling for free.
8. **Concision.** B costs exactly two required lines per task where A costs one (the verb key), plus one indent level for every operation field: a five-line task grows by roughly 20-40 percent, and that tax is paid on every task forever.
9. **Extensibility.** Envelope keys and operation names live in disjoint namespaces; a hypothetical fifth execution model is one enum value plus one table. Counter: op-specific sugar has nowhere to live — a scalar shorthand is structurally excluded because `params:` must stay a map; B trades sugar-space for uniformity.
10. **Provability.** The surface *is* the tagged union that canonical IRs, JCS-style hashing, and certification want — surface-to-IR is near-identity. Honest counter: the lift A needs (find the verb key, promote it to a tag) is a dozen lines; this is a real but minor trusted-surface saving.
11. **Performance.** Parsing and analysis stay O(n); immaterial either way.
12. **2060 fit.** Tagged operation records are the lingua franca of every IDL that will plausibly still be readable in 2060 (protobuf `oneof`, serde enums, TS discriminated unions, OpenAPI discriminators, LinkML type designators). Counter: `op:`/`params:` is IR jargon in a file humans sign — a 2060 human reads `infer: prompt: ...` aloud; B is the surface a 2060 *machine* prefers.

### B · error classes

**Made inexpressible by B:** two operations on one task (duplicate-key reject + one `params:` subtree — the dedicated checker rule and its teaching disappear) · verb/field namespace ambiguity (`op: fetch` fails a CLOSED enum with four candidates and the pointer that fetch is `nika:fetch` under `invoke`) · scalar-body confusion (`infer: just-a-prompt` is unstateable) · verb-typo-as-unknown-field (`op: infre` is a closed-enum miss — precise teaching by construction).

**Introduced by B (a verb-keyed surface cannot even express these):** stale discriminant drift (editing `params:` into another op's vocabulary while forgetting to flip `op:` — the closed table catches it one step removed from the cause; under A that drift takes two-block surgery) · plausible-but-op-less task (complete `params:`, forgotten `op:` — looks finished; A's equivalent omission is visibly incomplete) · anchors aliasing across ops (`params: *shared_defaults` reused under a different `op:` no longer self-describes at the anchor site).

### B · verdict (authored by the candidate)

Surface B objectively beats a verb-as-key surface wherever a machine touches the file: generation (one skeleton, the tagged shape structured-output stacks natively emit), analysis (an op-blind envelope), typing (a textbook discriminated union), proof (the surface is already the canonical IR's tagged record), long-horizon legibility, and operation-migration diffs. It objectively loses wherever a human's eye or hand touches the file: two boilerplate lines and an indent level on every task forever, the loss of verb keys as skim landmarks, a new stale-discriminant drift class that verb-keyed surfaces cannot even express, degraded generic-YAML-tooling diagnostics on `oneOf`, and the exclusion of scalar shorthands. The decision therefore reduces to the language's audience trajectory: if workflows are predominantly authored by agents and *reviewed* by humans, B's costs land on the shrinking side of the ledger; if hand-authoring remains the primary path, the per-task tax and the monotony argue for keeping the verb as the key.

---

## 6 · Candidate C — typed pipeline combinators

*Authored independently against the same fixed model and witnesses; self-critique preserved verbatim. C is defined by a total, deterministic **lowering** to the explicit-bindings core: every C file desugars to named tasks + explicit edges; `nika fmt --explicit` can always print the desugared file.*

### C · grammar summary

```
flow       = item ;                          (* usually a then: *)
item       = REF                             (* bare string -> tasks: map entry *)
           | { NAME : stage-body }           (* inline stage · NAME is the task id *)
           | { "then"     : [ item+ ] }      (* sequence · pipe = previous output *)
           | { "parallel" : [ item, item+ ] }(* fan-out · broadcast input · record output *)
           | { "map"      : map-spec }       (* collection fan-out · array output *)
           | { "race"     : [ item, item+ ] }(* first success settles · losers cancelled *)
map-spec   = { over: EXPR , do: item , [as: IDENT] , [max_parallel: INT>=1] ,
               [fail_fast: BOOL] , [id: IDENT] }
```

Edge-derivation rules (normative): `then:` adjacency is the pipe — stage N's input is stage N−1's output bound as `${{ in }}`; a **value edge** when `in` is referenced, order-only otherwise. The flow head has no pipe (`in` there = compile error). `parallel:` broadcasts input and joins ALL branches; output = a record keyed by branch name. `map:` fans out (`in` = element · `as:` alias · `index` bound); output = positional array; per-element `recover: X` contributes at its index (element type widens to `T?`). `race:` settles on first success. `with:` taps stay explicit value edges; `.status`/`.error` tap paths derive observation edges (status never rides the pipe). `pipe: none` severs the positional edge; observing the immediate predecessor REQUIRES it (`PIPE-004` rejects the contradictory middle). `after:` = pure control. Detached tasks (in `tasks:`, absent from `flow:`) are start-eligible and must be referenced or the file is rejected. In string positions any type renders as canonical JSON (sorted keys); `expects: <Type>` pins the pipe type against reorders.

Explicit bindings remain REQUIRED for: a second upstream · any non-adjacent read · every status/error observation · anything from a detached task · `map.over` · `outputs:`/`assert:` references.

### C·T1 — research-report

```yaml
nika: v1
workflow:
  id: research-report

types:
  Article:
    title: string
    body: string
    source: uri
  Summary:
    text: string
    key_points: string[]

inputs:
  url: { type: uri, required: true }

config:
  out_dir: { type: path, default: ./out }

secrets:
  provider_key:
    egress: [provider:openai]        # usable only toward this provider

policy:
  allow:
    - net:arxiv.org
    - fs.write:./out/**
  limits:
    cost_usd: 0.20

flow:
  then:
    - fetch:
        invoke:
          tool: nika:fetch
          args: { url: ${{ inputs.url }}, mode: article }
        returns: Article

    - summarize:
        infer:
          prompt: "Summarize this article for a technical reader. ${{ in }}"
        timeout: "30s"
        limits: { cost_usd: 0.05 }
        returns: Summary

    - publish:
        invoke:
          tool: nika:write
          args:
            path: ${{ config.out_dir }}/report.md
            content: ${{ in.text }}  # typed projection of the pipe (Summary.text)
        returns: artifact<text/markdown>

outputs:
  report:
    type: artifact<text/markdown>
    value: ${{ flow.output }}        # the pipe's final value · stable across renames

assert:
  - invariant: no_secret_egress
  - eventually: { task: publish, status: success }
```

### C·T2 — locale fan-out (`map:` · zip-sound recover · fan-in)

```yaml
nika: v1
workflow:
  id: locale-fanout

types:
  Translation:
    locale: string
    text: string
  Bundle:
    entries: Translation?[]          # recovered items contribute null at their index
    complete: bool

inputs:
  text: { type: string, required: true }

const:
  locales: [fr, de, ja]

flow:
  then:
    - map:
        over: ${{ const.locales }}
        as: locale
        max_parallel: 2
        fail_fast: false
        do:
          translate:
            infer:
              prompt: "Translate into ${{ locale }}. Return locale and text. ${{ inputs.text }}"
            returns: Translation
            on_error: { recover: null }

    - bundle:                        # fan-in is positional: in = the whole array
        expects: Translation?[]      # pin: element type widened by recover null
        infer:
          prompt: "Assemble a bundle. Set complete=false if any entry is null. ${{ in }}"
        returns: Bundle

outputs:
  bundle: { type: Bundle, value: ${{ flow.output }} }
```

### C·T3 — bounded agent

```yaml
nika: v1
workflow:
  id: bounded-research

types:
  ResearchLog:
    findings: string[]
    sources: uri[]
  Digest:
    summary: string

inputs:
  topic: { type: string, required: true }

policy:
  allow:
    - net:*
    - fs.write:./notes/**
  limits:
    cost_usd: 0.15

flow:
  then:
    - researcher:
        agent:
          model: local/qwen
          prompt: "Research ${{ inputs.topic }}. Log findings with sources."
          tools: [nika:fetch, nika:write]
          stop:
            max_turns: 8
            timeout: "2m"
            max_cost_usd: 0.10
        returns: ResearchLog

    - digest:
        expects: ResearchLog         # refuses any reorder that changes what flows in
        infer:
          prompt: "Write a one-paragraph digest of these findings. ${{ in }}"
        returns: Digest

outputs:
  digest: { type: Digest, value: ${{ flow.output }} }
```

### C·T4 — exec pipeline with a DIAMOND

```yaml
nika: v1
workflow: build-test-bench-deploy

types:
  BenchReport:
    mean_ms: number
    regressions: string[]

config:
  deploy_enabled: { type: bool, default: false }

policy:
  allow:
    - exec:cargo
    - exec:./scripts/**

tasks:                               # bodies out of line — the flow below is pure shape
  build:
    exec: { command: ["cargo", "build", "--release"] }

  test:
    exec: { command: ["cargo", "test", "--workspace", "--lib"] }

  bench:
    exec:
      shell: "cargo bench --quiet | ./scripts/bench-to-json.sh"   # explicit shell door
      decode: json                   # explicit decoder · required for a record returns:
    returns: BenchReport

  deploy:
    when: ${{ config.deploy_enabled }}   # local gate · evaluated only after the join
    exec: { command: ["./scripts/deploy.sh"] }

flow:
  then:
    - build
    - parallel: [test, bench]        # both branches receive build's position
    - deploy                         # THE JOIN: runs when BOTH settle success
                                     # in = { test: string, bench: BenchReport } — unread
                                     # here, so the projection records an order-only edge
```

### C·T5 — resilience (detached task · observation edge · `pipe: none`)

```yaml
nika: v1
workflow: fetch-with-fallback

config:
  feed_url: { type: uri, default: https://example.org/feed.json }

policy:
  allow:
    - net:example.org
    - fs.read:./cache/**
    - exec:rm

tasks:
  cache_read:                        # DETACHED — declared here, never placed in flow:
    invoke:                          # start-eligible at t0 · runs concurrently
      tool: nika:read
      args: { path: ./cache/latest.json }

flow:
  then:
    - live:
        invoke:
          tool: nika:fetch
          args: { url: ${{ config.feed_url }} }
        timeout: "30s"
        retry: { max_attempts: 3, backoff_strategy: exponential }
        on_error:
          recover: ${{ tasks.cache_read.output }}   # recovery-time read of the
                                                    # detached task (awaited terminal)
        on_finally:
          - exec: { command: ["rm", "-f", "./cache/fetch.lock"] }

    - notify:
        pipe: none                   # sever the positional value edge (PIPE-004)
        with:
          st: ${{ tasks.live.status }}   # terminal-observation edge:
                                         # notify runs when live is TERMINAL, any outcome
        invoke:
          tool: nika:emit
          args: { event: fetch_settled, status: ${{ with.st }} }
```

### C·T6 — auditable decision (two-input stage)

```yaml
nika: v1
workflow: pr-triage

types:
  Evidence:
    pr_number: number
    checks: string[]
    review_events: string[]
  SemanticFacts:                     # CLOSED analytic enums — the LLM classifies, never decides
    ci_state: enum[passing, failing, unknown]
    review_state: enum[approved, changes_requested, none]
    risk: enum[low, medium, high]
  Decision:
    lane: enum[auto_merge, review, human_required]
    reasons: string[]

inputs:
  pr: { type: number, required: true }

flow:
  then:
    - gather:
        invoke:
          tool: mcp:github-facts/pr_evidence
          args: { pr: ${{ inputs.pr }} }
        returns: Evidence

    - judge:
        infer:
          prompt: "Classify this PR evidence. Facts only, no recommendation. ${{ in }}"
        returns: SemanticFacts       # constrained decoding against the closed enums

    - decide:                        # a TWO-INPUT stage: pipe + one explicit tap
        with:
          evidence: ${{ tasks.gather.output }}   # 2nd upstream · explicit value edge
        invoke:
          tool: nika:decide
          args:
            bundle: registry:linkml/pr-triage@1.2.0
            evidence: ${{ with.evidence }}       # Evidence · typed value position
            facts: ${{ in }}                     # SemanticFacts · the pipe
        returns: Decision

    - apply_label:
        when: ${{ in.lane != 'human_required' }} # local gate over the typed pipe
        invoke:
          tool: mcp:github-facts/add_label
          args: { pr: ${{ inputs.pr }}, label: ${{ in.lane }} }
```

### C·T7 — composition

```yaml
nika: v1
workflow: research-then-summarize

types:
  ResearchReport:
    title: string
    findings: string[]

inputs:
  topic: { type: string, required: true }

flow:
  then:
    - research:
        invoke:
          tool: nika:workflow
          args:
            path: ./research.nika.yaml
            inputs: { query: ${{ inputs.topic }} }   # parent value -> child inputs authority
        returns: ResearchReport      # checked against the child's outputs: contract

    - summarize:
        infer:
          prompt: "Summarize the report findings in five bullets. ${{ in.findings }}"
        returns: string

outputs:
  summary: { type: string, value: ${{ flow.output }} }
```

### C · self-critique (12 criteria · authored by the candidate)

1. **Readability.** Chains read top-to-bottom as the execution actually happens — T1/T3/T7 are near-prose. It degrades on non-series-parallel meshes: a graph where `c` and `d` each read both `a` and `b` but `c` also feeds `d` forces taps and `after:` on top of position, and the reader must merge TWO edge systems mentally — strictly worse than one explicit system.
2. **Agent generability.** LLMs have a strong linear bias; generating a fresh chain in C is close to error-proof (no ids to cross-reference, no `depends_on` to forget). The failure mode is **edit-in-place**: an agent inserting a logging stage mid-chain silently retypes every downstream `in`; value positions catch it, string positions (`prompt: ${{ in }}`) do not — the prompt silently starts carrying the logger's output. `expects:` pins mitigate only where authors bothered to write them.
3. **Analyzability.** The lowering is total and deterministic, so the analyzer sees the same core graph as A/B; positional cycles are impossible by construction. Residual weakness: anonymous combinators have structural ids (`flow[1].map`) which drift when the flow is edited — trace continuity across refactors is worse than stable named nodes.
4. **Typing.** The pipe is checked at the seam (producer's `returns:` against every consumer read) — stronger ergonomics than checking each `with:` binding separately. The honest hole is string-position coercion: a reorder that changes `in` from `Summary` to `Article` type-checks in `prompt:` and only `expects:` or a human catches it.
5. **Security.** No delta versus the core: authorities, secret egress, policy, argv/shell split untouched; status/error can never ride the pipe, so observation edges remain visible and auditable.
6. **Git diff.** Reordering a chain is a one-line move; renaming an inline stage touches one line. The trap is the inverse: moving a stage changes its semantic input with **zero diff on the stage itself** — review tooling sees an innocent move where the meaning of every downstream `${{ in }}` changed.
7. **LSP.** Completion for `in.` is implementable (the pipe type at any cursor is statically known) but flow-sensitive: the server must resolve the combinator path to type `in`. Deeply nested contexts (`map.do.then[2].parallel[1]`) are exactly where schema-driven YAML completion is weakest; C makes the LSP a hard requirement rather than a nicety.
8. **Concision.** Chains lose all plumbing (T4's whole topology is three flow lines). On wide meshes concision inverts: every extra edge is a tap PLUS the reader-cost of knowing position no longer tells the whole story.
9. **Extensibility.** New COMBINATORS are reserved words: adding `switch:` in a minor collides with any workflow that named a stage `switch` — a breaking-hazard class surface A structurally does not have. The combinator set must be closed-at-v1.
10. **Provability.** Small and strong: the conformance surface is the lowering (golden desugar fixtures — C file in, canonical core out, byte-stable), after which every core proof is inherited.
11. **Performance.** Desugaring is a single tree walk at parse time; the scheduler and runtime are the core's, unchanged.
12. **2060 fit.** Chains age well. The decade risks: nesting depth (a `map` containing a `parallel` containing a `then` is write-only YAML at three levels — cap nesting at two, push depth into child workflows) and archaeology on old diffs where a stage move hid a retyping.

### C · error classes

**Made inexpressible by C (position IS the edge):** reference-without-edge on the main path (reading `${{ in }}` and having the edge are the same act) · pipe cycles (the combinator tree is acyclic by construction) · dangling/typo'd task ids in chains (a linear C workflow cites zero task names) · forgotten join member (`parallel:` joins ALL branches by construction) · accidental run-after-failure (a positional value edge always demands success; running on failure requires the explicit observation ceremony — `PIPE-004` rejects the contradictory middle).

**Introduced by C:** silent retyping on insert/move (the signature ambush — string positions absorb the change without a diagnostic; `expects:` pins are opt-in) · join-shape coupling (renaming a `parallel:` branch is a data-shape change for the consumer) · two edge systems in one file (position + taps/after — escape hatches concentrate exactly in the hardest files) · two homes for a task (inline vs `tasks:` map) · deep nesting (three levels of indentation-bearing semantics) · anonymous-node addressing (structural ids renumber on edit, degrading longitudinal trace comparison).

### C · verdict (authored by the candidate)

Surface C objectively beats explicit named bindings where workflows are what most workflows are: a chain with at most one fan-out. There it deletes the entire plumbing layer, makes the dominant error class unspellable, gives the type checker a seam that reports mismatches at the exact line where data changes hands, and yields diffs where a reorder is a move. It also composes naturally: stage and child workflow share the same `in -> returns` function shape. C loses, and loses honestly, on everything that is not tree-shaped: meshes and two-upstream stages reintroduce explicit bindings on top of position so the reader now merges two edge systems; observation edges need ceremony; edit-in-place is a typed minefield because position carries meaning that diffs do not show; the LSP goes from helpful to load-bearing; and reserved combinator names create a forward-compat hazard the core structurally avoids. **The strongest position for C is therefore not as *the* surface but as a defined-by-lowering layer over the explicit core**: the spec keeps one semantic truth, tooling can round-trip (`fmt --explicit` / `fmt --flow`), authors and agents write chains in C, and the hard graphs fall back to the core without changing language. If the tournament must pick a single authoring surface for all workflows including meshes, C is the wrong sole choice; if it may pick a canonical core plus one blessed sugar, C is the sugar worth blessing.

---

## 7 · Scoring

### Per-criterion verdicts

| # | Criterion | A verb-keyed | B tagged-op | C combinators |
|---|---|---|---|---|
| 1 | Readability (human) | **win** — verb keys are skim landmarks | lose — uniform monotony, +1 indent | win on chains · **lose on meshes** (two edge systems) |
| 2 | Agent generability | win — matches every model's prior | **win (fresh gen)** · lose (drift back to A-shape without schema) | win (fresh chains) · **lose (edit-in-place silent retyping)** |
| 3 | Analyzability | win — structural dispatch, keysets | win — op-blind envelope (quarantine, not reduction) | neutral — total lowering, but structural ids drift |
| 4 | Typing | neutral | **win** — textbook discriminated union | win at the seam · **hole in string positions** |
| 5 | Security | win — `shell:` greppable field | win — `grep 'op: agent'` | neutral — core untouched, observation ceremony explicit |
| 6 | Git diff | win — one-line field adds | win (op migration) · **lose (whole-corpus re-indent + context-less hunks)** | win (reorder=move) · **lose (move changes meaning with zero diff)** |
| 7 | LSP complexity | **win — the keysets door already IS this surface's completion model** | mid — sibling lookup + degraded generic-YAML `oneOf` diagnostics | **lose — flow-sensitive typing makes the LSP load-bearing** |
| 8 | Concision | mid — one verb key per task | **lose — +2 lines +1 indent per task, forever** | **win on chains** · inverts on meshes |
| 9 | Extensibility | win — additive task keys · sugar-space exists | win — enum value + table · **no sugar-space** | **lose — reserved combinator names = forward-compat hazard** |
| 10 | Provability | win — judgment reads off the shape · verb→tag lift ≈ a dozen lines | **win — surface ≈ canonical IR** (minor trusted-surface saving) | win — lowering is the whole conformance surface |
| 11 | Performance | neutral | neutral | neutral (parse-time tree walk) |
| 12 | 2060 fit | **win — a human reads `infer: prompt:` aloud** · the verb lock is encoded structurally | win for machines (tagged records = IDL lingua franca) | risk — nesting depth + diff archaeology |

### The operator cost function

```
TotalCost = Ambiguity + Duplication + HiddenAuthority + InvalidStates
          + LspComplexity + AgentComplexity + FutureDebt
```

| Term | A | B | C |
|---|---|---|---|
| Ambiguity | low (verb = structure) | low (closed enum) — but op-as-data may sit anywhere in the map | **high on meshes** (position + taps + after to merge mentally) |
| Duplication | none (model kills it) | none | none on chains · taps duplicate position's job on meshes |
| HiddenAuthority | none (model kills ambient env) | none | none |
| InvalidStates | two-verbs task = checker reject (PARSE-class, precise teaching) | **structurally unstateable** (B's real win) — but adds op-less-plausible + stale-discriminant states | run-after-failure unstateable · adds silent-retype states |
| LspComplexity | **lowest — today's oracle (keysets · lanes · hover anchors) is A-shaped** | medium (mid-edit no-op state · generic tooling degraded) | **highest (flow-sensitive · load-bearing)** |
| AgentComplexity | low — 4 templates, matches priors | low fresh-gen / medium edit (drift teaching loop) | low fresh-gen / **high edit-in-place** |
| FutureDebt | low — sugar-space open, no reserved words | medium — indent tax paid forever, sugar-space closed | **high — reserved words + nesting caps + trace-id drift** |

Two structural facts weigh beyond the table. First, most error classes the
refonte kills are killed by the **fixed semantic model**, not by any surface:
all three candidates equally bury reference-without-edge, ambient authority,
unbounded agents, output-contract duplication and scheduling/business-gate
conflation. The surfaces differ only on the residual classes above. Second,
the entire one-voice oracle shipped today — the parser keysets door, the
completion lanes, the hover anchors, the 262-workflow corpus, the starters and
authoring-shapes SSOT, and every model's training prior — is A-shaped. B's
machine elegance is reproducible with a twelve-line verb→tag lift in the
canonical IR (its own author concedes this); B's costs (per-task tax, new
drift classes, degraded generic tooling, corpus re-indent) are paid at the
surface forever.

---

## 8 · Decision (normative once ruled)

**RULED (operator lock 2026-07-13 · normative): Candidate A, verb-keyed typed dataflow — with B's IR lift absorbed under the hood and C rejected as a normative surface (sugar-by-lowering stays a post-1.0 hypothesis only).**

- **B is rejected as the surface** — its genuine wins (structurally
  unstateable two-op tasks; surface≈IR) are reproduced at near-zero cost in
  the canonical IR by promoting the verb key to a tag, while its costs are
  permanent, per-file and human-facing: two boilerplate lines and one indent
  level on every task forever, the stale-discriminant and op-less-plausible
  drift classes that a verb-keyed surface cannot even express, degraded
  generic-YAML diagnostics, a closed sugar-space, and a whole-corpus
  re-indent whose only yield is uniformity. Counterexample on record: the
  mid-edit state (`params:` typed before `op:`) has no resolvable completion
  table — the flagship editing flow gets worse, not better.
- **C is rejected as the sole surface, by its own author's verdict** — on
  anything not tree-shaped it degenerates into two edge systems; a stage
  MOVE changes the meaning of every downstream `${{ in }}` with zero diff on
  the moved stage (string positions absorb the retype silently); combinator
  names become reserved words (a forward-compat hazard A structurally
  avoids); and the LSP becomes load-bearing for basic comprehension.
  Counterexample on record: inserting a logging stage mid-chain silently
  rebinds every downstream pipe read.
- **C-as-blessed-sugar stays an explicitly open POST-1.0 option** — defined
  by total lowering to the A core (`fmt --explicit` / `fmt --flow`
  round-trip), it could serve chain-heavy authoring without ever entering
  the semantic model. It is NOT part of 1.0: one release never ships two
  worlds, and the pre-1.0 window is for hardening one truth, not blessing
  two spellings.
- **A is the surface** — it keeps the verb lock structural, its completion
  and analysis model is literally the oracle already shipped, it preserves
  the training prior of every authoring model, it leaves sugar-space open,
  and every error class it does not kill structurally it kills with a
  precise checker teaching (the 0.103 pattern: refuse + teach + machine-fix).

The residual B-only win (a task physically cannot carry two operations) is
accepted as a checker-enforced law in A (unchanged from today's PARSE-class
reject with its teaching), judged an acceptable trade against B's permanent
surface tax.

---

## 9 · Errors made inexpressible (the punch table)

Classes killed by the FIXED MODEL (all candidates · the refonte's real yield):

| # | Error class | Killed by |
|---|---|---|
| 1 | Reference without a dependency edge | the binding IS the edge (`with:` promotion) |
| 2 | Dependency edge whose value is never used | order-only waits move to `after:` — a binding that is unread is a lint, an unused `after:` is visible |
| 3 | Duplicate task ids / id-position divergence | tasks-as-map + duplicate-key reject |
| 4 | Ambient environment reads | authorities are declared or they do not exist |
| 5 | Secret interpolation into arbitrary strings | secrets are store-refs with sink-bound egress (checker: leak = error) |
| 6 | Scheduling gate vs business condition conflation | `after:` (states) ⊥ `when:` (local authorities only — task states illegal) |
| 7 | Output contract duplicated across verb mechanisms | one `returns:` per task; decoding is explicit mechanics |
| 8 | Unbounded agents by omission | bounded by default + `policy.forbid: unbounded_agents` |
| 9 | Value-read racing a failed producer | edge roles: a value edge admits only on success; observing failure is a different edge |
| 10 | Success-gate tautology (the old redundant `when` status pattern) | gate algebra: default gate + `after:` states replace status-`when` entirely |

Classes killed by SURFACE A specifically:

| # | Error class | Mechanism |
|---|---|---|
| 11 | Operation named by data that can drift from its parameters | the verb IS the key — a stale discriminant is unstateable |
| 12 | Task with plausible params but no operation | a task without a verb key is visibly incomplete (keyset check with teaching) |
| 13 | Verb-vocabulary collision with envelope fields | task-level keyset is closed; verbs are structural, not values |

Classes A leaves to the CHECKER (with precise teachings — the accepted trade):

| # | Class | Teaching |
|---|---|---|
| 14 | Two verb keys on one task | PARSE-class reject naming both keys (existing law) |
| 15 | Verb typo (`infre:`) | did-you-mean over the 4-verb keyset |
| 16 | `returns:` demanding a decode `exec` cannot produce | cross-field law: record type ⇒ `decode:` required |

---

## 10 · The callable layer (ratified with the surface)

The ruling extends the constitution below the surface: `invoke` is the
universal door to everything callable, and one contract feeds every judge.

### 10.1 `invoke` — a tagged union, never a magic builtin

`invoke` carries **exactly one** target field plus `args`:

```yaml
invoke:
  tool: nika:fetch          # catalogue capability (nika: · mcp:)
  args: { url: "…" }
```

```yaml
invoke:
  workflow: ./flows/risk-review.nika.yaml   # composable child · static literal
  args: { diff: "…" }
```

The field carries the semantics (the `command:`/`shell:` law generalized):
the parser knows structurally whether it resolves a catalogue capability or
a composable child. Hiding the child behind a generic `nika:workflow` tool
whose target lives in `args` is REJECTED — it would bury the output type,
the effects and the composition graph inside an argument value, show a
generic builtin in permits instead of the child's identity, and hand agents
a path-shaped power. In the IR both arms are one tagged `CallableRef`
(`Tool | Workflow`); a single-string `target:` spelling is likewise rejected
(prefix-parsing a string to recover semantics is the defect `command:`
strings had).

### 10.2 The CallableContract — one truth for every judge

Every invoke target (builtin · MCP tool · local child · registry child ·
pure decision · human interaction) exposes the same abstract contract:

```
Callable<I, O, E, ε, ρ, δ>
   I inputs · O output · E errors · ε effects · ρ resources ·
   δ determinism/idempotence
```

One **Callable Catalog** serves that contract to the checker, the runtime,
the agent loop, the LSP, the MCP oracle, the registry and the lockfile —
never per-surface partial views. A child workflow's contract is **derived**
from its body (inputs from its public surface · output from its outputs
contract · errors from its unrecovered terminals · effects/resources from
its reachable tasks · determinism from its operations); no manual
annotation can claim purity the body does not prove.

### 10.3 Composition laws (bind W-COMP)

1. **Static target** — local path is a literal; registry ref is resolved and
   hash-pinned in the lockfile; no expression-built targets.
2. **Typed call** — args satisfy the child's input contract (missing ·
   unknown · type-mismatch · unmapped-secret = findings).
3. **No implicit power** — the child receives nothing automatically:
   `Authority(child) ⊆ Authority(parent) ∩ DeclaredAuthority(child)`.
4. **Effect containment** — `RequiredEffects(child) ⊆ PermittedEffects(parent)`;
   calling can never widen the parent.
5. **Resource composition** — child costs/tokens/calls/artifacts sum into
   the parent certificate.
6. **Inherited deadlines & budgets** — the child never receives more than
   the parent's remaining budget or deadline.
7. **Acyclic call graph** — statically rejected cycles; a runtime depth cap
   is defense-in-depth, not the rule.
8. **Trace forest** — the child keeps its own hash-chained trace; the
   parent records its semantic hash, plan hash, trace id, chain head and
   outcome.
9. **Composed receipts** — child receipt roots Merkle into the parent's;
   one altered child breaks the parent's proof.
10. **Semantic cache** — child check memoization keys on
    (semantic hash · locked deps · input contract), never on file path.

### 10.4 Cross-cutting operation laws

- **Payload ⊥ Telemetry ⊥ Provenance** — a tool result separates the three;
  billing signals never ride business fields (reading a payload `cost_usd`
  as engine spend is a defect, not a feature).
- **Definition snapshots** — MCP definitions used at check time are
  captured, hashed and locked; a differing runtime definition refuses or
  re-resolves, never silently executes a different contract.
- **Agent capability closure** — agents choose among pre-approved
  capabilities only: public surface `tools:` and `workflows:` allowlists
  (globs resolve to exact sets in the lockfile); IR-side one tagged
  `CapabilitySet`; no path-shaped or dynamic targets.
- **Parallel safety** — concurrent calls require proven effect independence
  (read/write set disjointness; idempotence/commutativity for external
  effects) or they serialize; no optimistic invisible parallelism.
- **Value-dependent effects** — literal arg = exact effect · closed enum =
  finite union · unknown dynamic = widened effect or finding · never
  silently dropped.
- **Guarantee levels** — every displayed property carries its honest level:
  `statically_proven · runtime_enforced · best_effort · observed · unknown`
  (a shell blocklist is best_effort; a cycle rejection is statically_proven).

---

## 11 · Open decision points feeding the next chapters

These are surfaced by the tournament and ruled separately (each becomes a
normative spec section when locked):

1. **Authority model spelling** — `inputs:` / `config:` / `const:` /
   `secrets:` (names, required/default grammar, hash impact per authority).
2. **Type core boundary** — the exact decidable subset and its canonical
   lowering to JSON Schema 2020-12; out-of-core schemas stay usable but
   analyze as Unknown.
3. **Edge-role table** — the normative projection→role→admission-predicate
   mapping (value · terminal-observation · failure-observation · control ·
   recovery · finally) and its `graph_format: 2` serialization.
4. **Outcome IR** — terminal class × cause × payload; the transition table
   every surface (runtime · trace · LSP · assertions) consumes.
5. **Canonical semantic IR** — desugaring set, default expansion, Unicode/URI/
   duration normalization, domain-separated hashes (JCS).
6. **Evidence contract** — typed facts with integrity × confidentiality
   lattices, freshness, completeness, independence, four-valued logic.
7. **Decision contract** — fixed-point rubric IR, monotonicity declarations,
   interval propagation, abstention.
8. **Governance contract** — never-automatic actions, append-only overrides,
   public/private receipt split.
9. **Scientific validation protocol** — agreement metrics per output type,
   coverage and abstention always reported.
10. **Portability proof** — an independent second evaluator must reproduce
    golden decisions byte-for-byte before a bundle is called portable.

## Update log

- 2026-07-13 · RFC skeleton + fixed semantic model + witnesses + candidate A ·
  candidates B/C and scoring land in this same PR before review.
- 2026-07-13 (same evening) · **RATIFIED by operator ruling** — A locked as the
  sole canonical surface (B = IR lift under the hood · C = post-1.0
  sugar-by-lowering hypothesis only) · the four forms re-ratified as three
  atomic calls + one bounded controller · §10 callable layer added (invoke
  tagged union tool|workflow · CallableContract · composition laws ·
  guarantee levels) · 02-verbs.md forward-compat prose reconciled in the
  same window.
