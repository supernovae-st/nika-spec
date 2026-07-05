# Nika spec · CHANGELOG

All notable changes to the **Nika workflow language specification** are
documented here. The spec is pinned at the `nika: v1` contract forever ·
language additions are additive within v1 (feature-detected · no minor
version in the file). Stdlib (providers · extract modes · builtins) versions
independently.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added · `nika:image_generate` — the 24th builtin · first §Media graduate (2026-07-05)

- **`nika:image_generate`** joins the canonical stdlib (23 → 24 · the first
  graduate of the deferred media class) · provider-backed image asset
  generation as an *asset pipeline*: images are **saved under a declared
  `output_dir:`** (rides `permits.fs` · `NIKA-SEC-004` gated per final path
  before any I/O) and outputs/manifest carry **paths + dimensions + sha256 —
  image bytes never ride workflow outputs**. Providers v0.1 · `openai`
  (`gpt-image-2`) · `gemini` (`gemini-3.1-flash-image`) · `mock`
  (deterministic · offline · zero keys). Normative surface in
  [stdlib/builtins-v0.1.md §Media](stdlib/builtins-v0.1.md): closed arg
  enums · size-vs-aspect_ratio resolution rule (exact size wins, loudly) ·
  magic-bytes-are-the-authority decode validation (header-only · no pixel
  decode) · the `{stem}-{provider}-{modelslug}-{index}-{sha8}.{ext}`
  filename grammar (sanitized · traversal-free) · provenance manifest
  (`manifest_version: 1`) · stable `code: message` warnings · error codes
  `NIKA-BUILTIN-IMAGE_GENERATE-001..007`. The v0.1 boundaries are refused
  loudly, never silently: `mode: edit` · `reference_images:` ·
  `save: false` are RESERVED (media roadmap). Cascade · canon.yaml
  builtins 24 · workflow.schema.json tool enum · conformance fixtures
  `stdlib/builtins/004` (reserved `mode: edit` rejected) + `005` (valid
  mock generation) · showcase `t1-og-images` (the OG-image pipeline ·
  offline-runnable). Reference engine ships it as `nika-builtin`'s Media
  module family behind the dispatcher's image plane.

### Added · ADR-099 · durable-lite run resume (2026-07-05)

