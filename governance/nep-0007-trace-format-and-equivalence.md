# NEP-0007 · The trace leaves the private dialect: a normative journal, a required witness, a differential oracle

- **NEP**: 0007 (next free integer · 0001 reserved for the v1 surface · 0002 the trifecta gate · 0003 absent permits · 0004 the parameterization taint · 0005 the environment permit · 0006 the data-as-code sink)
- **Title**: The run journal is a versioned chapter of the spec, every permit decision is a required trace frame, and check ⇔ run agreement is proven by a differential oracle
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-23

## Abstract

NEP-0003 through NEP-0006 hardened WHAT the boundary refuses. This NEP
hardens the claim that the three deciders agree: the static judge, the
running engine, and the journal a verifier reads MUST decide the same
artifact · invariant 4, judged = executed = attested. Three deliverables
make the invariant checkable instead of asserted. (1) The trace format
becomes a normative, versioned chapter ([17](../spec/17-trace.md) ·
`trace_format: 2` · the frame grammar, the hash chain, the prologue
manifest, the kind vocabulary · graved from an observed run, never
invented). (2) Every permit decision the run takes · granted and
refused alike, across every plane · is a REQUIRED `permit_checked`
frame: the boundary becomes attributable after the fact. (3) The
equivalence is proven the Cedar way: a differential oracle replays the
same inputs through the checker and the engine and FAILS on any verdict
divergence, with coverage DERIVED by the suite itself · never « we
tested it well ».

## Motivation

The empirical driver is the measured spec↔engine skew (23 commits of
drift between what the documents said and what the code did, found by
the cross-audit): prose alignment decays, only a machine-checked
equivalence survives. The trace was an engine-private dialect (its
format documented in an internal crate spec), so no second
implementation could verify a journal, and permit decisions were
invisible in it · the vocabulary reserved a `permit_checked` kind that
production never emitted. A boundary that cannot be audited after the
fact is a boundary on trust.

## Specification

The law (MUST):

1. **The format is the chapter.** A conformant engine writes the run
   journal exactly as [17 · Trace](../spec/17-trace.md) specifies:
   NDJSON frames, the sha256 chain over exact previous-line bytes
   (genesis-tagged, head reported), the `workflow_started` prologue
   manifest carrying `trace_format: 2`, terminal frames for the
   workflow and every settled task, and the closed-per-minor kind
   vocabulary. A wire change that breaks a version-2 reader MUST bump
   `trace_format`; additive fields and kinds MUST NOT.
2. **The witness is required.** Every permit decision · the exec
   program gate, the tool grant, the fs and net boundary enforcements,
   the taint re-gate (NEP-0004), the environment composition
   (NEP-0005), the data-as-code sink (NEP-0006) · emits one
   `permit_checked` frame naming the gate, the decision
   (`allow` | `deny`), the law applied, and the task. Granted decisions
   are witnessed, not only refusals: an auditor reconstructs WHAT
   authority was exercised, not only what was blocked.
3. **Old journals stay readable, honestly.** The witness requirement is
   behavioral (a conformance requirement on the engine), not a wire
   bump: `trace_format` stays 2. A verifier reading a journal that
   exercised effects with zero permit-decision frames MUST report a
   FINDING (the witness is absent · the journal predates NEP-0007 or
   the engine is not conformant) · never FORGED (the chain still
   binds), never a crash.
4. **Equivalence is proven differentially.** The conformance suite
   replays the same inputs through BOTH evaluators · the static checker
   and the running engine · and FAILS on any verdict divergence, under
   the mapping law: a check-time refusal (the AUTH series) means the
   run refuses before its prologue; a check-time deferral (NEP-0004
   law 4 · NEP-0006 law 3) means the run's twin refuses at effect time
   (`NIKA-SEC-004`); a clean check means the run stays inside the
   declared boundary. Cases outside the mapping (pause · resume ·
   cancel) are DECLARED out of scope, never silently forced.
5. **Coverage is derived.** The differential suite counts and prints
   what it covered (families × planes × fixtures); no coverage figure
   is ever hand-written. What is not covered is named residual.

Registry and prose touched:

- **LAW-AUTH-0328** is added to `canon/laws/authority.yaml` (status
  active) · the machine row of this NEP.
- `spec/17-trace.md` is NEW (the chapter) · `spec/00-overview.md` maps
  it.
- No new diagnostic code: the verify surface reports the absent witness
  as a finding in its own verdict vocabulary, and the runtime refusal
  voice stays `NIKA-SEC-004`.
- Implementation surfaces: the event vocabulary (the reserved
  `permit_checked` kind gains its payload contract) · the runtime
  gates (emission) · the trace verifier (the REQUIRED-witness rule) ·
  the conformance differential suite.

## Conformance test

The golden journal ships as a conformance artifact · a REAL run's
trace (chained · sealed head · byte-verifiable) with its workflow ·
plus verify contracts: the intact journal verifies clean; the same
journal judged under NEP-0007 with effects and no witness frames is a
FINDING; a tampered byte is FORGED. The differential suite is
engine-side (it needs both evaluators) and prints its derived coverage.

## Compatibility impact

Additive. Old journals read clean under the chain walk and report the
absent witness as a finding (law 3). New journals grow one frame kind
per permit decision · the same order of magnitude as `tool_invoked`,
bounded by the existing retention caps.

## Rejected alternatives

- **Bumping `trace_format` to 3 for the witness** · rejected: the frame
  grammar is unchanged; version churn without a wire break makes every
  reader gate on a number that means nothing.
- **A new diagnostic code for the absent witness** · rejected for v1:
  the verifier's verdict vocabulary already distinguishes FINDING from
  FORGED; minting a wire code for a verify-surface report adds registry
  weight without a new refusal class.
- **Witnessing refusals only** · rejected: refusals already surface as
  task failures; the auditable gap is the GRANTED authority · the
  boundary you cannot reconstruct is the one that was exercised.
- **Proving equivalence by shared code** · rejected as the sole answer:
  shared predicates (the house pattern) kill one drift class, but only
  the differential replay proves the COMPOSED pipelines agree end to
  end (the Cedar lesson · RS-13).
