# NEP-0012 · The receipt is untrusted input

- **NEP**: 0012 (next free integer · 0011 the attested run lifecycle)
- **Title**: The verifier is a fortress — decode bounds are spec constants, terminal output is escaped, malicious artifacts are recognized rather than repaired, and two independent decoders must agree
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-24

## Abstract

The trace, the receipt and the seal exist to be VERIFIED — which means
the verifier is the one component guaranteed to parse attacker-supplied
bytes. This NEP hardens the reading side with four laws: (a) decode
bounds are NORMATIVE SPEC CONSTANTS (input size · line length · nesting
depth · proof-node count · identifier length), refused with a typed
finding, never silently truncated; (b) every artifact-derived field
printed to a terminal is escaped (C0/C1/DEL/OSC) — the TTY surface
only, the machine JSON stays byte-exact; (c) malicious artifacts are
RECOGNIZED against a golden corpus, never sanitized into acceptability
(the langsec law); (d) the reference decoder and the engine decoder
render the SAME verdict on the same artifact (the differential twin),
and the decode surface carries its own fuzz target.

## Motivation

The 2026 H1 parser CVEs are the anchor set: unbounded recursion at
decode (CVE-2026-26209 — the direct ancestor of the depth bound),
bounds carried by assertions compiled out in release (CVE-2026-29013 —
bounds must be code), deserializers that instantiate
(CVE-2026-31072). LangSec's shotgun-parser diagnosis remains the
frame: a verifier that partially repairs hostile input becomes the
vulnerability. Nika's three anchor surfaces (tier ladder · Rekor
sidecar · RFC 3161 token) already parse fail-closed — this NEP
generalizes that discipline into constants and laws so the NEXT reader
(and the second implementation) inherits it, instead of re-deriving it.

## Specification

The law (MUST):

1. **Bounds are constants.** The verifier refuses, with a typed
   finding, any artifact exceeding the spec's decode bounds — input
   size, journal line length, JSON nesting depth, proof-node count,
   identifier length. The bounds live in the spec as named constants
   (the values are the lane's, frozen with the law); refusal is total —
   no partial decode, no truncation-and-continue. Bounds are enforced
   by code on every build profile, never by debug assertions.
2. **Terminal hygiene.** Every artifact-derived string rendered to a
   TTY is escaped: C0 controls, C1, DEL, and OSC/CSI sequences cannot
   reach the terminal raw. The machine surfaces (`--json`, non-TTY
   stdout) stay byte-exact — pipelines read the truth, humans read the
   escaped rendering.
3. **Recognize, don't sanitize.** A malicious artifact is classified
   and refused; the verifier never repairs input into acceptability.
   The golden corpus (`receipts/malicious/` · the lane's classes:
   oversized · deep · flood · escape-bearing · truncated · duplicated
   · confused) lives WITH the engine's tests and is born with this law
   (ratchet NEP-0000). A crash, hang or overflow on the corpus is a P0
   engine bug by definition.
4. **The differential twin.** The reference decoder (`proof_core` ·
   Python) and the engine decoder MUST render the same verdict over
   the corpus — the mirror discipline `nika.lock` already lives by. A
   divergence is a spec bug until proven otherwise.
5. **The fuzz floor.** The receipt/journal decode surface carries its
   own fuzz target beside the existing four (parse · CEL · capability
   · permits), exercised in CI on the golden corpus seeds.

## Rationale

- **Constants over folklore.** The three disciplined surfaces got
  their bounds by craft; constants make the discipline portable to the
  second implementation (the weekend-doable rule) and auditable.
- **TTY-only escaping.** Escaping the machine surface would break
  byte-exact pipelines; the terminal is where escape sequences become
  an attack (title injection · clipboard writes · hidden text).
- **Corpus with the engine.** The fixture is born with the law and
  runs on every engine change — a conformance-repo corpus would gate
  only at pin bumps.

## Backwards Compatibility

Verification-side only: artifacts within bounds verify exactly as
before. Artifacts beyond bounds previously produced undefined behavior
(unbounded work · raw terminal bytes); they now produce a typed
refusal — naming behavior that was never a promise.

## Reference Implementation

- The engine lane (F-P1): bounds before `serde_json::from_str` on the
  receipt read, a line cap on the journal walk, the promoted
  `sanitize()` law on the verify render, the golden corpus under the
  forensics crate's tests, the 5th fuzz target, and the Rust-vs-Python
  differential over the corpus.

## Deferred (P2)

- Always-escape (non-TTY included) — rejected for v1: it breaks
  byte-exact pipelines; revisit only with evidence.
- Corpus sub-classes beyond the lane's set; sub-cause taxonomy of
  refusals.

## Copyright

This document is placed in the public domain under CC0-1.0, as every NEP.
