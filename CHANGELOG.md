# Nika spec · CHANGELOG

All notable changes to the **Nika workflow language specification** are
documented here. The spec is pinned at the `nika: v1` contract forever ·
language additions are additive within v1 (feature-detected · no minor
version in the file). Stdlib (providers · extract modes · builtins) versions
independently.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Changed — model selection · one field (pass 4 · D-2026-05-22-N13)

Socratic « is `provider:` + `model:` as two fields a good idea? » audit ·
research-validated against LiteLLM · OpenRouter · Vercel AI SDK · PydanticAI
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
  `native` GGUF runtime, which stays deferred per D-N8). `model: ollama/llama3.1`
  makes a zero-cloud run trivial.
- **Provider config stays OUT of the workflow** · `base_url` + auth in
  engine/provider config · a workflow only *selects*. Combine with typed `vars`
  (D-N10) to parameterize the model and run one workflow against any backend.

Pre-public hardening of the v0.1 draft (no adopters yet · free to perfect the
pillars to their immutable-forever form). Grounded in SOTA primary sources ·
CEL (cel.dev) · RFC 9535 JSONPath · OpenAPI single-field envelope · Docker
Compose versionless · AWS exponential-backoff-and-jitter.

### Changed

- **Envelope → `nika: v1`** · one field (was two · `apiVersion` + `schema`).
  Follows the OpenAPI `openapi: 3.1.0` pattern · the document type is
  discriminated by the resource key (`workflow:`).
- **The 5 verbs are absolute** · the count is locked at 5 forever · the
  operation space is complete · a 6th verb would require `nika: v2` (never).
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
- `spec/` · 9 sections · envelope · 5 verbs · DAG · variables · errors · stdlib
  contract · conformance · out-of-scope.
- `stdlib/` · curated v0.1 lists (9 providers · 9 extract modes · 36 builtins ·
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
