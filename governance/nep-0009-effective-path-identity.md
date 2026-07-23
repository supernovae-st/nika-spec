# NEP-0009 · A path grant names an effective path identity, re-judged at dispatch

- **NEP**: 0009 (next free integer · 0001 reserved for the v1 surface · 0002 the trifecta gate · 0003 absent permits · 0004 the parameterization taint · 0005 the environment permit · 0006 the data-as-code sink · 0007 the trace and the equivalence oracle · 0008 the egress projection)
- **Title**: A path grant names an effective path identity, re-judged at dispatch — escape is refused, never rewritten, on every enforcement arm
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-23

## Abstract

NEP-0003 decided WHAT the boundary grants; NEP-0008 projected that
judgment onto network egress. This NEP closes the same class on the
filesystem arm: a sandbox mount projection that follows a source symlink
at mount time mounts the TARGET, not the judged path — so a `fs.read` /
`fs.write` entry is re-judged at dispatch as an **effective path
identity** (longest existing ancestor canonicalized, the not-yet-existing
tail carried lexically). An identity that escapes the declared set is
refused before spawn and attested in the run journal — never silently
rewritten, and with the same verdict on every enforcement arm.

## Motivation

The mount-time symlink follow is a demonstrated hole, not a theory. On
the mount-projection arm (bubblewrap), a task with `fs.write:
[/workspace]` can replace `/workspace/data` with a symlink to
`$HOME/.ssh`; a later task's `fs.read: [/workspace/data]` is projected as
a literal bind, and mount(2) follows the source — the jail reads outside
the judged tree, and neither the check nor the journal names it. The
kernel path-walk arm (seatbelt) refuses the same access at open. The
class is industrial (flatpak `--persist`, CVE-2024-42472 · GHSA-7hgv-f2j8-xw87):
the reference fix is refusal of the symlinked bind source, completed by
an fd-pinned mount; the silent canonical-rewrite alternative (the
firejail practice) would mount a path the judgment never named.

The contract system calls this invariant 4 — judged = executed =
attested. A mount that follows a symlink breaks the equation three ways
at once: the executed path is not the judged one, the journal records
the judged string, and the two platform arms diverge. The boundary the
author declared must be the boundary the kernel enforces, on every arm.

## Specification

The law (MUST):

1. **Re-judgment at dispatch.** Before any sandbox projection of an
   `fs.read` / `fs.write` grant, the engine resolves the grant's literal
   prefix to its effective form — the longest existing ancestor
   canonicalized, the not-yet-existing tail carried lexically — and
   tests the identity against the declared set (descendancy, both sides
   canonical).
2. **Escape = refusal, never rewrite.** An identity that escapes the
   declared set is refused before spawn (`NIKA-SEC-004` class). The
   engine MUST NOT mount the resolved target under the judged name, and
   MUST NOT rewrite the grant to the canonical form: the receipt never
   lies.
3. **Attestation.** The refusal is attested in the run journal as
   `fs.path_mismatch`, carrying the judged prefix and the resolved
   target.
4. **Platform parity.** The same verdict holds on every enforcement arm
   (kernel path-walk and mount-projection alike); the conformance pair
   asserts both. A static lint SHOULD name a literal grant that
   traverses a symlink at check time, but the lint is never the wall —
   the planted symlink is a run-time fact.
5. **Not-yet-existing writes stay legal.** A write grant whose target
   does not exist is judged on its longest existing ancestor; creation
   under a healthy ancestor is admitted.
6. **The residual is declared.** A parallel task of the same run
   swapping the symlink between the dispatch re-gate and the mount is a
   documented residual window; the fd-pin projection (`--bind-fd`,
   bwrap ≥ 0.10.0, or the O_PATH equivalent) closes it as a named
   follow-on.

## Rationale

- **Refusal over rewrite.** The canonical-rewrite alternative admits the
  couple (link, target) silently: the journal would read « judged X »
  while mounting Y. A contract whose receipt misstates the executed
  authority is worse than no receipt. Refusal keeps one honest sentence:
  judged = mounted = attested.
- **Dispatch over check.** The planted symlink does not exist at check
  time; a static-only law would be security theatre. The dispatch is the
  grant's open time — the one moment the effective identity can be
  judged against the live filesystem before any mount happens.
- **One helper, both arms.** Extending the re-gate to the kernel
  path-walk arm (which already refuses at open) buys symmetry and an
  earlier, attested refusal from the same code path — the arms stop
  diverging in what they admit, not only in where they refuse.
- **fd-pin deferred, named.** The fd-pinned mount closes the parallel
  race but costs a version probe and a new spawn seam; shipping the
  re-gate first kills the demonstrated (sequenced) pivot at 100 % while
  the residual is honestly on the record.

## Backwards Compatibility

A workflow whose grant legitimately traverses a symlink (e.g. a
`/tmp`-adjacent or nix-store path declared by its link) changes verdict:
the grant must now be declared by its effective path. This is the same
shape the flatpak fix chose (a symlinked bind source is ignored with a
warning, never followed). Grants over non-symlinked trees are untouched;
not-yet-existing write targets stay legal by law 5.

## Reference Implementation

- The engine lane (`feat/h2-symlink-regate`): the dispatch re-gate
  (fail-closed, one call site), the `fs.path_mismatch` journal event,
  the check-side symlink lint (WARN-class, non-load-bearing), and the
  fixtures — the planted-pivot PoC refused before spawn (zero bytes
  read, zero exec event), the not-yet-existing write admitted, the
  platform-parity pair in the CI matrix.
- The residual window and the fd-pin follow-on are carried in the
  engine's inline documentation next to the re-gate.

## Deferred (named follow-ons)

- **fd-pinned mounts** (`--bind-fd` / O_PATH · bwrap ≥ 0.10.0 or the
  distro backport): closes the parallel-swap window; introduces a
  version floor question (fail-closed vs documented fallback) decided
  with the follow-on, not here.
- **The landlock-LSM arm**: inherits the re-gate for free (it lives at
  the projection layer above it).

## Copyright

This document is placed in the public domain under CC0-1.0, as every NEP.
