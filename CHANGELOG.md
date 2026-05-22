# Nika spec · CHANGELOG

All notable changes to the **Nika workflow language specification** are
documented here. The spec is pinned at the `nika: v1` contract forever ·
language additions are additive within v1 (feature-detected · no minor
version in the file). Stdlib (providers · extract modes · builtins) versions
independently.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added — for_each concurrency control + on_finally cleanup hook + 4 clarifications

D-2026-05-22-N24 · ultrathink session · « ok enregistre tout ce qui manque ·
verifie buildin + brouillon · prend les meilleures conventions · max parallel
on a Rust+Tokio pas pour rien · go au max ». User-locked. 3 NEW additive
fields (zero breaking · within nika: v1) + 4 clarifications (zero new fields).

- **NEW `max_parallel:` on `for_each:` block** · cap concurrent iterations ·
  optional · positive integer · default UNBOUNDED · engine impl via
  `tokio::sync::Semaphore`. Critical for production · rate-limit upstream
  APIs · avoid DOS on `for_each` over 1000+ items · compliance with provider
  concurrency limits. Field name `max_parallel:` per GitHub Actions canon
  (matrix.max-parallel) · explicit naming (vs brouillon's `concurrency:`
  which we considered but rejected for clarity).

- **NEW `fail_fast:` on `for_each:` block** · abort-on-error policy ·
  optional · boolean · default TRUE (first iteration error aborts remaining
  iterations · parent task fails immediately). When false · iteration
  errors are collected · all iterations run to completion · parent fails
  after all iterations done (with per-iteration error details). Brouillon
  convention adopted (best-of-best · production-essential for « process
  all even if some fail » pattern).

- **NEW `on_finally:` task field** · cleanup hook list of mini-tasks that
  ALWAYS run after the parent task completes (success/fail/timeout/cancel).
  Sequential in declared order · errors LOGGED but NOT propagated to
  parent status (best-effort semantics). Universal cleanup pattern · cf
  Argo `onExit:` · Temporal `defer` · GitHub Actions `if: always()` ·
  LangGraph `finally` · Airflow `on_failure_callback`.

