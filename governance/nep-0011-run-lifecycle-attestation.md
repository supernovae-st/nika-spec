# NEP-0011 · The run has an attested beginning and an attested end

- **NEP**: 0011 (next free integer · 0010 the run entropy + clock declaration)
- **Title**: The run's lifecycle is attested — a boot manifest binds the run to its judgment, the teardown seal binds the outcome to its evidence, and an unterminated journal is the VERIFIER's finding, never the dying process's silence
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-24

## Abstract

A trace can prove single frames, but the RUN as a whole has no attested
lifecycle: nothing binds what `nika check` judged to what actually
boots, the seal covers the journal but not the receipt it summarizes,
and a run killed mid-flight simply stops — a silence a reader can
mistake for success. This NEP creates the three lifecycle frames:

1. **BOOT** — the `workflow_started` prologue becomes a boot MANIFEST:
   the existing fields gain the contract inputs (`spec_pin` ·
   `stamper_kind` · the resolved `clock` · the `seed` when the
   declaration demands determinism), so the journal self-describes the
   contract it runs under.
2. **TEARDOWN** — the run seal's `covers` extends additively:
   `receipt_digest` (the run receipt folded at the seal instant ·
   recomputable), the consumed budgets (ρ), the exercised effects (ε).
3. **INCOMPLETE** — a journal whose chain walk reaches no
   lifecycle-terminal frame is classified **`incomplete`** — a finding
   carried by the VERIFIER, never a frame emitted by the dying process.

And the binding law: **jugé ≠ booté = refus** — a run whose check
report is stamped with a different semantic hash than the workflow it
is booting REFUSES to start, before its first event.

## Motivation

