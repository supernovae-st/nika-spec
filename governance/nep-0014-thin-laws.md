# NEP-0014 · The thin-laws (lot 3a): observable independence · input origins · the readable receipt · cross-version resume

- **NEP**: 0014 (next free integer · 0001 reserved for the v1 surface · 0002 the trifecta gate · 0003 absent permits · 0004 the taint · 0005 the environment permit · 0006 the data-as-code sink · 0007 the trace and the oracle · 0008 the egress projection · 0009 the effective path identity · 0010 the run declaration · 0011 the run lifecycle · 0012 the receipt as untrusted input · 0013 the approval ticket)
- **Title**: Four small laws of the contract — two incomparable tasks never share a write, every run input carries its origin, every receipt field carries a readable projection, and a resume across engine versions is explicit
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-29

## Abstract

Four laws too small for their own NEPs and too real to stay unwritten.
(1) Observable independence: two tasks whose writes overlap and that no
edge orders are a finding — parallelism is only safe where it is
observable. (2) Input origins: every run input carries an enumerated
origin (cli-operator · env · file · ci-context) that rises to the
receipt — an undeclared env read in CI is a finding. (3) The readable
receipt: every receipt field carries a human-readable projection in the
schema — a field without one refuses the schema; `explain` is reading,
never evidence. (4) Cross-version resume: resuming a run under a
different engine version is an explicit refusal naming both versions,
or a declared compatibility attested at the receipt — silent downgrade
dies.

## Motivation

Each law is a corner where the contract was ambient instead of written.
Parallel tasks that share a write path are a data race the file never
declares — the engine already *hints* it; a hint is not a boundary. A
run's inputs arrive from channels the receipt does not name — so a CI
environment variable can silently become the operator. A receipt that
only a machine can read is a receipt no one audits in 100 years. And a
resume across versions that degrades silently is judged ≠ executed for
the replay class. None of these needs a new mechanism; each needs the
law to say what the code already almost does.

## Specification

### Law 1 · Observable independence (F-P15)

Two tasks **incomparable** in the DAG closure (no path between them, in
either direction) whose filesystem WRITE effects overlap are a check
finding (`security_error` class). An explicit `depends_on` (or any
ordering edge) discharges it. A `for_each` fan writing the same path is
refused likewise. Parallelism is safe exactly where the effects are
provably disjoint.

### Law 2 · Input origins (F-P13)

Every workflow input the run binds carries an enumerated **origin** —
`cli-operator` · `env` · `file` · `ci-context` — propagated to the
receipt. The declared `type:` governs the `--var` parse (already the
engine's behavior); an environment variable feeding an input that is
not declared as env-sourced is a finding in CI. The untyped guess
(JSON-or-string) is graved behavior, documented, never silent.

### Law 3 · The readable receipt (F-P16)

Every field of the receipt schema carries a **readable projection** in
the schema itself; a new field without a projection refuses the schema
(the ratchet). The `nika receipt explain` verb renders that projection
as stable text. The projection is NEVER the evidence: `explain` is
reading, `verify` is proof — the two never share a trust level.

### Law 4 · Cross-version resume (F-P21)

A resume of a trace under an `engine_version` different from the
recording one is an explicit refusal naming both versions — or a
declared compatibility, attested at the receipt. The silent
degradation (the old implicit plan-empty fallback) ceases to exist:
the version is judged, never assumed.

## Rationale

- **Promotion over invention**: each law promotes an existing
  mechanism (the parallel-writer hint · the declared-type coercion ·
  the certificate's structure · the resume fold) into a written
  boundary — the cheapest correctness is the kind already half-built.
- **Ratchets over reminders**: law 3 lives in the schema itself, so a
  future field cannot forget its projection — the check refuses it,
  no human needs to remember.
- **Explicit over silent**: laws 2 and 4 close the two channels where
  an environment (CI variables · a newer binary) could silently become
  the operator's intent.

## Backwards Compatibility

Law 1 refuses workflows that were racy all along (a finding is the
correct verdict for an unordered shared write). Laws 2 and 4 are
additive surfaces (origin field · explicit refusal) — existing green
workflows keep their shape. Law 3 changes only the schema's own gate.

## Reference Implementation

- The engine lane (`feat/lot3-thin-laws`): the parallel-writer hint
  promoted to a refusal · the input-origin enumeration at the CLI
  binding · the schema projection gate and `receipt explain` · the
  cross-version resume judgment — each with its fixture pair.
- The remaining thin-laws (F-P18 pricing pin · F-P14 end obligation ·
  F-P22 blame polarity · F-P23 solo endorsement) ride their own
  follow-up; this NEP covers the first four only.

## Copyright

This document is placed in the public domain under CC0-1.0, as every NEP.
