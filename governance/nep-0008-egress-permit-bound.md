# NEP-0008 · The sandboxed egress proxy is the permit's exact projection

- **NEP**: 0008 (next free integer · 0001 reserved for the v1 surface · 0002 the trifecta gate · 0003 absent permits · 0004 the parameterization taint · 0005 the environment permit · 0006 the data-as-code sink · 0007 the trace and the equivalence oracle)
- **Title**: The sandboxed egress proxy is the exact projection of `permits.net.http` — exact-host allowlists, proxy-side DNS, a normative port floor, one allowlist per run, and no dead grants
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-23

## Abstract

NEP-0003 through NEP-0006 hardened WHAT the boundary refuses; NEP-0007
made the refusal attributable. This NEP hardens the network egress of the
sandboxed `exec` step: the loopback egress proxy the engine spawns for a
`net.http` allowlist IS the permit, projected — nothing more may pass,
nothing declared may silently fail. Five laws make the projection exact:
the allowlist is exact-host (the `*.` glob is refused at check), DNS is
resolved by the proxy and never by the client, the dangerous-port floor
rides beneath every permit, one run carries one allowlist, and a
floor-blocked entry is a dead grant flagged at check. The proxy stays
TLS-blind by design: it observes the CONNECT authority and byte counts,
never the content — and it journals every verdict.

## Motivation

The wildcard is the measured attack surface, not a convenience. The 2026
sandbox-egress incident record (the srt network-allowlist bypasses · « one
outside report is luck, two is implementation ») shows the `*.` grant
delegating the permit to the zone operator: `*.github.io` is every tenant
of a shared-hosting zone, including an attacker's. A contract whose
effective authority depends on who else lives in the zone is ambient
authority — the exact property the contract system exists to eliminate
(invariant 1 · zero ambient authority). The bare `*` remains legal as the
explicit, visible, non-stealthy escape (`NetPolicy::Allow`); what dies is
the stealthy middle.

Second, the engine's DNS-rebinding fix (per-address floor check inside
the dial loop · no resolve-then-connect window) shipped as a stopgap:
the code said yes while the module doc still documented the hole as
accepted and the spec's « DNS-rebinding stays covered » sentence did not
name the exec arm. This NEP turns the stopgap into law — a divergence
between doc and code is a finding, never a stable state.

Third, dead grants. An exact entry naming a floor-blocked target (cloud
metadata, RFC1918, link-local, CGN) can never take effect — the floor
refuses it at dial — yet nothing flagged it at check: the contract lied
by omission. NEP-0005 established the dead-grant teaching for the env
plane (`NIKA-AUTH-009`); this NEP applies it to the net plane
(`NIKA-AUTH-011`).

## Specification

The law (MUST):

1. **Exact-host allowlists.** Every `permits.net.http` entry is an exact
   host name or literal. An entry carrying a `*` in any position other
   than the whole bare-`*` entry is refused at check
   (`NIKA-AUTH-010` · `security_error`). The bare `*` stays legal and
   keeps its meaning (explicit full egress, `NetPolicy::Allow`).
2. **Proxy-side DNS.** Under a `net.http` allowlist, the confined
   client's own resolver fails closed (the OS fence refuses it); the
   proxy resolves and re-checks EVERY resolved address against the SSRF
   floor inside the dial loop. A permitted name resolving to a blocked
   address refuses at dial (`NIKA-SEC-005`) — there is no
   resolve-then-connect window.
3. **The port floor is normative.** The engine's dangerous-egress-port
   denylist applies beneath every permit; no permit overrides it.
4. **One run, one allowlist.** A run projecting two distinct `net.http`
   sets refuses fail-closed at the second projection
   (`conflicting_boundary`). There is no ambient merge of egress
   boundaries inside one run.
5. **No dead grants.** An exact entry naming a private / link-local /
   CGN / metadata / otherwise non-public address is an inert dead grant,
   refused at check under the floor parity (`NIKA-SEC-005` — the engine
   has enforced this class since the floor parity pass; this NEP graves
   the rule in the spec text and adds the reference-oracle mirror and
   fixture). The only declassifiable target stays the exact loopback
   literal (01-envelope §exact-loopback declassification · the closed
   vocabulary: bare `localhost`, a `127/8` literal, `::1`).
6. **Attestation.** The proxy journals every verdict — allowed, refused,
   and relayed byte counts per connection — through the run journal's
   egress observer events. The proxy is TLS-blind: content is never
   observed, terminated, or injected (a voluntary MITM is REFUSED as an
   architecture).

## Rationale

- **Exact-host over bounded-globs.** A maintained denylist of shared
  zones (`*.github.io`, `*.workers.dev`, …) is perpetual debt and can
  never be complete. Refusing the glob form is total and measured free:
  a full sweep of the tracked fixture corpus found zero `*.` usage in
  `net.http` (0/73 files at the decision date). Re-admission, if ever
  needed, comes through a future NEP with a lint — never silently.
- **Proxy-side DNS over client-side filtering.** Checking the name
  statically and resolving at the client leaves the rebinding window
  (the name resolves differently at dial). Checking each resolved
  address inside the dial loop closes the window without trusting the
  client's resolver at all — the fence makes the confined client's DNS
  fail-closed, so the proxy is the only resolver by construction.
- **TLS-blind as a feature.** The voluntary-MITM alternative (terminating
  TLS at the proxy to inspect content) would put the engine in the
  content path, expand the TCB with a root-of-trust installation, and
  break certificate pinning. The blind proxy keeps the honest envelope:
  host, port, byte counts — which is exactly what the receipt may claim.
- **One allowlist per run.** Keying proxies per boundary set is
  mechanically simple but multiplies the enforcement surfaces a reviewer
  must hold in their head; the single boundary keeps the projection
  auditable. A composition need (two tasks, two sets) is served by two
  runs — or by a future NEP.

## Backwards Compatibility

Breaking by design, measured empty: the `*.` form in `net.http` was
accepted before this NEP and is now refused at check. The tracked
fixture corpus (73 files) and the pack templates carried zero such
entries at the decision date. Authors depending on a glob move to exact
host lists, or to the explicit bare `*` where full egress is genuinely
intended.

## Reference Implementation

- The engine lane (`feat/f-p5-egress-permit-bound`): the check finding
  (`NIKA-AUTH-010` wildcard refusal), the proxy metering events (relayed
  byte counts), and the module-doc truth (the rebinding refusal is law,
  not an accepted limit). The dead-grant class (law 5) already rides the
  floor parity (`NIKA-SEC-005`) and stays untouched.
- Conformance fixtures: `tests/core/authority/025-net-http-wildcard-refused`
  (`NIKA-AUTH-010`) and `tests/core/authority/026-net-dead-grant-floor-blocked`
  (`NIKA-SEC-005`), with the reference oracle mirroring both laws.

## Deferred (P2, by decision)

- Port sets in the permit form (`{host, ports}`) and a distinct
  `net.tcp` dimension — the port floor (law 3) suffices for v1.
- The credential-injection proxy mode (reverse-proxy TLS origination with
  keyring-held credentials and session tokens · the nono Mode-2 pattern) —
  a second proxy, not a hardening of this one; the plain-HTTP `405` seam
  is the documented attachment point.
- Per-set keyed egress proxies (the composition escape from law 4).

## Copyright

This document is placed in the public domain under CC0-1.0, as every NEP.