- **NEW for_each « parallel-by-default » explicit callout** · spec
  clarification (C2) · big warning box · for_each is PARALLEL by default
  (differs from Python's sequential `for` loop) · `max_parallel: 1`
  forces sequential.

- **NEW `when:` CEL boolean conformance rule** · spec clarification (C3) ·
  `when:` MUST be a CEL expression returning bool · engine rejects
  non-boolean expressions at parse time (`NIKA-PARSE-WHEN-001`). Examples
  · valid (comparisons · `&&` · `||` · `null` checks) · invalid (integer ·
  object · string · literal). Truthy-coercion forbidden · explicit
  comparison required.

- **NEW raw-output-vs-named-bindings clarification** · spec clarification
  (C1) · `tasks.X.output` is the raw verb output · `tasks.X.<name>` are
  the JSONPath-extracted named bindings · both dual-accessible · reserved
  names (`output` · `status` · `error` · `started_at` · `ended_at` ·
  `duration_ms`) cannot be used as binding names.

- **NEW YAML multi-line `|` canonical guidance** · spec clarification
  (C4) · `|` (literal · preserves newlines) is canonical for prompts /
  system / command fields · `|-` (literal + strip trailing) alternative ·
  `>` and `>-` (folded · collapses newlines into spaces) FORBIDDEN in
  prompts (corrupts LLM intent).

### Skipped — `nika:notify` · `nika:uuid` · `nika:date` · `nika:hash` · `nika:wait_until`

Brouillon audit revealed these 5 builtins NOT in current brouillon
nika-builtin/src (no notify.rs · no uuid.rs · no date.rs · no hash.rs ·
no wait_until.rs). Adding them would change the spec MANDATE from 37 to
42 builtins · catastrophic spec/engine consistency violation per D-N22
architect-audit-verdict. Per Rams 10 « less but better » · current 37 list
is the v0.81 conformance contract · expansion to 42+ is a v0.2 candidate
requiring explicit user re-lock + spec amendment.

---

## [Previous Unreleased] — task-level `timeout` duration string + `output_format` type hint

User-locked v0.2 amendment candidates from `nika/hq/blueprint/NIKA_ROADMAP.md` §16
(D-2026-05-22-N23 · « Aok Bok Cok »). Two additive changes within `nika: v1` · zero
breaking · per forever-v0.x discipline (additive on language MINOR-equivalent).

- **`timeout_ms: 30000` → `timeout: "30s"`** · Go-duration / Kubernetes-style string ·
  format `[0-9]+(\.[0-9]+)?(ns|us|µs|ms|s|m|h)` · compound `"1h30m"` · MUST be
  quoted (YAML 1.2 numeric trap defense). Adopters get cleaner reads · `"5m"` >
  `300000`. Industry standard · Go `time.ParseDuration` · Kubernetes resource
  limits · Prometheus rules. Replaced at 7 sites · `03-dag.md` x4 ·
  `02-verbs.md` x3 · `07-conformance.md` x1.

- **NEW `output_format` task-level field** · optional · closed enum
  `text | structured | bytes` · default **inferred per verb**
  (`infer:` text-or-structured · `exec:` structured · `invoke:`
  structured · `agent:` structured). Explicit override unlocks **`bytes`**
  for binary output (the only-way · downstream consumers become binary-aware
  · avoids UTF-8 corruption via string substitution) AND statically declares
  shape for IDE autocomplete + parse-time mismatch detection. Section at
  `03-dag.md#output_format`.

### Skipped — `workflow:` `description:` field

Already existed in spec (`01-envelope.md:109`) · candidate B was redundant.

---

## [Previous Unreleased] — more local providers + stabilization

More local-provider options + a few consistency fixes.

- **5 local providers** now (was 2) · added `llamacpp` (llama.cpp `llama-server`
  `:8080`) · `localai` (`:8080` · OpenAI drop-in · multi-backend) · `vllm`
  (`:8000` · high-throughput · self-hosted). All external OpenAI-compatible HTTP
  servers — NOT the deferred in-process `native` GGUF runtime. Providers 10 → 13.
- **The `openai` escape hatch documented** · any other OpenAI-compatible server
  (Jan · llamafile · KoboldCpp · text-generation-webui · OpenRouter · Together ·
  custom) routes via `model: openai/<name>` + `OPENAI_BASE_URL` engine config —
  no new provider name. The LiteLLM pattern: named providers for the popular
  backends + `openai`+base_url for the long tail. (« Did we plan to add more? »
  → yes: named-provider set + escape hatch + independent stdlib versioning.)
- **`secrets source:` is now a closed enum** · `vault` (default · sovereign) ·
  `env` (read a secret from an OS env var · still masked) · `file` (Docker/k8s
  mounted secret). Previously only `vault` was shown → an author couldn't know
  what else was valid.
- **`exec.env` vs envelope `env:` disambiguated** · the one same-word overlap.
  Envelope `env:` = workflow config (`${{ env.* }}`) · `exec.env` = the OS
  environment of *that subprocess* · NOT auto-connected · pass values through
  explicitly. Crisp note added so it isn't a trap.

Audit also confirmed CLEAN (no change): tool refs consistently `namespace:path`
with `/` (zero `::` survivors) · Connectome is `nika:connectome/recall`
everywhere (no dot drift) · the kebab `workflow:` vs snake task-`id` split is
justified (CEL hyphen-minus) and documented.

### Changed — model selection · one field

Research-validated against LiteLLM · OpenRouter · Vercel AI SDK · PydanticAI
(all converged on a single `provider/model` string).

- **`provider:` + `model:` collapsed into ONE `model: <provider>/<name>` field.**
  The provider is the prefix (`anthropic/claude-sonnet-4-6` · `openai/gpt-4o`).
  Removes the silent-nonsense trap (`provider: anthropic` + `model: gpt-4o`) ·
  one atomic, self-documenting, swappable string · the de-facto industry
  convention. Applied across envelope · verbs · stdlib contract · providers doc
  · overview · README. The `provider:` field no longer exists.
- **Local-vs-cloud = the prefix.** `ollama/…` · `lmstudio/…` = LOCAL (localhost ·
  no key · sovereign) · the 7 cloud providers = CLOUD (key via `${{ secrets.* }}`) ·
  `mock/…` = TEST. No separate `local:` flag · no hidden config.
- **Providers 8 → 10.** Added `ollama` + `lmstudio` as first-class local providers
  (external OpenAI-compatible HTTP servers · NOT the crash-prone in-process
  `native` GGUF runtime, which stays deferred). `model: ollama/llama3.1`
  makes a zero-cloud run trivial.
- **Provider config stays OUT of the workflow** · `base_url` + auth in
  engine/provider config · a workflow only *selects*. Combine with typed `vars`
  to parameterize the model and run one workflow against any backend.

Pre-public hardening of the v0.1 draft (no adopters yet · free to perfect the
pillars to their immutable-forever form). Grounded in SOTA primary sources ·
CEL (cel.dev) · RFC 9535 JSONPath · OpenAPI single-field envelope · Docker
Compose versionless · AWS exponential-backoff-and-jitter.

### Changed

- **Envelope → `nika: v1`** · one field (was two · `apiVersion` + `schema`).
  Follows the OpenAPI `openapi: 3.1.0` pattern · the document type is
  discriminated by the resource key (`workflow:`).
- **The 4 verbs are absolute** · the count is locked at 4 forever · the
  operation space is complete · `fetch` is a TOOL not a verb (`invoke: nika:fetch`) ·
  a 5th verb would require `nika: v2` (never).
- **Expression language = CEL** (Common Expression Language · cel.dev) ·
  everything inside `${{ }}` — substitutions and `when:` predicates — is a
  documented subset of CEL. Common · validated · non-Turing-complete · portable
  (zero parser drift). Engines may embed a CEL interpreter or implement the
  small v0.1 subset.
- **Task `id` = snake_case** (`^[a-z][a-z0-9_]*$`) · ids appear in CEL paths
  (`tasks.fetch_page.output`) where a hyphen is CEL's minus operator. The
  `workflow:` name stays kebab-case (it never appears in an expression).
- **Message fields unified** · `infer:` and `agent:` both take `system:` +
  `prompt:`.
- **Tool reference grammar** · `<namespace>:<path>` with a `/` hierarchy ·
  `nika:write` · `nika:connectome/recall` · `mcp:browser/navigate` · globs
  `mcp:browser/*`. One colon for the namespace, slash for the path.
- **Agent tools default-deny** · `agent.tools:` absent → no tools (least
  privilege · pure conversation).
- **Cross-cutting fields are task-level** · `timeout_ms` and `retry` live on
  the task, not inside a verb block.
- **Output binding is RFC 9535 JSONPath** · engines use any RFC 9535
  implementation.
- **Builtin count = 36** (Core 6 + File 5 + Data 19 + Introspection 6).

### Added

- **`for_each:`** · bounded map / fan-out over a static list or a prior task's
  array output (`${{ item }}` · `${{ index }}`).
- **`${{ secrets.X }}`** · 5th variable namespace · vault-backed · masked in
  logs · the modern `env` ⊥ `secrets` security split.
- **Typed `vars`** · optional `{ type, required, default, description }` form
  (enables input validation + schema generation) · the simple `name: value`
  form is preserved.
- **`nika:done`** · agent-loop completion sentinel · error if invoked outside
  an `agent:` loop.
- **YAML conventions section** (in `01-envelope`) · a Nika file is YAML 1.2 ·
  one rule covers the classic generated-config footguns (the Norway problem
  `no` → boolean · leading-zero octal · sexagesimal `12:30` · version floats
  `1.10` → `1.1`) · quote anything that could be misread, and any expression
  containing `: # [ { , >`.
- **Canonical JSON Schema** · `schemas/nika-workflow.schema.json` is the
  machine-readable companion (envelope + task + verb shapes) for editor
  autocomplete + inline validation (the same DX as GitHub Actions / Docker
  Compose). The prose spec stays normative.
- **Retry `jitter`** · default on · full-jitter / equal-jitter family (AWS
  exponential-backoff-and-jitter) · anti-thundering-herd.
- **Conformance levels clarified** · Core is a static-check mode (`when:` /
  `for_each:` references resolve to known namespaces but are not evaluated) ·
  runtime evaluation is Level 2.

> Still towards v0.1.0 GA · examples + conformance fixtures + JSON schemas
> pending.

---

## [0.1.0-draft] — 2026-05-22

### Added

- Initial spec repo · Apache-2.0 (patent grant for implementers).
- `spec/` · 9 sections · envelope · 4 verbs · DAG · variables · errors · stdlib
  contract · conformance · out-of-scope.
- `stdlib/` · curated v0.1 lists (13 providers · 9 extract modes · 36 builtins ·
  media builtins deferred to a later stdlib release).
- `examples/` · placeholder (26 canonical workflows pending).
- `conformance/` · placeholder (test suite for the « v0.1-compliant » claim).
- `schemas/` · placeholder (JSON Schemas for `yaml-language-server`).

### Decisions

- **5 pillars immutable forever** · envelope · 5 verbs · DAG · variables ·
  errors. Everything else evolves in the stdlib.
- **License split** · the spec is Apache-2.0 (adoption + patent grant) · the
  reference engine is AGPL-3.0-or-later (anti-extraction).
- **Stdlib v0.1 inclusion list** · the providers / extract modes / builtins
  shipped at v0.1 (see `stdlib/`).

---

## Why no « 0.0.x »

This spec starts at v0.1.0-draft because it **derives from empirical
examples**, not from scratch · an earlier Nika prototype already ran 26
canonical workflows. The v0.1 spec distills that experience into the locked
contract.

The first GA release (`0.1.0`) is cut when ·

1. All 9 spec sections finalized + reviewed.
2. 26 examples published clean (`examples/`).
3. Conformance tests published (`conformance/tests/`).
4. JSON schemas consumable by `yaml-language-server` (`schemas/`).

After GA the 5 pillars are immutable forever. The stdlib evolves independently
via its own versioning (`stdlib/providers-v0.x.md` · etc.).
