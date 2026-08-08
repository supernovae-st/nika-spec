# governance/ · how the Nika standard evolves

Every evolution of the standard is a **NEP** (Nika Enhancement Proposal):
a numbered, public, git-versioned document.

> **Pre-ratification clause (until 1.0).** The language is not ratified
> yet: the spec on `main` is the DRAFT, and the draft evolves directly.
> Until `1.0.0` ratifies, the documents below are **design records of
> the draft** — they carry the reasoning the draft folds in, and their
> numbers are already load-bearing (engine code and traces cite
> `NEP-0012`, `NEP-0019`, …). At 1.0 the process becomes **binding**:
> from ratification on, nobody amends the standard directly, the
> maintainers included — every change walks through this door.

- Start here: [NEP-0000 · The NEP Process](nep-0000-the-nep-process.md)
- Propose: copy [nep-template.md](nep-template.md) to
  `nep-NNNN-<slug>.md` (next free number) and open a PR.

## Index

| NEP | Title | Type | Status |
|---|---|---|---|
| [0000](nep-0000-the-nep-process.md) | The NEP Process | Process | Active |
| [0002](nep-0002-lethal-trifecta-human-gate.md) | Lethal-trifecta human gate | Standards Track | Draft |
| [0003](nep-0003-absent-permits-zero-authority.md) | Absent permits: means zero authority (fail-closed) | Standards Track | Draft |
| [0004](nep-0004-permit-parameterization-taint.md) | Permit-parameterization taint: untrusted values re-gate under permits | Standards Track | Draft |
| [0005](nep-0005-env-permit-dimension.md) | The environment permit: a child's environment is composed, never inherited | Standards Track | Draft |
| [0006](nep-0006-data-as-code-sink.md) | The data-as-code sink: a fetch of a code-bearing artifact is never innocent | Standards Track | Draft |
| [0007](nep-0007-trace-format-and-equivalence.md) | The trace leaves the private dialect: a normative journal, a required witness, a differential oracle | Standards Track | Draft |
| [0008](nep-0008-egress-permit-bound.md) | The sandboxed egress proxy is the permit's exact projection | Standards Track | Draft |
| [0009](nep-0009-effective-path-identity.md) | A path grant names an effective path identity, re-judged at dispatch | Standards Track | Draft |
| [0013](nep-0013-approval-ticket.md) | Human approval is a bounded, content-bound, attested ticket | Standards Track | Draft |
| [0014](nep-0014-thin-laws.md) | The thin-laws (lot 3a): observable independence · input origins · the readable receipt · cross-version resume | Standards Track | Draft |
| [0015](nep-0015-preview-commit.md) | Preview-commit: the effect request is hashed at judgment and recomputed at the sink | Standards Track | Draft |
| [0016](nep-0016-provenance-tiers.md) | Provenance tiers: a closed ladder admitted by evidence, an operator-owned floor, the tier attested | Standards Track | Draft |
| [0017](nep-0017-thin-laws-3b.md) | The thin-laws (lot 3b): the pricing pin · the end obligation · the third blame · the named solo | Standards Track | Draft |
| [0018](nep-0018-energy-honesty.md) | Energy honesty: floors, ceilings, UNBOUNDED, and never a fabricated zero — the cost doctrine in watt-hours | Standards Track | Draft |
| [0010](nep-0010-run-entropy-clock.md) | Every source of randomness and time is declared at the envelope's `run:` block | Standards Track | Draft |
| [0011](nep-0011-run-lifecycle-attestation.md) | The run's lifecycle is attested: boot manifest, teardown seal, verifier-borne incomplete | Standards Track | Draft |
| [0012](nep-0012-receipt-untrusted-input.md) | The receipt is untrusted input: bounds as constants, terminal hygiene, recognize-don't-sanitize, the differential twin | Standards Track | Draft |
| [0021](nep-0021-delegation-block.md) | The `delegation:` block — bounded, attenuated, attested sub-runs under `agent:` | Standards Track | Draft |

Numbering runs through this door from NEP-0000 onward — pre-1.0 drafts
included (NEP-0002 is the living proof). The pre-1.0 RULINGS and the ADR
line are the founding era: their verbatim record stays canonical history,
not retroactive NEPs. NEP-0001, "the nika: v1 language surface", is the
one reserved retroactive entry, minted at the 1.0 freeze.
