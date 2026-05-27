# Nika spec · CHANGELOG

All notable changes to the **Nika workflow language specification** are
documented here. The spec is pinned at the `nika: v1` contract forever ·
language additions are additive within v1 (feature-detected · no minor
version in the file). Stdlib (providers · extract modes · builtins) versions
independently.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

Pre-public hardening of the v0.1 draft (no adopters yet · free to perfect the
pillars to their immutable-forever form). Every change below is **additive
within the `nika: v1` contract** — the 5 pillars stay immutable; the stdlib
versions independently. Grounded in SOTA primary sources · CEL (cel.dev) · jq ·
RFC 9562 UUIDv7 · OpenAPI single-field envelope · Go/Kubernetes durations ·
AWS exponential-backoff-and-jitter.

### Changed

- **One data language · jq.** Output bindings (`output:`) and `fetch`
  extraction use **jq** — the same jq as the `nika:jq` builtin. RFC 9535
  JSONPath is dropped (jq is a strict superset), so an author — or an LLM —
  never has to choose between two extraction syntaxes. Nika now has exactly
  **two expression layers**: **CEL** (inside `${{ }}` · conditions +
  substitution) and **jq** (extraction + transform).
- **Stdlib consolidated · 42 → 26 builtins** (zero capability loss). jq
  subsumes ~13 thin data wrappers (map · filter · group_by · aggregate ·
  enrich · chunk · flatten · unflatten · json_to_csv · base64 ×2 ·
  **json_merge** = jq's recursive `*`). `task_status` removed (read
  `tasks.X.status` directly). The two JSON validators merge into one
  `nika:validate` (`format: json | yaml`).
