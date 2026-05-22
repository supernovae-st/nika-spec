# Nika spec · CHANGELOG

All notable changes to the **Nika workflow language specification** are
documented here. The spec is pinned at the `nika: v1` contract forever ·
language additions are additive within v1 (feature-detected · no minor
version in the file).

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added — SOTA completeness (pass 3 · D-2026-05-22-N12)

Socratic « do we have ALL the industry standards » audit · 13-concern SOTA
checklist · 2 genuine gaps closed.

- **YAML 1.2 mandated + quoting conventions** · a Nika file is YAML 1.2 (a JSON
  superset). New « YAML conventions · no traps » section in 01-envelope fixes
  the classic generated-config footguns: the Norway problem (`no` → boolean),
  leading-zero octal (`0755`), sexagesimal colons (`12:30`), version floats
  (`1.10` → `1.1`). One rule: quote anything that could be misread as a
  number/boolean/date · quote expressions containing `: # [ { , >`. This is the
  « no traps when an AI writes it » guarantee.
- **Canonical JSON Schema established** · `schemas/nika-workflow.schema.json` is
  the machine-readable companion (envelope + task + verb shapes), consumed by
  editors (`yaml.schemas` / `$schema` modeline) for autocomplete + inline
  validation — the same DX as GitHub Actions / Docker Compose. Specified in
  07-conformance (the schema file is generated/maintained alongside the prose,
  which stays normative).
- **Retry jitter precision** · « ±50% » softened to the standard full-jitter /
  equal-jitter family (AWS « exponential backoff and jitter ») rather than
  over-specifying a formula.

### Changed — language logic hardening (pass 2 · D-2026-05-22-N11)

Second SOTA pass · scrutinized every detail against validated conventions +
idiomatic-Rust mapping · nuked everything weird/inconsistent/unvalidated.
Grounded: perplexity (CEL = de-facto standard for declarative conditions ·
K8s ValidatingAdmissionPolicy + Kyverno 1.17 · default-deny least-privilege
standard · RFC 9535 JSONPath standardized).

- **Expression language = CEL** (was a hand-rolled « custom minimal DSL »).
  Everything inside `${{ }}` — substitution and `when:`/predicates — is a
  documented subset of **CEL** (Common Expression Language · cel.dev). Common,
  comprehensible, validated, safe (non-Turing-complete), portable (zero parser
  drift). Engines may embed `cel-interpreter` or hand-roll the small subset.
- **Task `id` = snake_case** (`^[a-z][a-z0-9_]*$`, was kebab+snake mixed). Task
  ids appear in CEL paths (`tasks.fetch_page.output`) — a hyphen is CEL's minus
  operator, so kebab ids were a silent trap. `workflow:` stays kebab (never in
  expressions).
- **Message fields unified** · `infer:` and `agent:` both use `system:` +
  `prompt:` (was `infer.prompt` vs `agent.user` — inconsistent).
- **Tool reference grammar** · `<namespace>:<path>` with `/` hierarchy ·
  `nika:write` · `nika:connectome/recall` · `mcp:browser/navigate` (was the
  inconsistent `mcp:server::tool` `::` + `nika:connectome.recall` `.`). One
  colon for the namespace, slash for the path. Globs `mcp:browser/*`.
- **Agent tools = default-deny** · `agent.tools:` absent → NO tools (pure
  conversation · least-privilege), was « all engine tools allowed » (a hole).
- **Cross-cutting fields task-level only** · `timeout_ms` + `retry` live on the
  task, removed from inside `exec:`/`fetch:` (was duplicated · ambiguous).
- **Output binding pinned to RFC 9535** JSONPath (was « a subset »). Engines use
  `serde_json_path` or any RFC 9535 impl.
- **Retry `jitter`** · added (default true · ±50% full-jitter · anti-thundering-
  herd). Fixed the bad `on_codes` example (used a non-existent namespace + an
  HTTP status as a code).
- **Builtin count = 36** (Core 6 + File 5 + Data 19 + Introspection 6) ·
  canonical · nuked the « 61 » (verbs doc) and « core 7 » (conformance) drifts.

### Changed — language consolidation (pre-public final · D-2026-05-22-N10)

