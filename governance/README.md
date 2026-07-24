# governance/ · how the Nika standard evolves

Every evolution of the standard is a **NEP** (Nika Enhancement Proposal):
a numbered, public, git-versioned document. Nobody amends the standard
directly, the maintainers included.

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
| [0010](nep-0010-run-entropy-clock.md) | Every source of randomness and time is declared at the envelope's `run:` block | Standards Track | Draft |
| [0011](nep-0011-run-lifecycle-attestation.md) | The run's lifecycle is attested: boot manifest, teardown seal, verifier-borne incomplete | Standards Track | Draft |
| [0012](nep-0012-receipt-untrusted-input.md) | The receipt is untrusted input: bounds as constants, terminal hygiene, recognize-don't-sanitize, the differential twin | Standards Track | Draft |

Numbering runs through this door from NEP-0000 onward — pre-1.0 drafts
included (NEP-0002 is the living proof). The pre-1.0 RULINGS and the ADR
line are the founding era: their verbatim record stays canonical history,
not retroactive NEPs. NEP-0001, "the nika: v1 language surface", is the
one reserved retroactive entry, minted at the 1.0 freeze.
