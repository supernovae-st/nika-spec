# NEP-0000 · The NEP Process

- **NEP**: 0000
- **Title**: The NEP Process
- **Author**: SuperNovae Studio maintainers
- **Status**: Active (process NEP · never Final)
- **Type**: Process
- **Created**: 2026-07-18

## Abstract

A NEP (Nika Enhancement Proposal) is the public, numbered document through
which every evolution of the Nika standard is proposed, discussed and
decided. Nobody amends the standard directly, the maintainers included.
This document defines the process itself: the lifecycle, the template, who
decides, and how the process evolves.

The lineage is deliberate: [PEP 1](https://peps.python.org/pep-0001/)
governs Python this way, the
[KEP process](https://github.com/kubernetes/enhancements/blob/master/keps/sig-architecture/0000-kep-process/README.md)
governs Kubernetes (itself taken from Rust's RFCs, themselves shaped by
PEPs), and the [TC39 stages](https://tc39.es/process-document/) govern
JavaScript. A standard earns trust when its evolution has one public door.

## Motivation

Three effects, proven by the processes above:

1. **Credible neutrality.** A third-party vendor proposes an evolution
   through the same door the maintainers use. That is the condition for
   rival runtimes to adopt the spec at all.
2. **Fork resistance.** Fragmentation, relicensing, capture and dialects
   share one antidote: a public evolution process nobody can confiscate.
3. **A navigable freeze.** Post-1.0 the surface is frozen, additive only.
   Without a proposal process, frozen means dead. With one, frozen means
   stable and governed: the NEP is the vehicle of every legal addition.

## Specification

### Lifecycle

```
Draft → Discussion → Accepted | Rejected → Implemented → Final
```

- **Draft**: a PR adding `governance/nep-NNNN-<slug>.md` from the template.
  The number is the next free integer, claimed by the PR itself.
- **Discussion**: public, in the PR and its linked issue. There is no
  private track.
- **Accepted / Rejected**: decided per the Decision authority below.
  A rejected NEP stays published with its rationale. The record of noes
  is worth as much as the record of yeses: it prevents relitigating.
- **Implemented**: the reference engine ships it behind a green
  conformance suite, and the spec text is amended by the NEP's cascade.
- **Final**: the amendment is part of the frozen surface. Process NEPs
  (like this one) stay **Active** instead: they may be amended by a
  successor NEP.

### Types

- **Standards Track**: changes the language surface, the stdlib contract,
  the conformance suite or the trace format.
- **Process**: changes how Nika evolves (this document is one).
- **Informational**: records a design position without changing anything.

### Decision authority

Today: the SuperNovae Studio maintainers, by explicit written acceptance
in the NEP's PR. Tomorrow: when three to five independent vendors ship
conformant runtimes, authority transfers to a technical committee they
seat together. That transfer is itself a Process NEP, proposed through
this same door.

### Numbering and the founding era

NEP numbering runs through this door from NEP-0000 onward — a pre-1.0
Draft claims its number the same way (NEP-0002 is the living proof).
The pre-1.0 rulings are the founding era: their verbatim record (the
RULINGS documents and the ADR line) remains canonical history, not
retroactive NEPs. One retroactive exception is reserved: NEP-0001,
"the nika: v1 language surface", a Standards Track summary of the
constitution as frozen at 1.0, so the language has one readable front
door.

### Relationship to conformance

An accepted Standards Track NEP is not Implemented until the conformance
suite proves it. The public claim « Nika v1 Conformant — <Level>
(spec <commit>) » (the one claim string ·
[spec/07 §Claiming conformance](../spec/07-conformance.md#claiming-conformance))
is earned by passing the suite, never by declaration. A NEP that cannot
state its conformance test does not leave Discussion.

The ratchet is same-PR: an Accepted Standards Track NEP lands its
conformance fixtures in the implementing PR — the spec text amendment,
the registered error codes, and the fixtures that prove them arrive
together, never separately. A registered error code without a fixture
is a spec bug. (The precedent: MCP made a conformance scenario a
Final-gate for every SEP — SEP-2484; this door holds the same bar.)

### What a NEP is not

- Not a bug report: defects in the engine go to the engine tracker.
- Not documentation: docs follow the spec, they do not amend it.
- Not a fork of authority: a NEP the maintainers (today) or the committee
  (tomorrow) rejected does not become a dialect. Divergent runtimes lose
  the compatibility claim per the conformance rule.

## How to propose

1. Copy `governance/nep-template.md` to `governance/nep-NNNN-<slug>.md`
   (next free number).
2. Fill every section. "Rejected alternatives" and "Compatibility impact"
   are mandatory: an empty alternatives section means the design was not
   explored.
3. Open the PR. Discussion happens there. Silence is not consent: a NEP
   advances only by explicit acceptance.

## Rejected alternatives

- **GitHub issues as the process**: issues have no lifecycle, no template
  discipline, and vanish from the reading order. A numbered file in git
  is citable forever.
- **RFC-style mailing list**: the studio is small and the audience is
  developer-first. The PR is where the diff and the debate share a page.
- **Waiting until vendors exist to define the process**: the process must
  predate its first external user, or the first external proposal arrives
  with no door to knock on. Foundations land before the peak.

## Compatibility impact

None. This NEP is additive: it creates `governance/` and binds nothing
retroactively. The pre-1.0 gate (rulings, migrations, conformance work)
proceeds unchanged.