Grounded in SOTA primary sources (Docker Compose versionless · OpenAPI
single-field · Kestra minimal · env⊥secrets separation now standard). Done
while pre-public (zero adopters) — free to perfect the pillars to their
immutable-forever form.

- **Envelope → `nika: v1`** · one field replaces `apiVersion: nika.sh/v1` +
  `schema: nika/workflow@v1` (OpenAPI `openapi: 3.1.0` pattern · drops K8s
  ceremony + the two-version-field redundancy). Doc-type discriminated by the
  resource key (`workflow:`). Engine canonical URI `https://nika.sh/spec/v1`
  internal-only.
- **5 verbs · absolute** · the count is locked at 5 forever · the operation
  space is complete · a 6th verb would require `nika: v2` (effectively never).

### Added
- **`for_each:`** task field · bounded map/fan-out over a static list or a
  prior task's array output (`${{ item }}` · `${{ index }}`) · the iteration
  construct a workflow language must have.
- **`${{ secrets.X }}`** · 5th variable namespace · vault-backed · masked in
  logs · the modern `env`⊥`secrets` security split.
- **Typed `vars`** · optional `{ type, required, default, description }` form ·
  enables `nika.run_workflow` MCP schema-gen + UI-gen + input validation ·
  simple `name: value` untyped form preserved.
- **`nika:done`** · locked agent-loop-only (completion sentinel · error if
  invoked outside an `agent:` loop).
- **Core conformance** · clarified as static-check mode · `when:` / `for_each:`
  references resolve to known namespaces but are NOT evaluated (runtime eval is
  Level 2).
- (Still towards v0.1.0 GA · examples + conformance fixtures pending recopy ·
  JSON schemas pending generation from prose spec.)

---

## [0.1.0-draft] — 2026-05-22

### Added
- Initial scaffold of the spec repo (Apache-2.0 license · patent grant
  included for implementers).
- `spec/` · 9 markdown sections covering envelope · 5 verbs · DAG · variables ·
  errors · stdlib contract · conformance · out-of-scope.
- `stdlib/` · curated v0.1 inclusions (8 providers · 9 extract modes · 36
  builtins · 24 media builtins deferred to stdlib v0.x).
- `examples/` placeholder (26 canonical workflows to be recopied clean from
  the brouillon exploration era).
- `conformance/` placeholder (test suite for « v0.1-compliant » claim).
- `schemas/` placeholder (machine-readable JSON Schemas for
  yaml-language-server consumption).

### Locked decisions (cross-ref `dx/state/decisions.yaml`)
- D-2026-05-22-N1 · 5 pillars immutable forever (envelope · 5 verbs · DAG ·
  variables · errors).
- D-2026-05-22-N2 · License split · Apache-2.0 spec + AGPL-3.0-or-later engine.
- D-2026-05-22-N3 · GitHub topology · 7 public repos + monorepo orchestrator.
- D-2026-05-22-N4 · Diamond CRAFT sharpenings · `nika-syntax` L0 NEW · break
  engine→lsp-core · break media→mcp · ~25 crate target.
- D-2026-05-22-N5 · Stdlib v0.1 inclusion list.
- D-2026-05-22-N6 · v0.1 ship plan · 3 weeks (Phase A spec public) + 7 weeks
  (Phase B engine vertical slice).
- D-2026-05-22-N7 · `supernovae-st/nika-spec` NEW Apache-2.0 public repo (creation pending
  Thibaut go-ahead).

---

## Why no « 0.0.x »

This spec exists from the start as v0.1.0-draft because the brouillon
exploration era (`supernovae-st/nika` brouillon branch) already shipped
`nika/workflow@0.12` in 26 canonical examples. The v0.1 spec **derives
from empirical examples** · not invented from scratch.

The first GA release (`0.1.0`) will be cut when ·
1. All 9 spec sections finalized + reviewed (pantheon · architect lenses)
2. 26 examples recopied clean (zero brouillon references in spec corpus)
3. Conformance tests `conformance/tests/` published
4. JSON schemas in `schemas/` consumable by `yaml-language-server`

After GA · the 5 pillars are immutable forever. Stdlib evolves
independently via its own versioning (`stdlib/providers-v0.x.md` etc.).
