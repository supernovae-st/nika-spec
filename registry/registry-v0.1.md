# Registry v0.1 · the sharing contract

> How Nika artifacts are shared: the entry format, the trust model, and
> the surfaces any conformant registry MUST serve. Versioned independently
> of the language (like the stdlib). SPDX-License-Identifier: Apache-2.0
>
> Reference implementation:
> [supernovae-st/nika-registry](https://github.com/supernovae-st/nika-registry).
> This document is the contract; anyone can run a conformant registry —
> an org-internal one, a mirror, a fork — and `nika add` (engine roadmap)
> will speak to all of them identically.

---

## 0 · The trust model (normative)

A registry is a **thin, forkable phonebook**. It stores *pointers, digests
and proofs* — never artifact copies, never code that runs at install time.

1. **Identity is decentralized.** An artifact lives in its author's git
   repository. An entry pins it by *full commit* + *full sha256*. Anyone
   can verify the bytes from anywhere; the registry's death or capture
   cannot change what a pinned reference resolves to.
2. **Trust lives in the artifact, not the gatekeeper.** Every claim an
   entry makes (hash, conformance, effects) MUST be re-derivable locally
   by the consumer. A registry's CI re-proves entries as a *convenience*;
   a consumer who re-runs the proof needs no registry at all.
3. **Entries are immutable.** A merged entry never changes. A new release
   is a new entry file. Withdrawal is an *advisory*, never a deletion —
   reproducibility survives revocation.
4. **Zero install-time execution.** Entries and artifacts are data. A
   conformant client writes bytes to disk and stops; execution is a
   separate, explicit, user-owned step (`nika check`, then `nika run`).

## 1 · The entry (normative)

One TOML file per released version, at the path:

```
registry/<type>s/<publisher>/<name>/<version>.toml
```

```toml
schema = 1                      # this contract's version
type = "workflow"               # workflow · pack · skill · agent · template · policy · bench
name = "meeting-actions"        # ^[a-z0-9][a-z0-9-]{0,63}$ · MUST equal the parent dir
publisher = "acme"              # GitHub owner · MUST equal the grandparent dir
version = "1.2.0"               # SemVer · MUST equal the filename
description = "One line."
license = "Apache-2.0"          # SPDX id from the registry's allowlist
spec = "nika/v1"                # the language contract the artifact targets

[source]
repo = "acme/workflows"         # ^owner/name$ · owner MUST equal publisher
rev = "<40-hex commit>"         # full commit · tags and branches are FORBIDDEN
path = "flows/meeting-actions.nika.yaml"   # repo-relative · no traversal

[integrity]
sha256 = "<64-hex>"             # of the exact bytes at repo@rev:path

[cert]                          # OPTIONAL · informative — never trusted
oracle = "nika-spec conformance/runner.py @ <rev>"
conformance = "pass"

[signature]                     # OPTIONAL · reserved (v0.2)
scheme = "minisign"
pubkey = "RW..."
sig = "flows/meeting-actions.nika.yaml.minisig"   # sidecar in the SOURCE repo
```

Constraints a conformant registry MUST enforce (each maps to a documented
registry failure class):

| # | Rule | Kills |
|---|---|---|
| R1 | entry files are immutable once merged | unpublish breakage · rug pulls |
| R2 | `rev` = full 40-hex commit · `sha256` = full 64-hex · path repo-relative, no traversal | mutable-tag rewrites |
| R3 | fetched bytes MUST hash to `integrity.sha256` | metadata that lies about content |
| R4 | the artifact MUST pass the conformance oracle at verify time | broken or lying artifacts |
| R5 | key-shaped strings in the artifact refuse the gate | shared-template credential leaks |
| R6 | `publisher` MUST equal the path segment AND own `source.repo` | dependency confusion · typosquatting |
| R7 | `license` MUST be a declared, allowlisted SPDX id | unlicensed redistribution |

Unknown top-level or `[source]` fields MUST be rejected (a field the gate
does not understand is a smuggling channel). Artifacts SHOULD be bounded
in size (the reference caps at 1 MB — workflows are kilobytes of text).

## 2 · The certificate (normative where present)

A registry MAY project the engine's static analysis into a per-entry
certificate (the reference does, from a digest-pinned engine):

```json
{
  "engine": "0.95.0",
  "sha256": "<the entry's pinned digest>",
  "certificate": {
    "clean": true,
    "llm_calls": 2,
    "cost_usd": { "bounded_total": 0.6, "has_unbounded": false },
    "secret_leaks": [],
    "permits_boundary": "permits:\n  exec: false\n  tools: [...]"
  }
}
```

Rules: the certificate MUST name the engine version that produced it;
consumers MUST be able to re-derive it (`nika check --json` on the pinned
bytes); a UI presenting it MUST show the exec flag and the cost bound —
these are the two facts a user needs before running foreign automation.

## 3 · Advisories (normative)

Withdrawal is additive. One TOML per advisory:

```toml
id = "NIKA-ADV-2026-0001"       # registry-scoped, immutable id
published = "2026-07-06"
severity = "high"               # low · medium · high · critical
affected = "workflows/acme/meeting-actions"
versions = ["1.2.0"]
summary = "One line: what is wrong."
details = "What happened · how found · what a consumer should do."
action = "upgrade to 1.2.1"     # or "do not run · no fix"
```

A conformant client MUST consult advisories before install and MUST
refuse (not warn) on a matching one unless explicitly overridden.

## 3b · Provenance tiers (normative)

Trust in an artifact is not a boolean. A client resolves every artifact
with a **tier**, on a closed, totally-ordered ladder ·

```
unprovenanced  <  provenanced  <  stage-clear  <  verified
```

1. **The ladder is closed.** An unknown tier string — in a policy file,
   in a cache record, in any registry statement — REFUSES. It grows by
   amending this specification, never by parsing something new.
2. **Evidence admits; a claim admits nothing.** A tier is earned only
   by evidence observed AT FETCH ·
   - `unprovenanced` — the digest floor of §1: bytes provably
     consistent with the pinned `sha256`, origin unproven.
   - `provenanced` — the artifact's signature verifies under the
     publisher's anchored key: origin proven to a key, key continuity
     proven by the anchor record.
   - `stage-clear` · `verified` — reserved: their evidence formats (a
     staged-window statement · a complete publish layout) land with
     the work that defines them.

   The `index.json` of §4 is a convenience projection: a tier asserted
   there and not re-derived from evidence admits **nothing**. This is
   §0 law 2 — trust lives in the artifact, not the gatekeeper —
   applied to provenance.
3. **The admission floor is operator DATA, never a constant in code.**
   A versioned policy file names it; an absent file means
   `unprovenanced`, which is today's behavior stated out loud rather
   than assumed. An unknown policy version or an unknown floor refuses.
   No floor lives in source, so every change to it is an operator edit
   — reviewable, greppable, attributable to a person.
4. **Below the floor, nothing is written.** A fetch whose admitted tier
   is under the floor refuses (`NIKA-REG-008`) AFTER verification and BEFORE the store,
   so a rejected artifact never lands on disk. A cache hit whose
   recorded tier is under the floor refuses identically: the policy
   changed over the cache, and **the cache does not grandfather**.
5. **The tier is recorded, and it is attested.** The cache record
   carries the tier beside the digest, and a hit re-tells the recorded
   truth — evidence is not re-sought on a hit, the record IS the
   evidence of what that fetch proved. The tier of every registry
   artifact a run consumes rises to the receipt: a run attests the
   provenance of what it consumed, not merely its hash.
6. **No inflation, and no retroactive upgrade.** A record naming a tier
   its evidence class cannot admit is treated as tampered. A later
   registry-side improvement rewrites nothing: re-fetch re-proves, and
   the receipt of the day tells the truth of the day.

## 4 · Machine surfaces (normative for discovery)

A conformant registry MUST serve, at stable paths:

- **`index.json`** — every entry with its pin, digest, cert summary and
  advisory ids, in one fetch. This is the resolution surface for tools
  and agents; it is a *convenience projection* — a client MUST verify
  against the entry + bytes, never against the index alone.
- **`llms.txt`** — the consume/verify path in agent-readable markdown
  (llmstxt.org form), including the warning that LLM-suggested names
  MUST be resolved against the index before any install (slopsquatting).

All projected surfaces (index, certificates, catalogs, badges) MUST be
regenerable from the entries and MUST be drift-gated in the registry's
CI — a derived surface that cannot be re-derived is treated as tampered.

## 5 · First-party projection (informative)

A registry that also *publishes* artifacts SHOULD derive those entries
from its canonical source rather than authoring them by hand. The
reference projects the spec's showcase pack via a pinned source commit
(`SPEC_PIN`) — the pin makes projection deterministic across machines,
and bumping it is a reviewed, deliberate act.

## 6 · Out of scope (v0.1)

Blob storage for heavy artifacts (models — pointers only today) · the
`nika add` client verb (engine ADR) · signature enforcement (the
`[signature]` block is reserved; verification semantics land in v0.2) ·
federation between indexes (a client MAY read several; cross-index
semantics are undefined in v0.1).

---

🦋 *Identity decentralized · discovery a thin forkable phonebook · trust
re-derivable in the artifact itself. The registry can be dumb because
the language is auditable.*
