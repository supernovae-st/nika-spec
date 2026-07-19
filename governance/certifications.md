# Certifications & external-standards posture

> How the Nika standard holds itself to the same bar it asks of engines.
> « Nika v1 Conformant » is the badge WE grant (earned by the suite ·
> [07 §Claiming](../spec/07-conformance.md#claiming-conformance)); the
> programs below are the badges we EARN from the ecosystem's own
> verifiers. Primary-source research receipt: 2026-07-19 (live fetches ·
> bestpractices.dev · securityscorecards.dev · reuse.software · slsa.dev ·
> docs.github.com). SPDX-License-Identifier: Apache-2.0

## The matrix

| Program | What it proves | Status | Evidence / next |
|---|---|---|---|
| **OpenSSF Best Practices** (passing · 67 criteria) | project hygiene, end to end | 🟡 self-assessment below · entry creation = maintainer gesture (GitHub login on bestpractices.dev) | this file §self-assessment |
| **OpenSSF Scorecard** (20 checks) | supply-chain posture, continuously measured | 🟢 workflow shipped ([scorecard.yml](../.github/workflows/scorecard.yml)) · badge lands after the first published run | §scorecard below |
| **REUSE 3.3** | machine-readable licensing, file-complete | ✅ `reuse lint` GREEN (1034/1034) · [REUSE.toml](../REUSE.toml) blanket + overrides · CI job live ([reuse.yml](../.github/workflows/reuse.yml)) | repo root |
| **SLSA v1.2 Build** | release provenance | ⏳ engine release train · `actions/attest-build-provenance` = Build L2 on hosted runners · reusable-workflow isolation = L3 | engine-lane brief |
| **Sigstore / cosign** | release signatures | ⏳ engine release train · keyless `cosign sign-blob --bundle <tarball>.sigstore.json` per release asset (id-token: write) | engine-lane brief |
| **SBOM** | dependency transparency | ⏳ engine release train (cargo-auditable / cargo-cyclonedx) · N/A for this repo (no built artifacts) | engine-lane brief |
| **IANA media type** | `application/vnd.nika+yaml` | ⏳ post-1.0 gesture · vendor tree · RFC 6838 §5.6 template · submit at iana.org/form/media-types | [01 §File naming](../spec/01-envelope.md#file-naming-normative) |
| **SchemaStore** | editor validation everywhere | ✅ live (« Nika workflow » · `*.nika.yaml` + `*.nika.yml` matchers) | schemastore catalog |
| **GitHub Linguist** | language recognition | ⛔ honestly gated · needs ~2000 in-the-wild files/year (forks excluded) · not claimable today | adoption trigger |
| **tree-sitter grammar** | native editor grammars (Zed · Neovim) | ⏳ demand-gated · self-servable (publish grammar + nvim-treesitter `lua/parsers.lua` PR · quality bar, no usage threshold) | editor-demand trigger |
| **BCP 14** | normative language | ✅ [07 §Notation](../spec/07-conformance.md#notation) | — |
| **SemVer · Keep-a-Changelog · NEP process** | versioning + evolution discipline | ✅ VERSION · CHANGELOG.md · [governance/](./nep-0000-the-nep-process.md) | — |

## OpenSSF Best Practices — passing self-assessment (2026-07-19)

Against the 67 passing criteria (live list, criteria/0):

- **Met by existing structure** · description/interact/license trio
  (README · Apache-2.0 OSI · LICENSE at root) · docs pair (README + spec/)
  · sites_https · discussion (issues/PRs) · english · maintained ·
  repo_public/track/interim/distributed · version_unique/semver/tags
  (VERSION + tags) · release_notes (CHANGELOG.md) · report_process/
  tracker/archive (GitHub issues) · vulnerability_report_process
  (SECURITY.md) · test + test_invocation + test_continuous_integration
  (conformance suite + selftests + conformance.yml) · delivery_mitm
  (https everywhere) · no_leaked_credentials (registry-grade R5 hygiene) ·
  know_secure_design / know_common_errors (maintainers) ·
  vulnerabilities_fixed_60_days (none open).
- **Closed by this wave** · contribution + contribution_requirements +
  test_policy + tests_are_added → [CONTRIBUTING.md](../CONTRIBUTING.md)
  (the corpus-case-with-every-normative-change rule IS the test policy).
- **Open gaps (tracked)** ·
  1. `vulnerability_report_private` — enable GitHub private vulnerability
     reporting (repo Settings · maintainer gesture) and cite it in
     SECURITY.md.
  2. `static_analysis` — justification path: the conformance oracle
     statically analyzes every artifact this repo ships; the Python
     tooling itself gets a linter (ruff) as a follow-up.
  3. `.bestpractices.json` — the repo-side machine self-assessment file
     (the badge app imports it) · follow-up once the entry exists.
- **N/A block** · all 9 `crypto_*` (no crypto shipped) · `build*` (no
  build step — markdown + Python scripts run in place) ·
  `dynamic_analysis_unsafe` (no memory-unsafe language) ·
  `release_notes_vulns` (no CVEs to date).

Verdict: **passing is clearable now**; the entry creation + the two
settings gestures are maintainer-side.

## Scorecard — expected first-run posture

Strong out of the gate: Token-Permissions (top-level least privilege in
all workflows) · Dangerous-Workflow (zero risky triggers · no event data
in shells) · Pinned-Dependencies (actions SHA-pinned as of this wave ·
pip version-pinned) · CI-Tests · License · Security-Policy · Maintained.

Known deductions, tracked honestly:

| Check | Why | Move |
|---|---|---|
| Branch-Protection | not yet enabled on `main` | maintainer gesture (require PR + `static gate` status check) |
| Code-Review | small-maintainer reality — self-merged PRs | NEP discussions mitigate · improves with contributors |
| SAST | no CodeQL job | candidate follow-up (Python scripts only) |
| Signed-Releases / Packaging / SBOM / Fuzzing | no released artifacts from this repo | N/A-class for a spec repo (the engine train carries them) |
| CII-Best-Practices | badge not yet registered | §Best Practices above |

Badge (after first published run) ·
`[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/supernovae-st/nika-spec/badge)](https://scorecard.dev/viewer/?uri=github.com/supernovae-st/nika-spec)`

## Maintainer gestures (queued · settings-side · not automatable from here)

1. **bestpractices.dev** — log in with GitHub · create the entry for
   `supernovae-st/nika-spec` · walk the §self-assessment above.
2. **Branch protection on `main`** — require PRs + the `static gate ·
   core + stdlib surface + examples` check (Scorecard's Branch-Protection
   + Code-Review both read it).
3. **Private vulnerability reporting** — repo Settings → Security →
   enable · then cite in SECURITY.md.

## Related

- [07-conformance §Claiming](../spec/07-conformance.md#claiming-conformance) — the claim we grant
- [NEP-0000](./nep-0000-the-nep-process.md) — how the standard evolves
- [SECURITY.md](../SECURITY.md) · [CONTRIBUTING.md](../CONTRIBUTING.md) · [REUSE.toml](../REUSE.toml)
