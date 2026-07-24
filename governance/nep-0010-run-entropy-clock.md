# NEP-0010 · The run declares its entropy and its clock

- **NEP**: 0010 (next free integer · 0001 reserved for the v1 surface · 0002 the trifecta gate · 0003 absent permits · 0004 the parameterization taint · 0005 the environment permit · 0006 the data-as-code sink · 0007 the trace and the equivalence oracle · 0008 the egress projection · 0009 the effective path identity)
- **Title**: Every source of randomness and time is declared at the envelope's `run:` block — entropy and clock are contract inputs, never ambient facts
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-23

## Abstract

A run's determinism class (δ) is only meaningful if the sources of
non-determinism are named. This NEP creates the envelope's `run:` block
and declares the two ambient sources every run consumes: randomness
(`entropy: none | ambient | { seeded: <u64> }`) and time (`clock: system |
virtual`). The two dimensions couple — the deterministic states require
the virtual clock, because byte-identical journals need deterministic
time as much as deterministic randomness. The declaration is a contract
input: `entropy: seeded(N)`
forces the deterministic seams (same file, same N, byte-identical
journals), `entropy: none` demands strict determinism, `ambient` is the
honest status quo. Absent, the block defaults to `ambient` + `system` —
nothing existing changes; what changes is that the unknown becomes
visible.

## Motivation

The constitution's third clause: every unknown stays visible. Today a
workflow file cannot say whether its run is replayable, because the
sources of randomness and time are ambient — consumed, never declared.
The industry has already priced the opposite bet: deterministic
simulation testing (the FoundationDB single-seam model · the
TigerBeetle VOPR seed-as-contract-input · Antithesis' 2026 raise) turns
« same seed, same execution » into a sellable property, and durable
execution engines (Temporal · DBOS · Restate) converge on « replay
without determinism is silent divergence ». Nika's seams already exist
(the deterministic stamper, the injected clock, the seeded jitter) —
what does not exist is the declaration that lets a contract claim them.

Without the declaration, the determinism class δ of the contract formula
is decorative: a run claiming replayability while consuming ambient
entropy is an unverifiable promise. With it, δ becomes checkable at
`nika check`, provable by fixtures, and eventually explorable (a
seeded run can be replayed under a different seed to map where the
randomness lives).

## Specification

The law (MUST):

1. **The `run:` block.** The envelope gains an optional top-level
   `run:` block carrying exactly two keys in v1: `entropy` and `clock`.
   The block is a closed set — any other key is refused in both parse
   modes (a typo'd declaration silently not binding would mis-declare
   the determinism contract).
2. **Entropy.** `entropy: none | ambient | { seeded: <u64> }`, default
   `ambient` (bare scalars for the parameterless values · a single-key
   map for the parameterized one). `seeded(N)` forces the deterministic
   seams and pins the run's seed to `N` — two runs of the same file
   with the same `N` produce byte-identical journals. `none` demands
   strict determinism: any structural randomness the engine would
   consume is a finding. `ambient` is the honest status quo — legal,
   and named as what it is.
3. **Clock.** `clock: system | virtual`, default `system`. `virtual`
   substitutes the engine's injected virtual clock for wall time — time
   becomes a contract input, and a `timeout:` budget reads against the
   declared clock.
4. **The dimensions couple (refusals).** Byte-identical journals
   require deterministic TIME as much as deterministic randomness — a
   seeded run under a wall clock leaks wall time into the journal. The
   only legal pairs are `ambient × system` (the status quo) and
   `none | seeded × virtual` (the deterministic states): a declared
   contradiction (`ambient × virtual` · `none | seeded × system`) is
   refused at parse (`NIKA-PARSE-019`). A declaration of strict
   determinism (`none`) combined with a consumed randomness source is
   refused at check. A `timeout:` budget against an undeclared clock
   earns an honesty finding — never a refusal (the status quo cannot
   turn red overnight).
5. **One run, one clock.** The declaration lives at the envelope, never
   per task: a run has exactly one entropy source and one clock, so the
   composition stays auditable.

## Rationale

- **Declaration over inference.** The engine could infer the seams it
  uses; making the author declare them keeps the contract the judge of
  the run, not the engine's word for it. The seed is an input of the
  contract — the VOPR lesson — not an implementation detail.
- **Envelope over per-task.** A per-task clock makes the DAG's
  composition unauditable (which time does a downstream budget read?).
  One run, one clock is the FoundationDB law.
- **Virtual clock over paused wall-clock.** A paused `tokio` clock still
  couples the test to the runtime's scheduler internals; the injected
  virtual clock is a pure seam the receipt can name.
- **Defaults that keep the world green.** `ambient` + `system` absent
  the block means no existing workflow flips. The law bites only where
  an author claims strictness (`none`) — the claim is what gets checked.

## Backwards Compatibility

Fully additive: the block is optional, the defaults are the status quo,
and every existing workflow keeps its current behavior. The only new
refusals attach to explicit declarations (`entropy: none` with a
consumed randomness source · a closed-set violation inside `run:`).

## Reference Implementation

- The engine lane (`feat/f-p3-entropy-clock`): the `run:` block in the
  envelope parser (closed set), the declaration driving the stamper and
  clock selection, the check findings, and the fixtures — the flagship
  pair: `entropy: seeded(42)` twice produces byte-identical journals,
  and `seeded(42)` against `seeded(43)` diverges where the randomness
  lives (the fixture is non-vacuous).
- The boot manifest carries the declaration (NEP-0007's
  `workflow_started` prologue · extended by the F-P2 lane), so the
  journal self-describes its determinism contract.

## Deferred (P2)

- The `time_source` / `time_scale` receipt enums (F-N10) and the
  CGPM-2026 leap-tolerance clause — receipt-side, absorbed by NEP.
- Seed-driven swarm replay (`--swarm N`) as a first-class exploration
  mode — the declaration makes it possible; the mode is its own arc.

## Copyright

This document is placed in the public domain under CC0-1.0, as every NEP.
