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
| **OpenSSF Best Practices** (passing · 67 criteria) | project hygiene, end to end | 🟡 self-assessment below · [.bestpractices.json](../.bestpractices.json) shipped · entry creation = maintainer gesture (GitHub login on bestpractices.dev) | this file §self-assessment |
| **OpenSSF Scorecard** (20 checks) | supply-chain posture, continuously measured | 🟢 workflow shipped ([scorecard.yml](../.github/workflows/scorecard.yml)) · badge lands after the first published run | §scorecard below |
| **REUSE 3.3** | machine-readable licensing, file-complete | ✅ `reuse lint` GREEN (the run is the live count) · [REUSE.toml](../REUSE.toml) blanket + overrides · CI job live ([reuse.yml](../.github/workflows/reuse.yml)) | repo root |
| **SLSA v1.2 Build** | release provenance | ⏳ engine release train · `actions/attest-build-provenance` = Build L2 on hosted runners · reusable-workflow isolation = L3 | engine-lane brief |
| **Sigstore / cosign** | release signatures | ⏳ engine release train · keyless `cosign sign-blob --bundle <tarball>.sigstore.json` per release asset (id-token: write) | engine-lane brief |
| **SBOM** | dependency transparency | ⏳ engine release train (cargo-auditable / cargo-cyclonedx) · N/A for this repo (no built artifacts) | engine-lane brief |
| **IANA media type** | `application/vnd.nika+yaml` | ⏳ post-1.0 gesture · vendor tree · RFC 6838 §5.6 template · submit at iana.org/form/media-types | [01 §File naming](../spec/01-envelope.md#file-naming-normative) |
| **SchemaStore** | editor validation everywhere | ✅ live (« Nika workflow » · `*.nika.yaml` + `*.nika.yml` matchers) | schemastore catalog |
| **GitHub Linguist** | language recognition | ⛔ honestly gated · needs ~2000 in-the-wild files/year (forks excluded) · not claimable today | adoption trigger |
| **tree-sitter grammar** | native editor grammars (Zed · Neovim) | ⏳ demand-gated · self-servable (publish grammar + nvim-treesitter `lua/parsers.lua` PR · quality bar, no usage threshold) | editor-demand trigger |
| **BCP 14** | normative language | ✅ [07 §Notation](../spec/07-conformance.md#notation) | — |
| **SemVer · Keep-a-Changelog · NEP process** | versioning + evolution discipline | ✅ VERSION · CHANGELOG.md · [governance/](./nep-0000-the-nep-process.md) | — |
| **CITATION.cff · Code of Conduct** | citability + community posture | ✅ [CITATION.cff](../CITATION.cff) (cffconvert-valid) · [Contributor Covenant 2.1](../CODE_OF_CONDUCT.md) (CC-BY-4.0 declared in REUSE) | repo root |

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
- **Closed by this hardening wave (2026-07-19)** ·
  1. `vulnerability_report_private` — GitHub private vulnerability reporting
     is **enabled** on the repo and cited in [SECURITY.md](../SECURITY.md)
     (GitHub Security Advisories = the preferred private channel).
  2. `static_analysis` — **ruff** lints the Python tooling on every push/PR
     ([conformance.yml](../.github/workflows/conformance.yml) · config
     [ruff.toml](../ruff.toml)) and **CodeQL**
     ([codeql.yml](../.github/workflows/codeql.yml)) adds security SAST;
     the conformance oracle already statically analyzes every artifact this
     repo ships.
  3. `.bestpractices.json` — the repo-side machine self-assessment file
     ([.bestpractices.json](../.bestpractices.json)) is **shipped** (the
     badge app imports it once the entry exists).
- **N/A block** · all 9 `crypto_*` (no crypto shipped) · `build*` (no
  build step — markdown + Python scripts run in place) ·
  `dynamic_analysis_unsafe` (no memory-unsafe language) ·
  `release_notes_vulns` (no CVEs to date).

Verdict: **passing is clearable now** — every code-closable criterion is
Met or N/A ([.bestpractices.json](../.bestpractices.json)); the one step
left is the maintainer creating the bestpractices.dev entry (branch
protection is a Scorecard/silver concern, not a passing criterion).

## Scorecard — expected first-run posture

Strong out of the gate: Token-Permissions (top-level least privilege in
all workflows) · Dangerous-Workflow (zero risky triggers · no event data
in shells) · Pinned-Dependencies (actions SHA-pinned as of this wave ·
pip HASH-pinned (--require-hashes · .github/requirements.txt · uv pip compile)) · SAST (CodeQL ·
[codeql.yml](../.github/workflows/codeql.yml)) · Dependency-Update-Tool
(Dependabot · [dependabot.yml](../.github/dependabot.yml)) · CI-Tests ·
License · Security-Policy · Maintained.

Known deductions, tracked honestly:

| Check | Why | Move |
|---|---|---|
| Branch-Protection | not yet enabled on `main` | maintainer gesture (require PR + `static gate` status check) · time it **after** the pre-1.0 gate's direct-push ceremonies, or enable with admin bypass — a hard require-PR rule would break the sister-lane ceremony pushes |
| Code-Review | small-maintainer reality — self-merged PRs | NEP discussions mitigate · improves with contributors |
| Signed-Releases / Packaging / SBOM / Fuzzing | no released artifacts from this repo | N/A-class for a spec repo (the engine train carries them) |
| CII-Best-Practices | badge not yet registered | §Best Practices above |

Badge (after first published run) ·
`[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/supernovae-st/nika-spec/badge)](https://scorecard.dev/viewer/?uri=github.com/supernovae-st/nika-spec)`

## Maintainer gestures (queued · settings-side · not automatable from here)

1. **bestpractices.dev** — log in with GitHub · create the entry for
   `supernovae-st/nika-spec` · the [.bestpractices.json](../.bestpractices.json)
   shipped this wave pre-fills the answers.
2. **Branch protection on `main`** — require PRs + the `static gate ·
   core + stdlib surface + examples` check (Scorecard's Branch-Protection
   + Code-Review both read it). Time this **after** the pre-1.0 gate's
   direct-push ceremonies, or enable it with admin bypass — a hard
   require-PR rule would break the sister-lane ceremony pushes.

Done this wave · **private vulnerability reporting** is enabled (repo
Settings → Security) and cited in [SECURITY.md](../SECURITY.md).

## Related

- [07-conformance §Claiming](../spec/07-conformance.md#claiming-conformance) — the claim we grant
- [NEP-0000](./nep-0000-the-nep-process.md) — how the standard evolves
- [SECURITY.md](../SECURITY.md) · [CONTRIBUTING.md](../CONTRIBUTING.md) · [REUSE.toml](../REUSE.toml)
