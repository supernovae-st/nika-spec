# Nika spec · CHANGELOG

All notable changes to the **Nika workflow language specification** are
documented here. The spec follows `apiVersion: nika.sh/v1` forever (per
ADR-044) · only the schema version (`schema: nika/workflow@v1`) may
receive additive minor bumps.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- (Working towards v0.1.0 GA · spec sections drafted · examples + conformance
  pending recopy from brouillon · JSON schemas pending generation from prose
  spec.)

---

## [0.1.0-draft] — 2026-05-22

### Added
- Initial scaffold of the spec repo (Apache-2.0 license · patent grant
  included for implementers).
- `spec/` · 9 markdown sections covering envelope · 5 verbs · DAG · variables ·
  errors · stdlib contract · conformance · out-of-scope.
- `stdlib/` · curated v0.1 inclusions (9 providers · 9 extract modes · 61
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
