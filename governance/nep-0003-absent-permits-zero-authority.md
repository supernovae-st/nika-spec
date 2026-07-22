# NEP-0003 · Absent permits: means zero authority (fail-closed)

- **NEP**: 0003 (next free integer · 0001 reserved for the v1 surface · 0002 the trifecta gate)
- **Title**: An absent `permits:` block declares zero authority, in every mode
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-22

## Abstract

Today a workflow with no `permits:` block runs bounded only by the engine
floor: the file carries no authority, so the constitution's first clause
(zero ambient authority) is true only for annotated files. This NEP gives
the absence one meaning everywhere: an absent `permits:` block IS
`permits: {}` · DeclaredPermits := ∅ · every required effect is a check
refusal, at every profile, for every file including composed children. A
pure-compute workflow needs no block; anything that touches the world
declares it.

## Motivation

The engine's own comment names the hole: « no `permits` declared · the
runner floor is the only gate » (nika-runtime/src/dispatch.rs). The checker
proves it: a parent without permits contains nothing, so a child
`exec: rm -rf` passes with zero finding (test
`undeclared_parent_boundary_is_no_wall`), and the reference oracle spells
the same reading (« absent block = today's behavior · everything granted »,
conformance/composition_core.py). The spec prose promises default-deny
while the composition test asserts no-wall: the constitution is
structurally empty for every non-annotated file. Census at 2026-07-22: 226
of 409 spec-repo workflows, 31 of 73 engine workflows, 6 of 11 playground
workflows carry effects with no block · every one is an undeclared blast
radius.

## Specification

One sentence: **an absent `permits:` block means DeclaredPermits := ∅**
(provenance: absent), in draft and published profiles alike, for top-level
and composed workflows alike.

Definitions (normative · closed):

- **ABSENT** · the `permits:` key does not appear in the envelope, or
  appears with a YAML null value. Semantics: DeclaredPermits := ∅. (A null
  spelling is refused with a prescriptive detail pointing at the explicit
  forms · one obvious way.)
- **EMPTY** · `permits: {}` (the explicit empty mapping). Semantics:
  DeclaredPermits := ∅, provenance: declared. The legal spelling of
  « I touch nothing ».
- **PARTIAL** · some categories listed. Semantics unchanged: listed =
  granted, omitted categories default-deny (01 §permits, untouched).

The law (MUST/SHOULD):

1. An engine MUST judge `Required ⊆ Declared` with Declared := ∅ whenever
   the block is ABSENT. Any non-empty Required is a check refusal · before
   any token.
2. The refusal MUST be `NIKA-AUTH-006` (new · security_error · check-time),
   distinct from `NIKA-SEC-004` (escape under a PRESENT block): the repair
   differs (add a block vs extend one), and the diagnostic carries the
   inferred block inline, ready to paste.
3. At run time any effect attempted under an absent block MUST fail the
   task (`NIKA-SEC-004`, security_error, never fed back to an agent:
   model) · defense in depth for the dynamic cases the static judge cannot
   see (a host computed at run time).
4. A workflow whose Required is ∅ (pure compute: infer without tools ·
   CEL · pure/internal builtins per the builtin classification table) with
   an absent block MUST pass check; the report SHOULD carry an
   informational hint naming `permits: {}` as the explicit form.
5. Composition: an absent block on a PARENT means Authority(parent) := ∅;
   any child whose inferred effect boundary is non-empty violates
   `NIKA-COMP-002` at check, `NIKA-SEC-004` at run. The « no wall »
   reading is dead: absent IS a wall, the zero wall.
6. An absent block on a CHILD invoked via `workflow:` means the child's
   own Declared := ∅; the parent's grants never flow down implicitly
   (containment is monotone · inter = child). A child that touches the
   world MUST declare it, in its own file.
7. Nothing changes syntactically: the grammar keeps `permits:` optional
   (LAW-AUTH-0320 · no new YAML field, no version marker). The change is
   semantic only.

Registry and prose touched:

- **LAW-AUTH-0324** is added to `canon/laws/authority.yaml` (status
  active) · the machine row of this law.
- **LAW-AUTH-0306** (draft: absent ⇒ DeclaredPermits := RequiredCapabilities
  · provenance inferred) is tombstoned (status retired · replaced_by
  LAW-AUTH-0324): the grant equaling whatever the body happens to require
  is the ambient floor wearing an inference costume.
- **LAW-AUTH-0307** (published: explicit block required even empty ·
  `NIKA-AUTH-002`) is untouched and stands strictly stronger than the
  floor this NEP sets.
- `spec/01-envelope.md` §permits « optional and non-breaking … runs
  exactly as today » is replaced by the law above.
