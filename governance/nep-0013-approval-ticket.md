# NEP-0013 · Human approval is a bounded, content-bound, attested ticket

- **NEP**: 0013 (next free integer · 0001 reserved for the v1 surface · 0002 the trifecta gate · 0003 absent permits · 0004 the parameterization taint · 0005 the environment permit · 0006 the data-as-code sink · 0007 the trace and the equivalence oracle · 0008 the egress projection · 0009 the effective path identity · 0010 the run declaration · 0011 the run lifecycle · 0012 the receipt as untrusted input)
- **Title**: Human approval is a bounded, content-bound, attested ticket — the shown is the signed, scoped, TTL'd, rate-limited, and chained into the journal
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-24

## Abstract

The human gate is the last unbounded authority surface in the engine:
an approval is a bare answer to a prompt — nothing binds what was shown
to what was signed, nothing bounds a burst, and nothing attests the
decision in the journal. This NEP makes every human approval a
**ticket**: content-bound (the shown is the signed — the hash of the
canonical rendering, never an LLM summary), scoped (this run × this
step × this content hash), TTL'd, rate-limited (N per run — the N+1th
is a typed HALT, never a queue), and attested (a hash-chained
`approval_decided` event, revocable before execution only). It is the
contract system's sixth invariant: no human authority is exercised
beyond what its ticket declares.

## Motivation

Consent fatigue is measured, not hypothetical: the accept-reflex
majority under repeated prompting means a burst of identical prompts
collects bare approvals by exhaustion. An `--answer` in a resumed run
answers content the human may never have seen — nothing today proves
shown = signed. And the journal cannot say who approved what, when,
under which scope: an approval that leaves no attestation is ambient
authority with extra steps.

The existing gates (NEP-0002's trifecta gate · `policy:
require.human_gate_before`) decide THAT a human must approve; they say
nothing about HOW the approval is bounded. This NEP is the HOW. The
operator's constraint is normative: approval happens at the CONTRACT,
rarely, never at the action — there is no yolo mode, and there never
will be.

## Specification

The law (MUST):

1. **Content-bound (WYSIWYS).** The ticket binds the hash of the
   canonical rendering of what is shown: the message, the gated
   action's identity, and the effect classes in play — JCS-canonical,
   never an LLM-generated summary. An answer whose resolved content
   hash differs from the shown hash halts with an
   `approval.content_mismatch` finding at the receipt.
2. **Scope and TTL.** A ticket lives for this run (the run nonce) ×
   this step × this content hash, with a bounded TTL (engine-named
   constant, 15 minutes default). An expired ticket re-prompts — it
   is never inherited; a ticket replayed across runs is refused (the
   nonce does not match).
3. **Anti-fatigue.** Approvals are rate-limited per run (engine-named
   constant N=5). Identical prompts dedup (the same content hash rides
   the same ticket — attested `dedup`, the human is not re-asked). A
   heterogeneous batch (different actions folded into one approval) is
   refused at check: one prompt gates one action of one class. The
   N+1th prompt of a run is a typed HALT (`security_error`) — never a
   queue.
4. **Attestation.** Every decision emits a hash-chained
   `approval_decided` event carrying the ticket digest, the shown
   hash, the decision (allow · deny · dedup), the remaining TTL, and
   the scope — and the digests rise to the receipt.
5. **Revocation.** A decided ticket may be revoked before the gated
   action starts — never after: the receipt shows what executed under
   which authority, and nothing is rewritten retroactively.

## Rationale

- **Content-bound over content-free.** The WebAuthn WYSIWYS lesson:
  what-you-see is what-you-sign, or the signature is theatre. An
  LLM-written summary is excluded by construction — the rendering is
  canonical and engine-produced, so the hash binds bytes the human
  actually read.
- **Dedup over re-prompt.** Re-asking the identical question trains
  the reflex the rate-limit exists to defeat. The dedup attestation
  keeps the receipt honest: one decision, N consumers.
- **HALT over queue.** A queue converts fatigue into latency; a HALT
  converts it into a finding — the workflow that needs a sixth
  approval in one run must declare a batched gate at the contract.
- **The ticket around the prompter.** The `Prompter` seam (TTY ·
  headless) stays pure; the ticket wraps it at the runtime layer, so
  the binding lives in the TCB that already owns the journal.

## Backwards Compatibility

Workflows using `nika:prompt` keep their current semantics — the
ticket wraps, it does not rename. The new refusals are the burst
(N+1th), the content mismatch, and the cross-run replay: all three
were unbounded authority before. The `approval_decided` event kind is
additive to the journal vocabulary (see Deferred).

## Reference Implementation

- The engine lane (`feat/f-p4-approval-ticket`): the ticket mint
  (`approval.rs`), the rate-limit and dedup state, the pause/resume
  ticket validation, the `approval_decided` event, the check-side
  heterogeneous-batch refusal, and the fixtures — the burst HALT, the
  content-mismatch HALT, the TTL re-prompt, the cross-run refusal, the
  dedup attestation, and the honest gate green end to end.

## Deferred

- The `approval_decided` event kind vs an additive field on an
  existing frame (the journal vocabulary is closed-per-minor; the
  kind-bump decision lands with the freeze verdict).
- Per-hour rate limiting (per-run in v1) · approval quorums (the
  endorsement lane) · the full permits-diff rendering in the shown
  content (v1 renders message + action identity + effect classes).

## Copyright

This document is placed in the public domain under CC0-1.0, as every NEP.
