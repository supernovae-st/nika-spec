# governance/ · how the Nika standard evolves

Every evolution of the standard is a **NEP** (Nika Enhancement Proposal):
a numbered, public, git-versioned document.

> **The process is dormant until the v1 pre-freeze.** A proposal process
> only has meaning against something FROZEN. Before the freeze there is
> nothing to propose *against*: a new law is written **directly** into
> [`spec/`](../spec/), and the deep breaks live inside `v1` itself. At the
> pre-freeze this door becomes binding — from then on every change is a
> proposal again, the maintainers included.
>
> That is why the drafts that used to sit here are gone: on 2026-08-14 the
> twenty of them stopped being proposals and became the language. The
> table below says where each law lives now.

- The process itself: [NEP-0000 · The NEP Process](nep-0000-the-nep-process.md)
- The shape a future proposal takes: [nep-template.md](nep-template.md)

## The fold · 2026-08-14 · where each law lives now

The numbers stay load-bearing: engine code, traces and commit messages
cite `NEP-0009`, `NEP-0012`, … . **This table is what those citations
resolve to.** A number is never reused.

| NEP | The law | Lives now in |
|---|---|---|
| 0002 | Lethal-trifecta detection with a Rule-of-Two human gate | [`spec/05-errors.md`](../spec/05-errors.md) · `NIKA-SEC-009` |
| 0003 | An absent `permits:` block declares zero authority | [`spec/01-envelope.md`](../spec/01-envelope.md) §`permits` · `NIKA-AUTH-006` |
| 0004 | Untrusted values re-gate on their canonical resolved form | [`spec/10-authority.md`](../spec/10-authority.md) §the permit-parameterization taint · `NIKA-AUTH-007/008` |
| 0005 | A child's environment is composed, never inherited | [`spec/01-envelope.md`](../spec/01-envelope.md) §the environment category |
| 0006 | A fetch of a code-bearing artifact is never innocent | [`spec/10-authority.md`](../spec/10-authority.md) §the data-as-code sink · `NIKA-SEC-008` |
| 0007 | The journal is a normative chapter · every permit decision is witnessed | [`spec/17-trace.md`](../spec/17-trace.md) (the whole chapter) |
| 0008 | The sandboxed egress proxy is the permit's exact projection | [`spec/01-envelope.md`](../spec/01-envelope.md) §the sandboxed egress proxy |
| 0009 | A path grant names an effective path identity, re-judged at dispatch | [`spec/01-envelope.md`](../spec/01-envelope.md) §a path grant names an effective path identity |
| 0010 | Every source of randomness and time is declared | [`spec/01-envelope.md`](../spec/01-envelope.md) §`run` |
| 0013 | Human approval is a bounded, content-bound, attested ticket | [`spec/10-authority.md`](../spec/10-authority.md) §the approval is a bounded ticket · `NIKA-SEC-010` |
| 0015 | Preview-commit: judged = executed, at the action scale | [`spec/05-errors.md`](../spec/05-errors.md) · `NIKA-SEC-011` |
| 0020 | A refused confirm must not reach an effect | [`spec/10-authority.md`](../spec/10-authority.md) §the affirmative-consent law · `NIKA-SEC-014` |

## Still folding

These carry law the spec does not yet hold in full. Each descends into
`spec/` before its file goes — deleting first would lose normative text
nothing else carries.

| NEP | Title | Type | Status |
|---|---|---|---|
| [0011](nep-0011-run-lifecycle-attestation.md) | The run's lifecycle is attested: boot manifest, teardown seal, verifier-borne incomplete | Standards Track | Draft |
| [0012](nep-0012-receipt-untrusted-input.md) | The receipt is untrusted input: bounds as constants, terminal hygiene, recognize-don't-sanitize | Standards Track | Draft |
| [0014](nep-0014-thin-laws.md) | The thin-laws (lot 3a): observable independence · input origins · the readable receipt · cross-version resume | Standards Track | Draft |
| [0016](nep-0016-provenance-tiers.md) | Provenance tiers: a closed ladder admitted by evidence, an operator-owned floor, the tier attested | Standards Track | Draft |
| [0017](nep-0017-thin-laws-3b.md) | The thin-laws (lot 3b): the pricing pin · the end obligation · the third blame · the named solo | Standards Track | Draft |
| [0018](nep-0018-energy-honesty.md) | Energy honesty: floors, ceilings, UNBOUNDED, and never a fabricated zero | Standards Track | Draft |
| [0019](nep-0019-workflow-token-budget.md) | The workflow token budget — the portable cap leaves the agent verb | Standards Track | Draft |
| [0021](nep-0021-delegation-block.md) | The `delegation:` block — bounded, attenuated, attested sub-runs under `agent:` | Standards Track | Draft |

## Numbering

Numbers run through this door from NEP-0000 onward, folded documents
included — a folded number is spent, never recycled. The pre-1.0 RULINGS
and the ADR line are the founding era: their verbatim record stays
canonical history, not retroactive NEPs. NEP-0001, "the `nika: v1`
language surface", is the one reserved retroactive entry, minted at the
1.0 freeze.