- Implementation surfaces: nika-check (the `NIKA-AUTH-006` finding) ·
  nika-runtime (the run-time refusal) · nika-cli (`--fix` grows an
  insert-permits arm) · the reference oracle (conformance/deep_static.py
  + composition_core.py).

## Conformance test

Seven fixture pairs ship with this NEP (NEP-0000: a Standards Track NEP
without a stateable test does not leave Discussion). New suite group
`conformance/tests/core/authority/` · the authority plane named by
canon/laws/authority.yaml · plus one runtime pair:

- `core/authority/001-absent-permits-pure-compute-clean` · positive ·
  absent block, pure compute → valid (law 4 · the report SHOULD hint
  `permits: {}`).
- `core/authority/002-absent-permits-fetch-refused` · negative ·
  `nika:fetch` under an absent block → `NIKA-AUTH-006` (laws 1-2).
- `core/authority/003-absent-permits-exec-refused` · negative · `exec:`
  under an absent block → `NIKA-AUTH-006` (law 1).
- `core/authority/004-absent-permits-fs-read-refused` · negative ·
  `nika:read` under an absent block → `NIKA-AUTH-006` (law 1).
- `core/authority/005-empty-permits-explicit-pure-clean` · positive ·
  `permits: {}` authored, pure compute → valid (the EMPTY definition).
- `core/authority/006-child-absent-under-permitted-parent` · negative ·
  a child with no block (running `exec:`) invoked by a permitted parent →
  `NIKA-COMP-002` (law 6 · the parent's grants never flow down).
- `runtime/permits/003-absent-permits-runtime-refusal` · negative · a
  fetch host templated `${{ inputs.url }}` under an absent block → task
  failure `NIKA-SEC-004` at run (law 3 · the dynamic case the static
  judge cannot see).

Engine/reference differential per LAW-AUTH-0319.

## Compatibility impact

NOT additive · this is the intended flip (flag-day, ratified 2026-07-22).
Census (derived · lane F-O8 inventory): spec repo 226 effect-carrying
files without a block (of 344 block-less, 409 total) · engine @origin/main
31 (of 42, 73) · playground 6 (of 7, 11). Every one turns red at check
until the block is added; pure-compute files (118 spec · 11 engine ·
1 playground) stay green. Surfaces checked: examples/ · templates/ ·
conformance/ · playground/ · the engine test corpus.

## Migration plan

**What changes for you.** A workflow that touches the world (reads or
writes a file, calls a host, runs a shell, invokes a tool) and carries no
`permits:` block now fails `nika check` before a single token is spent:

```
error[NIKA-AUTH-006]: task `load` requires fs outside the declared boundary
  · this file has no `permits:` block · absent means zero authority (NEP-0003)
  · add the inferred boundary (re-checks clean):
    permits:
      fs: { read: ["./data/**"] }
```

The repair is one command · `nika check --infer-permits` prints exactly
the block your workflow needs (paste it, the check passes; the block is
the same object the certificate names). During the transition window,
`nika check --suggest-permits` prints the suggestion without failing. A
workflow that touches nothing (pure compute) needs no block and stays
green; `permits: {}` is the authored spelling of « I touch nothing ».
Nothing else changes: the grammar, the verbs, and the `nika: v1` marker
are untouched.

Mechanics: the error is the teacher (`NIKA-AUTH-006` carries the inferred
block inline) · `nika check --infer-permits` already implements the
round-trip law · a codemod `permits-explicit-v1` (equivalence-or-stop ·
precedent: secrets-source-explicit-v1, LAW-AUTH-0321) inserts the inferred
block into every red file in the studio corpus BEFORE the checker flips;
the flip lands when the census of block-less effect-carrying files reaches
zero.

## Rejected alternatives

- **WARNING + zero-at-run** · rejected as the default: it leaves check
  green on effect-carrying files (judged ≠ executed · invariant 4), and CI
  that never runs stays blind. The soft variant survives only as the
  transition flag above (`--suggest-permits`).
- **Absent ⇒ inferred (LAW-AUTH-0306 draft mode)** · rejected: the file
  still carries no authored boundary; the grant equals whatever the body
  happens to require, which is the ambient floor wearing an inference
  costume. The constitution says the file IS the blast radius.
- **Child inherits the parent's block** · rejected: it breaks containment
  monotonicity (a permit-less child would silently wield the parent's
  grants) and makes the child's file unreadable alone.
- **Reuse `NIKA-SEC-004` for the absent-block refusal** · rejected: one
  code, two repairs (add a block vs extend one); the repair-loop converges
  slower and the certificate cannot tell the two provenances apart.
- **Grammar-level required `permits:`** · rejected: a pure-compute
  workflow must not be forced to annotate; the law is semantic (Declared
  := ∅), the grammar keeps the key optional (LAW-AUTH-0320).
