# NEP-0017 · The thin-laws (lot 3b): the pricing table in the pin · the end obligation · the third blame polarity · the named solo endorsement

- **NEP**: 0017 (next free integer · 0001 reserved for the v1 surface · 0002 the trifecta gate · 0003 absent permits · 0004 the parameterization taint · 0005 the environment permit · 0006 the data-as-code sink · 0007 the trace and the equivalence oracle · 0008 the egress projection · 0009 the effective path identity · 0010 the run declaration · 0011 the run lifecycle · 0012 the receipt as untrusted input · 0013 the approval ticket · 0014 the thin-laws lot 3a · 0015 preview-commit · 0016 the provenance tiers)
- **Title**: Four more small laws — the versioned pricing table rides the semantic pin, a failed run owes an attested quarantine, a normalization default is blamed on the contract that declares it, and a one-endorser action names its mode
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-29

## Abstract

The second batch of laws too small for their own NEPs and too real to
stay ambient — the continuation NEP-0014's Reference Implementation
announced. (1) The versioned pricing table that gives a cost its
meaning is part of the run's semantic pin. (2) A failed run owes an
attested quarantine of its half-written outputs. (3) A default inserted
by normalization that violates downstream is blamed on the contract
that declares it — a third blame polarity, « by the contract ».
(4) An endorsement of exactly one endorser is a named mode with a fresh
bound human authorization — never an implicit escape.

## Motivation

A cost verdict is only meaningful against the pricing table that
produced it: replay a run in 2031 against 2031 prices and the budget
law speaks nonsense — the table must ride the pin or the replay is a
different run. A failed run leaves half-written outputs that today
re-enter the next run's inputs silently: the teardown attestation
(NEP-0011) proves the end *happened*; nothing yet says what the end
*owes*. A normalization default that violates a downstream rule is
blamed on the caller who never wrote it: the blame vocabulary has
« by the value » and « by the caller » and lacks the truthful third.
And an endorsement gate that admits exactly one human is the approval
surface at its most fatigue-prone: the mode must be named, bound, and
logged — or it is a queue with one slot.

## Specification

### Law 1 · The pricing table in the pin (F-P18)

The versioned pricing table the cost bound (ρ) is computed against is
part of the run's semantic pin. A replay reads cost against the PINNED
table — a run whose pin lacks the table, or names a table version the
engine does not know, refuses the cost-meaning replay (the replay of
effects is untouched; it is the *budget verdict* that requires the
table). A replay against the pinned table yields the identical budget
verdict.

### Law 2 · The end obligation (F-P14)

A run that fails after producing partially-written outputs owes an
**attested quarantine**: the teardown seal (NEP-0011) names the
half-written artifacts and marks them quarantined — a quarantined
artifact re-entering as the input of a later run is a finding. The
distributed saga (compensation actions across services) is declared P2
and out of v1: v1 owes the *naming and the containment*, not the
undoing.

### Law 3 · The third blame polarity (F-P22)

A default value inserted by normalization (the canon's declared
defaults) that participates in a downstream violation is imputed to
the contract that DECLARES the default — « by the contract » — naming
the declaring rule; neither « by the value » nor « by the caller »
may absorb it. The receipt and the check diagnostic speak the polarity.

### Law 4 · The named solo endorsement (F-P23)

An endorsement surface admitting exactly one endorser is lawful only
as the NAMED mode `endorsement: solo`: one endorser, a fresh human
authorization BOUND to the action (the NEP-0013 ticket chain), logged
as solo. One endorser without the declared mode is a refusal — F-F5
applies with zero implicit escape: a quorum of one is a decision,
never a default.

## Rationale

- **Meaning rides the pin.** A digest of the plan without the table
  that prices it is half an identity — the pin binds what the verdict
  was computed AGAINST, not only what was computed.
- **The end owes, not just happens.** NEP-0011 attested the teardown;
  this law gives the teardown its first debt. Quarantine over undo:
  the honest v1 debt is that the mess is named, contained, and never
  silently re-consumed.
- **Blame the declarer.** A mis-attributed default teaches the wrong
  repair: the caller is told to fix a value they never wrote. The
  third polarity makes the receipt teach the truth.
- **A mode named over a mode slipped into.** The solo case is the
  dangerous case (NEP-0013's fatigue class); naming it binds it to the
  ticket chain instead of letting it pass as the absence of a quorum.

## Backwards Compatibility

Law 1 refuses only cost-meaning replays of runs pinned before the
table existed — they replay their effects and lose the budget verdict,
stated plainly. Law 2 adds findings where half-written outputs were
silently re-consumed (always a bug). Law 3 changes diagnostics, never
verdicts. Law 4 refuses the undeclared solo surface — no green
workflow carried one (the endorsement surface ships with this law).

## Reference Implementation

- The engine lane (`feat/lot3b-thin-laws`): the pricing-table pin and
  its replay gate · the quarantine section of the teardown seal and
  the re-entry finding · the blame polarity in the check diagnostic and
  the receipt · the `endorsement: solo` mode with its bound ticket —
  each with its fixture pair.

## Copyright

This document is placed in the public domain under CC0-1.0, as every NEP.