- **`adr/` opens in this repo** with
  [ADR-099](adr/adr-099-durable-lite-run-resume.md) · « durable-lite run
  resume — the trace IS the checkpoint » (**accepted** · implemented by
  engine supernovae-st/nika#154). `nika run --resume <trace>` re-executes a workflow
  skipping every task whose (task-definition hash + resolved-input hash)
  matches a `task.completed` record in the run's own NDJSON trace · each
  skip is a **visible** `task.cache_hit` event (never silent) · `--from
  <task_id>` forces re-run from a node. Rider · the durable human gate: a
  non-interactive default-less `nika:prompt` journals `workflow.paused` +
  exits cleanly · `--resume` re-arms it (H5's live-pause limitation
  resolved · zero new syntax). Non-goals locked in the ADR · no
  author-facing determinism constraints (side-effectful tasks re-run
  unless hash-matched) · idempotency keys stay the NEXT deferral · zero
  envelope change (CLI + trace/event vocabulary only · `paused` joins the
  run-report workflow states additively) · no daemon.
- **08-out-of-scope amended in step** · §checkpointing carries the
  durable-lite lift note (the `checkpoint:`-block sketch REMAINS
  deferred) · H1 marks the tier lifted-by-ADR and un-couples it from
  idempotency keys · H5 points durable pause at ADR-099's `--resume` ·
  §idempotency cross-links the interplay.
- ADR numbering continues the shared Nika series (engine `docs/adr/`
  keeps the registry · ADR-098 taken in-flight engine-side) ·
  registered in the engine index with the implementation (64 ADRs valid).

### Fixed · sitemap examples bound a phantom `.urls` wrapper (2026-07-05)

- **`nika:fetch` `mode: sitemap` returns the ROOT ARRAY**
  `[{loc, changefreq, priority}, …]` · but t2-seo-content-brief sliced
  `.urls[:5]`, t3-competitor-radar `.urls[:8]`, and the 03-dag fan-out
  snippet taught `pages: ".urls[]"` (phantom wrapper AND a stream binding
  where a binding is single-valued). Every user copying the examples hit
  `NIKA-VAR-004` at the first sitemap task (F5 field report 2026-07-04).
  Fixed to `.[:5] | map(.loc)` / `.[:8] | map(.loc)` / `map(.loc)` ·
  `examples/manifest.yaml` sha256_16 regenerated. This repo is the SSOT
  the engine vendors (`sync-pack.sh`) · mirrors engine `a8c2acaa4`.

### Added · launch inputs + provider transport deadline (2026-07-05)

- **`nika run --var key=value` documented** (repeatable · overrides a
  declared `default:` · satisfies `required: true` · JSON-when-it-parses
  else string · unknown key refused pre-run) at the contract home
  (01-envelope §vars) · cross-linked from 04-variables `vars.X`,
  QUICKSTART §3 and the templates README `NIKA-VAR-001` repair row. The
  7 required-var example `# Run` lines now carry the `--var` they need.
- **§Transport deadline** (stdlib/providers-v0.1.md) · the task
  `timeout:` governs the provider HTTP deadline · per-class defaults
  when unset (local ≥300s · cloud 30s) · 600s ceiling on a fully-silent
  connection · streaming rides only an explicit budget (the idle-read
  guard reaps stalls). One cross-link from 03-dag §timeout · no
  duplicated prose.

### Added · `nika:compose` · the agent's self-check builtin (2026-06-13)

- **`nika:compose` · the 23rd canonical builtin** (Introspection · stdlib
  v0.1 builtins 22 → 23). The agent loop's self-verification intrinsic: the
  model passes a `workflow_yaml` draft it wrote and gets the full `nika check`
  verdict back as the tool result (conformance + secret-flow + permits + the
  termination/cost certificate) — it **never executes** the draft
  («generation is not permission»). Loop-only like `nika:done` (valid only
  inside an `agent:` whitelist · standalone is `NIKA-BUILTIN-COMPOSE-001`).
  Documented in `stdlib/builtins-v0.1.md` + `02-verbs.md` §agent · added to
  the closed enum in `workflow.schema.json`.
- **The tool-namespace closure is now enforced for agent whitelists.** The
  namespace set was already CLOSED at `{nika:, mcp:}` for `invoke:`; the
  `agent: tools:` whitelist now rejects a third namespace at parse too (an
  engine that previously let a non-`nika:`/`mcp:` glob through was
  spec-lax). This is what keeps `nika:compose` in the closed `nika:` set
  rather than inventing an `agent:` namespace.

### Added · the parse tier enters the registry (2026-06-12)

- **`NIKA-PARSE-001..019` allocated** (18 codes · 016 retired) — the
  structural/envelope failure class a beginner meets FIRST was emitted by
  the reference checker but absent from the normative floor: a second
  engine could not match parse-time behavior from the spec alone, and
  `nika explain` had no row to teach. The registry now carries every
  statically-emitted code: envelope (001-005) · task shape (006-012) ·
  bindings/secrets/vars (013-015) · mapping/field/structural (017-019).
- **`NIKA-PARSE-016` retirement documented** — folded into `NIKA-VAR-005`
  at the deep-conformance registry remap; the allocation hole is
  deliberate per the additive-never-repurposed rule.
- **`NIKA-BUILTIN-001` allocated** — builtin `invoke:` arg-contract
  violations (e.g. `nika:fetch` without `url:`) were emitted by the
  checker but only the `nika:done` special case (`BUILTIN-DONE-001`) had
  a row. The generic code joins the floor.
- `error_codes` count 30 → 49 · canon + prose table + errors catalog +
  docs tables re-projected in parity.

### Added · rounds 5-10 cohort (2026-06-11 · the night-loop continuation)

- **Behavioral conformance tier (contract-first)** — `tests/runtime/`
  carries the execution-half contract BEFORE the engine: fixture shape
  (`input.nika.yaml` + `run.json` + `expected-run.json` · named so the
  static gate ignores them by construction), run-report assertion schema,
  determinism rules, five areas, eleven fixtures — every input statically
  valid today. Writing them locked a position: `tool:` is schema-static
  (no expressions), so the static permits check is COMPLETE for the tools
  category; the one runtime-only escape is a dynamic fetch host.
- **`permits:` hardening pass** — PERMITS-FIT static check (the declared
  boundary must contain the body · `NIKA-SEC-004` · deep tier) + two
  flagship declarations (resume-screener: the sovereignty story — no net
  category, PII cannot leave; human-gated-ship template: argv programs +
  webhook host pinned).
- **Run-sim gate field** — the DAG model emits `gate: default | when |
  always` per task so consumers implement gate-based failure propagation
  honestly (the website break-it beat is the first consumer).
- **Registry growth** — `NIKA-VAR-009` (typed outputs validation · the
  parity ratchet's first real catch) + `NIKA-SEC-004` (permits boundary) ·
  registry at 30 codes · canon gains a count self-check (len(items) ==
  count == the counts-block mirror · both projector modes).
- **Eval routing arm** — `--condition routing/all`: the model picks the
  template family from the routing table (scored against ground truth) and
  authors without the template body.

### Fixed · rounds 5-10 cohort (2026-06-11)

- **resume-screener taught a hallucination** — the prompt asked the model
  to quote evidence from a CV it never received (only the path). Fixed
  with the read-zip-screen shape (glob → read fan-out with null recovery →
  transpose → screen over `{path, text}`).
- Header truth pass (14 files) — `on_finally` claims scoped to
  started-tasks-only, resilient fan-outs credit `recover: null`,
  release-radar names its `on_codes` scoping, run lines added to the six
  root examples missing the convention.
- Deep fixture 002 migrated `has()` → `matches()` (the CEL expansion
  legalized `has` · `matches` stays the reserved unknown-function case).
- QUICKSTART step 5 + header join the one-voice posture (check today via
  the oracle · execution at the engine milestone).
- Generated docs tables are MDX-escaped at emission (a bare brace in a
  table cell parsed as a JSX expression and killed the docs build).

### Added · divergence audit + projection ring (2026-06-11)

- **Gate-based failure propagation** — unrecovered failure no longer reads as
  a blanket kill: in-flight tasks drain, a task with an explicit `when:`
  still evaluates over terminal deps (the **always-pattern** — `when: true`
  cleanup/notify works in a failing workflow), user-cancel stays a blanket
  kill (05 §workflow-level semantics).
- **`on_error.on_codes`** — catch-side code routing (mirror of
  `retry.on_codes`); `on_error.skip` now preserves the original error at
  `tasks.X.error` (downstream per-code routing).
- **Defined-null reads** — a skipped/cancelled task's `.output` (and
  bindings) read as `null`, never an error — the diamond-join idiom is
  canonical (04 §defined-null).
- **`for_each` closed semantics** — `timeout:`/`output:` bindings apply per
  iteration; failed iterations contribute `null` placeholders at their index
  (zip alignment survives partial failure); non-array collections are
  `NIKA-VAR-006`.
- **Concrete error registry** — 28 allocated codes (the normative floor a
  second engine matches from the spec alone) + 2 additive categories
  (`process_error` · `budget_error`); machine-readable in `canon.yaml`
  (`error_codes:` · `error_categories:`); sub-namespace regex admits
  underscore builtins (`NIKA-BUILTIN-JSON_MERGE_PATCH-001`).
- **Agent-loop termination contract** — budget exhaustion is `failure`
  (`NIKA-AGENT-001/002` · partial preserved in `error.details`); tool errors
  feed back to the model EXCEPT `security_error`; `nika:done result:` arg
  defined.
- **`when:` boolean literals** — `when: true`/`false` (YAML booleans) are
  legal; bare non-`${{ }}` strings are rejected; static shape rejection is
  `NIKA-VAR-005`, eval type errors `NIKA-VAR-006` (the orphan
  `NIKA-PARSE-WHEN-001` is gone).
- **YAML profile** — anchors/aliases normative-yes; `<<:` merge keys
  rejected (YAML 1.2 dropped them).
- **Three horizon postures** — H17 caching/memoization · H18 matrix (the
  jq-product idiom) · H19 value-conditioned polling (the jq-error+retry
  pattern).
- **`NIKA-DAG-004`** — `on_error.recover` referencing a task downstream of
  the declaring task is a parse error (the recovery await would deadlock).
- Oracle: bare-`when:`, `${{ }}`-in-bindings, `nika:write` content,
  standalone `nika:done`, envelope `model:` all static now; 11 new fixtures.
- Projector v5: the served `schema/workflow.json` + `errors/catalog.json`
  (v3 · generated from the canon registry) are projection TARGETS with a
  prose↔canon parity check — the drift class is structurally closed.

### Fixed · divergence audit (2026-06-11)

- `exec` `capture: structured` makes a non-zero exit **data** (`exit_code`),
  not failure; default capture modes fail with `NIKA-EXEC-001`.
- The spec's own examples tested `status == 'failed'` — the enum is
  `failure`; corrected everywhere.
- `${{ workflow_run_id }}` ghost identifier removed from the `on_finally`
  example (it resolved against no namespace).
- `secrets:` schema is source-discriminated (`vault`/`env` require `key:` ·
  `file` requires `path:`); `mcp:` tool references require the slash; server
  names admit kebab-case.
- 06 §namespace-ownership claimed an `x-<vendor>:` third namespace while 02
  closes the set at `nika:`/`mcp:` — resolved: engine-specific tools route
  through `mcp:` (the engine hosts its own server); `x-` is reserved as a
  possible future additive minor, non-existent in v0.1.
- 07 documents the `deep/` fixture tier; `NIKA-DAG-004` + `NIKA-VAR-005`
  added to the Core conformance contract.

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
- **Stdlib consolidated · 42 → 22 builtins** (zero capability loss · 2026-05-27 cumulative · pre-ADR-086/087/088 stage was 26 · post is 22). jq
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
- **Introspection builtins evaluated · `dag_info`/`threads` KEPT, `threads`
  gets a portability caveat.** A "verifier d'autre candidat" sweep flagged these
  2 as the most speculative (zero usage · engine-self-introspection). Verdict ·
  KEEP — the stdlib cut criterion is **redundancy** (jq-subsumes), not rarity;
  both are **unique** (nothing else provides DAG topology / engine state) so
  neither falls under the 42→26 principle. `nika:threads` gains an **advisory**
  note (its counts reflect the engine's concurrency model · impl-dependent ·
  coarse adaptive-throttling · not a portable contract-precise number).
  > ⚠️ **§2.7 amendment 2026-05-27 evening · ADR-088 unified** · same-day after
  > the KEPT verdict above, the next Rams sweep applied the « one super-powerful
  > builtin · multi-mode args » pattern to the 4 introspection builtins
  > (`cost` + `records` + `dag_info` + `threads`) and collapsed them into
  > `nika:inspect view: <which>` view-discriminated · single registration · zero
  > capability loss. The KEEP-vs-NUKE decision above stays correct (those
  > capabilities are unique and stay shipped) · the EXPOSURE-SURFACE changed
  > (4 builtin names → 1 with view enum). Same § 42→22 principle as ADR-086/087.
- **ADR-086 · `csv_to_json` → `convert` universal multi-format.** Same Rams
  pattern · ONE super-powerful builtin (`nika:convert format: <X> direction:
  encode|decode`) subsumes csv↔json + yaml↔json + toml↔json + base64↔text ·
  zero capability loss · -1 builtin (was 26 · now 25 after this).
- **ADR-087 · `sleep` + `wait_until` → `wait` unified.** Same Rams pattern ·
  ONE super-powerful builtin (`nika:wait duration: "5s" | until: <ISO 8601>`) ·
  -1 builtin (now 24).
- **ADR-088 · 4 introspection → `inspect` view-discriminated.** Same Rams
  pattern · `nika:inspect view: cost|records|dag_info|threads` · -3 builtins
  (now **22 · final**).
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
  use `${{ secrets.* }}`. **14 providers** (8 cloud incl. `openrouter` —
  promoted to a first-class provider per D-2026-06-10-N2 · 5 local · `ollama` ·
  `lmstudio` · `llamacpp` · `localai` · `vllm` · 1 test `mock`). Any other
  OpenAI-compatible backend rides the `openai` + base-URL escape hatch.
  Provider config stays out of the workflow — a workflow only *selects*.
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
- **Canonical JSON Schema** · `schemas/workflow.schema.json` is the
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
