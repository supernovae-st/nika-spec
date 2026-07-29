# NEP-0016 · Provenance tiers: every registry artifact resolves with a measured tier, and the admission floor is operator data

- **NEP**: 0016 (next free integer · 0001 reserved for the v1 surface · 0002 the trifecta gate · 0003 absent permits · 0004 the parameterization taint · 0005 the environment permit · 0006 the data-as-code sink · 0007 the trace and the equivalence oracle · 0008 the egress projection · 0009 the effective path identity · 0010 the run declaration · 0011 the run lifecycle · 0012 the receipt as untrusted input · 0013 the approval ticket · 0014 the thin-laws lot 3a · 0015 preview-commit)
- **Title**: Provenance tiers — a closed ladder (`unprovenanced < provenanced < stage-clear < verified`) admitted by evidence only, an operator-owned admission floor, and the tier recorded at fetch and attested at the receipt
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-29

## Abstract

Today the registry resolver proves two things — content integrity (the
pinned digest) and, for signed entries, origin (minisign under a
TOFU-anchored publisher key) — but it speaks a bare boolean, lets no
operator set an admission floor, and records nothing a receipt can
attest. This NEP replaces the boolean with a **closed tier ladder**
(`unprovenanced < provenanced < stage-clear < verified`), admitted only
by evidence observed at fetch, never by a registry claim. The admission
floor is **operator data** — a versioned policy file, never a constant
in code. A fetch below the floor refuses before anything is written
(`NIKA-REG-008`), the tier is recorded with the cache record, and it
rises to the receipt: every run attests the provenance of what it
consumed.

## Motivation

The registry's trust model (registry-v0.1 §0) already says trust lives
in re-derivable evidence, not in the gatekeeper. What is missing is the
*vocabulary*: two registry-side attestations are designed and waiting —
the staged window (F-P25) and trusted publishing (F-P24) — and they
have no shape to land in. A boolean cannot grow four states. A floor
written in source code is a policy nobody reviewed: an operator who
wants "this machine runs only provenanced modules" should edit a file,
not a build. And a run that consumed a third-party workflow owes its
receipt the provenance of that act — today the receipt cannot say it.

## Specification

The law (MUST):

1. **The closed ladder.** The tier set is exactly
   `unprovenanced < provenanced < stage-clear < verified`, totally
   ordered. An unknown tier string — in a policy file, a cache record,
   or any registry statement — refuses. The set is closed the way the
   verb set is closed: growth is a spec amendment, never a parse.
2. **Evidence admits, never claims.** A tier is admitted ONLY by
   evidence observed at fetch:
   - `unprovenanced` — the digest floor (registry-v0.1 §1): bytes
     provably consistent with the pinned `integrity.sha256`, origin
     unproven.
   - `provenanced` — the artifact's minisign verifies (registry v0.2)
     under the publisher's TOFU-anchored key: origin proven to a key,
     key continuity proven by the TOFU record.
   - `stage-clear` — a registry staged-window statement (the format
     lands with F-P25; reserved in v1).
   - `verified` — a complete in-toto publish layout (the format lands
     with F-P24; reserved in v1).
   The index is a convenience projection (registry-v0.1 §4): a tier
   asserted there and not re-derived from evidence admits NOTHING.
3. **The floor is operator data.** `~/.nika/registry/policy.toml`:
   `{ version = 1, floor = "<tier>" }`. An absent file means
   `floor = "unprovenanced"` — today's behavior, stated honestly. An
   unknown `version` or an unknown `floor` refuses. No floor lives in
   source: the default is the semantics of absence, every change is an
   operator edit — reviewable, greppable, attributable.
4. **Below floor refuses.** A fetch whose admitted tier is below the
   floor refuses with `NIKA-REG-008` and NOTHING is written — the
   refusal happens after verification, before the store. A cache hit
   whose recorded tier is below the floor refuses identically (the
   policy changed under the cache; the cache does not grandfather).
5. **The tier is recorded and attested.** The cache record carries
   `tier` alongside the digest; a cache hit re-tells the recorded truth
   (evidence is not re-sought on a hit — the record IS the evidence of
   what that fetch proved). The tier of every registry artifact a run
   consumes rises to the receipt.
6. **No downgrade, no inflation.** A record naming a tier its evidence
   class cannot admit (e.g. `verified` on a v1 record) is treated as
   tampered (the `NIKA-REG-004` class). A later registry-side upgrade
   rewrites nothing: re-fetch re-proves; the receipt of the day tells
   the truth of the day.

## Rationale

- **A closed ladder over a string.** Four states, totally ordered,
   everything else refused — the same closed-set law as the verbs. A
   tier an engine does not know is a smuggling channel, never a floor.
- **Evidence over claims.** The registry-v0.1 trust model already
   refuses to trust the index; the tier inherits it. What the fetch
   observed is the only truth the cache record may speak.
- **Data over code.** A policy constant in a binary ships unreviewed.
   The file makes the floor an operator artifact — the same shape as
   the TOFU key store, the pin record, the cache itself.
- **Refusal before store.** Nothing below the floor ever reaches the
   cache, so a poisoned fetch cannot become a later cache hit. The
   store remains the moment where only verified bytes land
   (registry-v0.1 R3).

## Backwards Compatibility

The default (absent policy file) is exactly today's behavior: unsigned
entries resolve with the v0.1-floor mark. Cache records written before
this NEP carry `signed` and no `tier`; they read as the tier their
boolean denotes (`signed: true` → `provenanced`, else `unprovenanced`)
— no migration, no invalidation. The `Resolved` surface gains the
tier; the digest story is untouched.

## Reference Implementation

- The engine lane (`feat/f-p27-provenance-tiers`): the `ProvenanceTier`
  closed enum, the policy-file read with its absence semantics, the
  floor gate before store and at cache hit (`NIKA-REG-008`), the
  recorded tier with its legacy-boolean read, the receipt surface, and
  the fixtures — the unsigned entry below a `provenanced` floor refused
  with nothing written, the unknown tier string refused, the inflated
  record treated as tampered, the cache hit under a tightened floor
  refused, the honest default green end to end.

## Deferred

- The `stage-clear` evidence format (the staged-window statement ·
  F-P25, the registry arc) and the `verified` evidence format (the
  in-toto publish layout · F-P24): v1 reserves both tiers and admits
  neither — an engine that cannot observe the evidence must not admit
  the tier.
- Per-publisher floor overrides (`floor.publishers`) · signed policy
  files (the policy as an attested artifact) · the `nika add` verb's
  policy surface.

## Rejected alternatives

- **Keeping the boolean.** Two states cannot hold the four the
  registry roadmap already names; the boolean becomes a lie the day
  `stage-clear` lands.
- **A hardcoded floor.** A policy in source is a policy no operator
  reviewed — the file is the point.
- **Trusting an index-declared tier.** The index is a projection; a
  projection that cannot be re-derived is treated as tampered
  (registry-v0.1 §4) — a tier is no exception.
- **Refusing all unsigned entries at v1.** The existing corpus is
  unsigned; the floor exists so each operator chooses, and the default
  tells the truth about what the floor proves (consistency, not
  origin).

## Copyright

This document is placed in the public domain under CC0-1.0, as every NEP.
