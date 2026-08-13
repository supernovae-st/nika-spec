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
> That is why the drafts that used to sit here are gone: on 2026-08-13 the
> twenty of them stopped being proposals. Eighteen became the language;
> two were never built and are buried as such. The tables below say where
> each one went — a number that resolves to nothing does so on purpose.

- The process itself: [NEP-0000 · The NEP Process](nep-0000-the-nep-process.md)
- The shape a future proposal takes: [nep-template.md](nep-template.md)

## The fold · 2026-08-13 · where each law lives now

The numbers stay load-bearing: engine code, traces and commit messages
cite `NEP-0009`, `NEP-0012`, … . **This table is what those citations
resolve to.** A number is never reused.

*(The date above is when the fold was **done**, read off the clock. The
decision that authorised it is `D-2026-08-14-N1` and keeps its own id —
an identifier is not a timestamp, and reading one as the other is how
this heading was wrong for a day.)*

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
| 0011 | The run's lifecycle is attested: boot manifest, teardown seal, verifier-borne `incomplete` | [`spec/17-trace.md`](../spec/17-trace.md) §the prologue · §the end of the run |
| 0012 | The receipt is untrusted input: bounds as constants, recognize-don't-sanitize | [`spec/15-proof.md`](../spec/15-proof.md) §the verifier is a fortress |
| 0013 | Human approval is a bounded, content-bound, attested ticket | [`spec/10-authority.md`](../spec/10-authority.md) §the approval is a bounded ticket · `NIKA-SEC-010` |
| 0014 | The thin-laws (3a): observable independence · input origins · the readable receipt · cross-version resume | [`spec/05-errors.md`](../spec/05-errors.md) `NIKA-SEC-012` · [`04`](../spec/04-variables.md) §origin · [`15`](../spec/15-proof.md) §receipt · [`17`](../spec/17-trace.md) §fold law |
| 0015 | Preview-commit: judged = executed, at the action scale | [`spec/05-errors.md`](../spec/05-errors.md) · `NIKA-SEC-011` |
| 0016 | Provenance tiers: a closed ladder admitted by evidence, an operator-owned floor, the tier attested | [`registry/registry-v0.1.md`](../registry/registry-v0.1.md) §3b · `NIKA-REG-008` |
| 0017 | The thin-laws (3b): the pricing table rides the pin · a failed run owes an attested quarantine · the third blame polarity | [`15`](../spec/15-proof.md) §the semantic hash · [`17`](../spec/17-trace.md) §the end of the run · [`05`](../spec/05-errors.md) §blame polarity |
| 0018 | Energy honesty: unknown stays unknown, and never a fabricated zero | [`spec/07-conformance.md`](../spec/07-conformance.md) §the spend-honesty law |
| 0020 | A refused confirm must not reach an effect | [`spec/10-authority.md`](../spec/10-authority.md) §the affirmative-consent law · `NIKA-SEC-014` |

### Retired · the law died rather than moved

A number here resolves to nothing in `spec/` **on purpose**. Reading it
as « folded somewhere I have not found yet » sends the next reader
hunting a law that does not exist.

| NEP | What died | Why |
|---|---|---|
| 0017 law 4 | the named solo endorsement (`endorsement: solo`) | the `policy:` block left the envelope on 2026-08-12, and `NIKA-POLICY-001` + `NIKA-SEC-013` are **retired** with it ([`spec/05-errors.md`](../spec/05-errors.md) §retired · [`canon/tombstones.yaml`](../canon/tombstones.yaml)). The law's other three fold above; this one had no carrier left |
| 0019 | the workflow-level token budget | a SKETCH, never built: no engine carries it, and the `policy:` surface it proposed to hang from left the envelope on 2026-08-12 ([`spec/10-authority.md`](../spec/10-authority.md) §the unconditional laws). The verb-level `agent.max_tokens_total` it wanted to generalize is untouched ([`spec/02-verbs.md`](../spec/02-verbs.md)). Text at `509472c` |
| 0021 | the `delegation:` block and its three builtins | a SKETCH, never built: `nika:delegate` · `nika:take` · `nika:scratch` exist in no engine and no stdlib. Writing it into the spec would promise a surface nothing implements. Text at `509472c`, and on the branch `nep/0021-delegation-block` |

## Numbering

Numbers run through this door from NEP-0000 onward, folded documents
included — a folded number is spent, never recycled. The pre-1.0 RULINGS
and the ADR line are the founding era: their verbatim record stays
canonical history, not retroactive NEPs. NEP-0001, "the `nika: v1`
language surface", is the one reserved retroactive entry, minted at the
1.0 freeze.