The constitution's third clause: every unknown stays visible. A `kill
-9` today produces a journal that just… stops. The fold already refuses
to conjure a verdict from it (honest), but the absence has no NAME — a
pipeline reading the trace cannot distinguish « still running » ·
« died » · « tampered ». Likewise the seal proves the journal's
integrity but not the receipt's derivation from it, and nothing proves
the workflow that boots is the workflow that was judged.

The industry has no standard to follow (verified 2026-07-23): OTel's
GenAI conventions are at zero stable attributes for run manifests;
Temporal, DBOS and Restate keep proprietary step journals whose
lifecycle lives in their databases, not in a portable attested
artifact. Nika's substrate already exists (the 10-field prologue · the
ed25519 seal · the fold's terminal-kind discipline) — what does not
exist is the CONTRACT that makes the lifecycle attestable end to end.

## Specification

The law (MUST):

1. **The boot manifest.** The `workflow_started` prologue carries, in
   addition to its existing fields: `spec_pin` (the spec commit the
   engine's conformance is proven at), `stamper_kind`
   (`deterministic` | `system` — the event-identity seam the `run:`
   declaration resolves to, the SAME resolution the composer's stamper
   pick rides), `clock` (`system` | `virtual` — the resolved run-level
   clock, NEP-0010's `clock_or_default`), and `seed` (present exactly
   when the declaration demands determinism: `seeded(N)` → `N` ·
   `none` → the zero stream; an ambient run carries no seed claim).
   All additions are ADDITIVE — tolerant readers ignore unknown
   fields; a manifest claims only what exists (absent is honest).
2. **The teardown seal.** The seal's `covers` object gains
   `receipt_digest` (the digest of the run receipt folded from this
   seal's OWN pre-seal chain facts — a verifier MUST recompute it from
   `covers.head` / `covers.events`; the folded receipt fixes
   `chain: intact` and `sealed: true` at the seal instant, so its
   digest is deliberately NOT the later evidence-pack receipt's),
   `budgets` (the consumed ρ — `spent_usd` only when metered, never a
   fabricated zero), and `effects` (the exercised ε at the
   effect-task attempt grain, beside the declared bound). The
   extension is ADDITIVE: a teardown-less seal's `covers` stays
   byte-identical to the classic four fields and verifies exactly as
   before; a seal that carries the new fields binds them under the
   same signature.
3. **The incomplete class.** The chain walk classifies a journal that
   reaches no lifecycle-terminal frame (`workflow_completed` ·
   `workflow_failed` · `workflow_paused` · `workflow_cancelled` ·
   `run_sealed`) as **`incomplete`** — a finding of the VERIFIER,
   surfaced by `nika trace verify` and by every reader of the walk
   (evidence packs · projections). A dying run emits nothing at death;
   the classification is always the reader's. Incomplete is never
   success and never silently equal to failure: it is its own named
   class, and the verify exit stays the tier ladder's (an incomplete
   journal is not a verification failure — the journal is honestly
   what it is).
4. **Jugé ≠ booté = refus.** A check report STAMPED with the semantic
   hash of the workflow it judged must match the workflow the run is
   booting: on mismatch the run REFUSES before its first event (zero
   events emitted — the refusal precedes the prologue), and the CLI
   exits with the file-findings code (2). The grain is SEMANTIC: a
   cosmetic edit (whitespace · a comment) re-keys nothing and never
   refuses; a content edit — even structure-preserving — does. An
   UNSTAMPED report skips the clause (the stamp is the producer's
   opt-in; the trust backstop clauses remain).
5. **One run, one lifecycle.** Boot is one frame, teardown is one
   seal; neither exists per task. (The per-task story is the
   receipt's, not the lifecycle's.)

## Rationale

- **Verifier-borne honesty.** A dying process cannot attest its own
  death (it may not get the chance) — any protocol that asks it to is
  vacuous exactly when it matters. The verifier carries the
  classification because the verifier is the only party guaranteed to
  exist at reading time.
- **Additive covers over a new frame.** The seal already exists and is
  fail-closed; extending `covers` keeps ONE signature surface and
  tolerant readers, instead of minting a second attestation artifact.
- **Seal-side binding over certificate-side.** The `RunCertificate`
  stays structural and replayable across engine editions (the reprise
  law); the seal is already the signed surface, so the source binding
  (`covers.workflow` — the SEMANTIC hash) lives there.
- **Boot-time refusal over verify-time.** The binding law fires at the
  run gate, before the prologue — the earliest honest moment. A stale
  report never gets to produce a journal that must later be distrusted.
- **Defaults that keep the world green.** Old journals (no new fields)
  verify exactly as before; the new refusals attach only to artifacts
  that CARRY the new claims — plus the `incomplete` NAME for a state
  that was already unverifiable, now visibly so.

## Backwards Compatibility

Fully additive on the emit side (new prologue fields · new covers
fields · a new field on the check report, `report_version` unchanged).
On the verify side, `incomplete` names a state that previously
produced no verdict — pipelines that treated « no verdict » as success
were already wrong, and now have a class to key on. No existing sealed
journal changes verdict.

## Reference Implementation

- The engine lane (`feat/f-p2-run-lifecycle`): the extended prologue
  (one `opening` vec · zero new plumbing · the single emission site
  preserved), the additive `covers` extension (the classic
  four-field seal pinned byte-identical by a regression test), the
  `incomplete` class in the chain walk (evidence packs · projections ·
  the verify surface all read it), the boot-time binding clause (the
  refusal precedes the prologue · the CLI maps it to exit 2 · the
  semantic grain proven by a cosmetic-twin test), and the fixtures —
  a terminal-less journal verifies INCOMPLETE; the extended seal is
  recomputed and verified through the real tier ladder; the
  no-fake-zero and attempt-grain folds are unit-pinned.
- NEP-0010's declaration rides the manifest: `stamper_kind` / `clock`
  / `seed` are the runtime's answer to the envelope's `run:` block —
  the journal proves which determinism contract actually ran.

## Deferred (P2)

- `time_source` / `time_scale` — the F-N10 RECEIPT enums stay
  receipt-side (out of the run block by design); the run-level time
  axis is the manifest's `clock` claim.
- `lock_digest` in the boot manifest — no lock-recording surface
  exists today (the `LOCK_UNRECORDED` posture): the manifest claims
  only what exists. The field lands with the lock-recording lane,
  operator-ratified.
- A nonzero verify exit for `incomplete` — the shipped law keeps the
  tier ladder's exit; tightening it is an operator choice.
- Sub-causes of `incomplete` (killed · truncated · still-running) —
  the class is deliberately one name in v1; forensics may refine it.
- Certificate-side source binding (defense in depth) — rejected for
  v1: it would make the certificate non-replayable across editions.

## Copyright

This document is placed in the public domain under CC0-1.0, as every NEP.