- **`nika:json_merge` CUT · 27 → 26** (the verification-gated builtin · resolved
  2026-05-27). It was kept on the claim *"jaq lacks reliable recursive `*`"* —
  **source-verified false**: jaq's `jaq-json/src/lib.rs` has a dedicated
  `obj_merge` for `Obj * Obj`, its test corpus asserts
  `{"k":{"a":1,"b":2}} * {k:{a:0,c:3}}` → `{"k":{"a":0,"b":2,"c":3}}` (recursive),
  and `docs/corelang.dj` states *"Multiplying two objects merges them
  recursively."* So `json_merge` is exactly `jq '.[0] * .[1]'` on a `[base,
  overlay]` input → a jq-wrapper → cut by the same 42→27 principle that cut
  map/filter/etc. `json_merge_patch` (RFC 7396 · null-deletes) **stays** —
  delete-on-null is NOT `*` semantics, genuinely not jq-expressible.
- **DAG coherence · 3 fixes (03-dag + 05-errors).** (D1) `for_each` introduces
  `${{ item }}` / `${{ index }}` but the namespace model claimed "5 namespaces" ·
  now documented as **for_each-local CEL variables** (the 5 are global · item/index
  are loop-scoped). (D5) `size()` was used in canonical `when:` examples but was
  NOT in the v0.1 CEL subset nor explicitly reserved · now **the one v0.1 function**
  (collection/string length · the empty-check idiom) · string-manipulation functions
  stay reserved. (D4) the error sub-namespace is **generalized** · `NIKA-<NS>-<SUB>-<NNN>`
  valid per-builtin (`NIKA-BUILTIN-WAIT-001`) AND per-field (`NIKA-PARSE-WHEN-001`) ·
  was prose-restricted to builtin while the pattern + usage were already general.
- **Envelope coherence · 2 prose↔schema drifts (01-envelope + schema).** (E1)
  the `vars`/`outputs` typed-form `type:` prose listed 5 (`string·number·boolean·
  array·object`) but the schema enum has 6 (incl `integer`) · prose now lists
  `integer`. (E4) `secrets.source` prose said "vault **(default)**" but the schema
  made `source` **required** (contradiction) · schema now makes `source` optional
  defaulting to `vault` (the sovereign default · `secrets: { k: { key: path } }`
  works without spelling `source: vault`).
- **Schema · expression-leaf `format` tags + JSONPath→jq alignment.** The
  hand-derived `schemas/workflow.schema.json` now tags its expression leaves ·
  `when:` (task + `on_finally`) carries `"format": "cel-expression"` · `output:`
  binding values carry `"format": "jq"`. These are LSP hooks (annotation-only ·
  validators ignore unknown formats · zero structural break) for future
  CEL-namespace / jq-path completion. Same change corrects the `output:`
  description, which still read « RFC 9535 JSONPath bindings » — the schema was
  lagging the already-decided prose (one data language · jq) · now aligned to
  spec/04-variables.md §216-225. The closed builtins-enum (LSP autocomplete of
  the 27) is deliberately deferred to the engine-generated `nika-schema`
  (schemars) output — a flat grep of `stdlib/builtins-v0.1.md` returns 41 names
  (27 canonical + 14 documented-as-cut), proving the enum needs structured
  codegen, not a drift-prone hand-edit.
- **Output model hardened · 5 coherence fixes (04-variables).** Audit of the
  output/binding surface against CEL + jq semantics + SOTA workflow engines
  (GitHub Actions · Argo · Temporal · n8n · Dagger) · all read the task result
  as an OBJECT, never a bare value. (1) `tasks.X` is the **result record** ·
  the bare-alias « `tasks.X` == `.output` » is removed (it made `tasks.X` both
  a scalar AND a record-with-`.status` · which CEL cannot type) · the output is
  always `${{ tasks.X.output }}`. (2) A binding resolves to **exactly one jq
  value** · a stream (`.users[]`) is a parse-time error · collect with `[ … ]`
  (`[.users[].email]`) · the canonical example was a stream-producing bug · now
  fixed. (3) **Object→string** substitution renders as compact deterministic
  JSON (sorted keys) · controlled via jq `@json`/`tostring` in `output:` (no
  pipe-filters). (4) `output:` jq is **pure jq over the raw output** · no
  `${{ }}` nesting (the 2 expression layers never mix in one string) · jq-var
  parametrization is a v0.2 candidate. (5) `.started_at`/`.ended_at` exposed
  (were reserved-but-hidden) · the dual-access example fixed (used the reserved
  `status` binding name + JSONPath `$.` syntax · now `http_status` + jq).
- **`output_format` task field REMOVED** (drafted in pre-public hardening ·
  removed before any adopter · net-never-shipped). It duplicated the per-verb
  output mechanisms (`exec.capture` · `infer`/`agent` `schema:` · the
  `nika:validate` builtin) AND its default table had drifted out of sync with
  02-verbs (claimed `exec:`/`agent:` default to `structured` · while 02-verbs
  says **stdout string** / **final-message string**) — a literal second source
  of truth contradicting the first. Output **shape is per-verb · one source**
  (the `.output` table in 02-verbs). Binary output is **tool-determined**
  (MCP image content · binary read) · opaque · flows tool→tool · file-mediated
  for `fetch`/`exec` — no task-level type enum (the source + sink tools each
  already declare their own type · the middle hint was redundant).
- **`on_error` simplified · 4 modes → 3.** `fallback:` + `value:` merge into
  one `recover:` field (a `${{ }}` ref resolves to either a task output or a
  literal) · plus `skip:` and `fail_workflow:`.
- **`depends_on` is the success-gate.** A redundant `when: status == 'success'`
  is discouraged — `when:` is for conditions *beyond* the default gate. A
  `when:` / `with:` reference to `tasks.<id>` **MUST** declare `<id>` in
  `depends_on:` (parse-time error otherwise · no invisible edges).
- **Envelope → `nika: v1`** · one field (was `apiVersion` + `schema`) ·
  follows the OpenAPI `openapi: 3.1.0` pattern (document type discriminated by
  the `workflow:` key).
- **The 4 verbs are absolute** · `infer` · `exec` · `invoke` · `agent`. The
  count is locked at 4 forever — `fetch` is a TOOL (`invoke: nika:fetch`), not
  a verb. A 5th verb would require `nika: v2` (never).
- **Expression language = CEL** · everything inside `${{ }}` (substitutions +
  `when:` predicates) is a documented subset of CEL · validated ·
  non-Turing-complete · portable.
- **`when:` is a CEL boolean** · the engine rejects non-boolean expressions at
  parse time · no truthy coercion (explicit comparison required).
- **Task `id` = snake_case** (`^[a-z][a-z0-9_]*$`) · ids appear in CEL paths
  where a hyphen is the minus operator. The `workflow:` name stays kebab-case.
- **`infer:` and `agent:` message fields unified** · both take `system:` +
  `prompt:`.
- **Tool reference grammar** · `<namespace>:<path>` with a `/` hierarchy
  (`nika:write` · `nika:connectome/recall` · `mcp:browser/navigate` · globs
  `mcp:browser/*`).
- **Agent tools default-deny** · `agent.tools:` absent → no tools (least
  privilege · pure conversation).
- **Cross-cutting fields are task-level** · `timeout` and `retry` live on the
  task, not inside a verb block.
- **One duration format** · Go / Kubernetes-style strings (`"5s"` · `"1h30m"`)
  for task `timeout`, `nika:sleep`, everywhere — quoted (YAML numeric-trap
  defense). Replaces the prior numeric `_ms` fields.
- **Model selection · one field** · `model: <provider>/<name>` (the provider is
  the prefix · `anthropic/claude-sonnet-4-6` · `openai/gpt-4o`). Removes the
  silent-nonsense trap of a separate `provider:` field. Local-vs-cloud **is the
  prefix** · `ollama/…` · `lmstudio/…` = local (no key) · the cloud providers
  use `${{ secrets.* }}`. **13 providers** (5 local · `ollama` · `lmstudio` ·
  `llamacpp` · `localai` · `vllm` · plus the `openai` + `OPENAI_BASE_URL` escape
  hatch for any other OpenAI-compatible backend). Provider config stays out of
  the workflow — a workflow only *selects*.
- **`secrets source:` is a closed enum** · `vault` (default · sovereign) ·
  `env` (an OS env var · still masked) · `file` (mounted secret).
- **`exec.env` vs envelope `env:` disambiguated** · envelope `env:` = workflow
  config (`${{ env.* }}`) · `exec.env` = the subprocess OS environment (not
  auto-connected · pass values explicitly).

### Added

- **`outputs:` envelope block** · the workflow declares **what it returns** —
  the symmetric twin of `vars:`. Untyped (a bare `${{ tasks.X.output }}` ref)
  or typed (`{ value, type, description }`). Typed `vars:` + typed `outputs:` =
  the complete callable contract (typed in · typed out).
- **`agent:` gains `schema:`** · an agent may declare a JSON Schema to validate
  its **final message** as structured output (same contract as `infer.schema:`).
- **`for_each:` concurrency control** · `max_parallel:` (cap concurrent
  iterations · default unbounded · `max_parallel: 1` forces sequential) +
  `fail_fast:` (abort-on-error policy · default true). `for_each` is **parallel
  by default** — unlike Python's sequential `for`.
- **`on_finally:` task field** · cleanup-hook mini-tasks that **always** run
  after the parent task completes (success / fail / timeout / cancel) ·
  sequential · best-effort (errors logged, not propagated). cf Argo `onExit` ·
  Temporal `defer` · GitHub Actions `if: always()`.
- **5 stdlib builtins** · `nika:notify` (one builtin · `channel:` enum
  webhook / slack / email / discord / sms) · `nika:uuid` (v7 default ·
  timestamped · sortable · RFC 9562) · `nika:date` (op-discriminated ·
  TZ-aware · ISO 8601) · `nika:hash` (blake3 default · sha256 / sha512 ·
  md5 / sha1 excluded as broken for crypto) · `nika:wait_until` (absolute
  timestamp · sister to `nika:sleep`).
- **`for_each:`** · bounded map / fan-out over a static list or a prior task's
  array output (`${{ item }}` · `${{ index }}`).
- **`${{ secrets.X }}`** · 5th variable namespace · vault-backed · masked in
  logs · the modern `env` ⊥ `secrets` security split.
- **Typed `vars`** · optional `{ type, required, default, description }` form
  (input validation + schema generation) · the simple `name: value` form is
  preserved.
- **`nika:done`** · agent-loop completion sentinel · error if invoked outside
  an `agent:` loop.
- **YAML conventions section** (in `01-envelope`) · one rule covers the classic
  generated-config footguns (the Norway problem `no` → boolean · leading-zero
  octal · sexagesimal `12:30` · version floats `1.10` → `1.1`) · quote anything
  that could be misread.
- **YAML multi-line guidance** · `|` (literal · preserves newlines) is canonical
  for prompts / system / command fields · `>` / `>-` (folded) **forbidden** in
  prompts (collapsing newlines corrupts LLM intent).
- **Canonical JSON Schema** · `schemas/nika-workflow.schema.json` is the
  machine-readable companion (envelope + task + verb shapes) for editor
  autocomplete + inline validation — the same DX as GitHub Actions / Docker
  Compose. The prose spec stays normative.
- **Retry `jitter`** · default on · full-jitter / equal-jitter family (AWS
  exponential-backoff-and-jitter) · anti-thundering-herd.
- **Conformance levels clarified** · Core is a static-check mode (`when:` /
  `for_each:` references resolve to known namespaces but are not evaluated) ·
  runtime evaluation is Level 2.

### Forward-compat — documented, not applied

Long-horizon v0.2 candidates (each needs an explicit re-lock + spec amendment) ·
sessions / threads (multi-turn context · LangGraph-style checkpoints) · workflow
composition (`include:` · sub-workflow execution · Argo-style) · cost-tracking
output fields (`tasks.X.cost` / `tokens` / `provider`) · multi-agent handoffs ·
cost-aware model routing (per-task cheap-vs-expensive switching).

> Still towards v0.1.0 GA · examples + conformance fixtures + JSON schemas
> pending.

---

## [0.1.0-draft] — 2026-05-22

### Added

- Initial spec repo · Apache-2.0 (patent grant for implementers).
- `spec/` · 9 sections · envelope · 4 verbs · DAG · variables · errors · stdlib
  contract · conformance · out-of-scope.
- `stdlib/` · curated v0.1 lists (13 providers · 9 extract modes · builtins ·
  media builtins deferred to a later stdlib release).
- `examples/` · placeholder (26 canonical workflows pending).
- `conformance/` · placeholder (test suite for the « v0.1-compliant » claim).
- `schemas/` · placeholder (JSON Schemas for `yaml-language-server`).

### Decisions

- **5 pillars immutable forever** · envelope · 4 verbs · DAG · variables ·
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
