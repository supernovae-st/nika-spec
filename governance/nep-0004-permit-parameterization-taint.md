# NEP-0004 · Permit-parameterization taint: untrusted values re-gate under permits

- **NEP**: 0004 (next free integer · 0001 reserved for the v1 surface · 0002 the trifecta gate · 0003 absent permits)
- **Title**: An untrusted value never reaches a permit bound, and reaches a permitted verb's argument only through the re-gate
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-22

## Abstract

NEP-0003 made the boundary fail-closed when the block is absent. This NEP
makes the boundary honest when the block is PRESENT but the values flowing
under it are attacker-controlled. Every value carries an integrity label
(Integ ∈ {trusted, untrusted}). An untrusted value that reaches a permit
BOUND (the host/glob/program literal inside `permits:`) is a hard refusal:
the boundary itself would be self-serve. An untrusted value that reaches a
permitted verb's ARGUMENT is re-gated: the engine canonicalizes the
RESOLVED value first, then matches it against the STEP's permit, and
refuses when the canonical form escapes. One explicit `declassify:`
declaration is the only door, and it lands in the receipt.

## Motivation

HF incident vector n°2: the static judge proves `Required ⊆ Declared` on
CATEGORIES (the file reads files, the file fetches hosts) while the
resolved VALUES escape the declared bound: a `datasets/**` read permit
serves `../../etc/passwd` when the path is caller-supplied, an `exec`
permit on `find` serves `find . --exec rm` when a flag is data, an
`api.example.com` fetch permit serves any host when the URL host is
interpolated. Literality (RS-28) already blocks data→permit-declaration at
the grammar level for literals; nothing blocks data→argument-under-permit.
The narrowing law and the IFC label model (RS-06) fuse here into ONE rule:
the permit must cover the resolved, canonical value, not the category.

## Specification

Definitions (normative · closed):

- **Integ label** · every value carries (Conf, Integ). Integ=trusted:
  literals, `const.*`, `secrets.*` (Conf high · masked, integrity intact),
  and pure-compute results over trusted inputs. Integ=untrusted: fetch and
  tool results (`nika:fetch`, MCP tools, any `invoke:` reaching the world),
  `inputs.*` (caller-supplied at launch), `config.*` (deployment-supplied,
  outside the file), and any `tasks.<id>.output`/interpolation derived from
  them. Propagation is monotone: one untrusted operand taints the whole
  interpolation.
- **PERMIT BOUND** · a host, glob, or program literal inside the `permits:`
  block. A bound MUST be a literal. Any interpolation reaching a bound is a
  hard refusal: there is nothing left to canonicalize against.
- **VERB ARGUMENT UNDER PERMIT** · an `args`/argv value of a verb whose
  CATEGORY the step's permit covers. The category being granted says
  nothing about the resolved value.
- **CANONICAL FORM** · per plane, computed on the RESOLVED value before any
  match: fs path → lexical normalization against the run base (`.`/`..`
  resolved, separators collapsed · the comparison is the canonical string
  against the declared glob, never a raw prefix); net host → lowercase,
  IDNA→punycode, trailing dot and default port stripped; exec argv → the
  program is argv[0], and re-entry-class tokens (`--exec`, `-c`, `eval`…)
  are never covered unless the permit lists them explicitly.
- **RE-GATE** · the act of matching the canonical resolved value against
  the STEP's permit (after task-level narrowing of the workflow block).
  When: statically at check for every value resolvable at check (literal,
  const, input with a default), and mandatorily at run, at interpolation
  resolution, before dispatch, for everything else.
- **DECLASSIFY** · the only door · RS-31. A task-level `declassify:` entry
  raises one binding from untrusted to trusted, authored, check-visible,
  and receipt-recorded (event `declassify` with the taint path, the
  `because:` text, and the value digest). Declassify lifts the TAINT law
  only: the value is then matched like a literal, so it still must sit
  inside the boundary. Robust-declass composition with the trifecta human
  gate (RS-06 · NEP-0002) is out of scope for v1.

The law (MUST/SHOULD):

1. An engine MUST refuse any interpolation source reaching a permit bound,
   at check when statically visible and before any token · `NIKA-AUTH-007`
   (new · security_error · check-time). The repair: declare the bound,
   gate the value in the body.
2. An engine MUST re-gate every untrusted value reaching a verb argument
   under a present permit: canonicalize the resolved value, match against
   the step's permit, refuse on escape · `NIKA-AUTH-008` at check when the
   value is resolvable there, `NIKA-SEC-004` at run otherwise (defense in
   depth · the provenance twin of NEP-0003 law 3).
3. A re-gate refusal MUST carry the taint path source-first (the 10 §
   secret-flow format) plus the canonical form and the bound it escaped.
4. An untrusted value NOT resolvable at check (no default) defers: the
   file stays valid, the runtime re-gate is mandatory, and the check
   report SHOULD list the deferred re-gates informationally.
5. A `declassify:` entry MUST name `from:` (one binding), `to: trusted`,
   and `because:` (non-empty justification); the receipt MUST record it
   with its evidence. It is the only mechanism that lifts the taint law;
   there is no implicit declassification in v1.
6. Trusted values change nothing: every effect, trusted or not, is matched
   against the declared boundary (LAW-AUTH-0307 · NEP-0003). Declassify is
   not a permit bypass.
7. Nothing changes syntactically: no new YAML field outside `declassify:`,
   no version marker. The grammar gains one optional task-level key.

Registry and prose touched:

- **LAW-AUTH-0325** is added to `canon/laws/authority.yaml` (status
  active) · the machine row of this law.
- `spec/10-authority.md` gains « The permit-parameterization taint
  (normative) » · `spec/01-envelope.md` §permits gains the one-line
  literal-bound pointer.
- `canon/diagnostics/registry.yaml` gains `NIKA-AUTH-007` +
  `NIKA-AUTH-008` (+ the `canon.yaml` error_codes items, re-rendered by
  the SSOT compiler).
- `schemas/workflow.schema.json` gains the optional task-level
  `declassify:` key (law 7 · the one grammar addition).
- Implementation surfaces: nika-tmpl (label propagation) · nika-check
  (static twin) · nika-runtime (the dispatch re-gate seam) · the receipt
  writer (the declassify event) · the reference oracle
  (conformance/deep_static.py).

## Conformance test

Eight fixture pairs ship with this NEP (NEP-0000: a Standards Track NEP
without a stateable test does not leave Discussion) · seven static,
continuing the NEP-0003 suite in `conformance/tests/core/authority/`,
plus one runtime pair. Engine/reference differential per LAW-AUTH-0319.

- `core/authority/007-untrusted-traversal-under-fs-read-refused` ·
  negative · `inputs.p` (untrusted, resolvable via its default)
  canonicalizes to `../../etc/passwd`, outside `fs.read: ["datasets/**"]`
  → `NIKA-AUTH-008` (law 2 · the category grant says nothing about the
  resolved value).
- `core/authority/008-untrusted-exec-reentry-flag-refused` · negative ·
  an untrusted argv tail token resolves to the re-entry class (`--exec`)
  under `exec: ["find"]` → `NIKA-AUTH-008` (law 2 + the exec canonical
  form · the program is covered, the re-entry token is not).
- `core/authority/009-untrusted-host-under-fetch-permit-refused` ·
  negative · the canonical host of the resolved URL
  (`evil.example.com`) escapes `net.http: ["api.example.com"]` →
  `NIKA-AUTH-008` (law 2).
- `core/authority/010-tainted-permit-bound-hard-refused` · negative · an
  interpolation reaches the bound itself (`net.http: ["${{ inputs.host }}"]`)
  → `NIKA-AUTH-007` (law 1 · the default even matches: irrelevant, the
  boundary would be self-serve).
- `core/authority/011-declassify-declared-opens-the-door` · positive · a
  task-level `declassify:` lifts the taint on `inputs.p`; the value is
  then matched like a literal and sits inside the declared boundary →
  valid (laws 5-6 · no permit bypass).
- `core/authority/012-trusted-value-passes` · positive · `const.p` is
  author-baked (Integ=trusted), the static match against `datasets/**`
  succeeds, no re-gate needed → valid (law 6).
- `core/authority/013-canonical-form-back-inside-boundary` · positive ·
  the RAW string `datasets/../datasets/q3.csv` spells `..` yet
  canonicalizes to `datasets/q3.csv`, inside the bound → valid (law 2 ·
  the canonicalize-first pivot: a prefix matcher false-positives here
  while 007, the true escape, shares the same prefix shape).
- `runtime/permits/004-untrusted-arg-runtime-regate` · negative ·
  caller-supplied at launch, no default: the static twin DEFERS (law 4),
  the run re-gate canonicalizes the resolved value and the escape fails
  the task `NIKA-SEC-004` (laws 2+4 · defense in depth, the NEP-0003
  law 3 provenance).

The reference oracle (conformance/deep_static.py) ships the static twin
with this NEP: law 1 (the 010 class) and law 2 (the 007/008/009/013
classes) are judged at check, source-first taint path in the detail. The
run-time re-gate and the receipt `declassify` event land with the engine
flip (F-O1 PR-2/3); the runtime pair states the contract ahead of it, in
the reserved runtime tier (runner-protocol).

## Compatibility impact

NOT additive for the files the HF vector targets · additive for every
honest file. A workflow that interpolates caller/tool data into a
permitted verb's argument turns red at check ONLY when the resolvable
value escapes the bound; dynamic cases defer to the run. Census of the
spec corpus at 2026-07-22 (derived · the re-gate surface): every file
carrying a present `permits:` block with an `inputs.*`/`config.*`
reference in a verb argument resolves NONE of them at check (no defaults)
· zero existing file flips; the law binds new authoring and the
adversarial suite, never the shipped corpus.

## Migration plan

**What changes for you.** A workflow that feeds caller-, config-, or
tool-produced data into a permitted verb's argument is now re-gated
against the STEP's permit, on the canonical resolved value. Two errors
teach the law:

```
error[NIKA-AUTH-008]: task `load` passes an untrusted value that escapes the step permit
  · taint path: inputs.p -> args.path (nika:read)
  · resolved (default): "../../etc/passwd" -> canonical "/etc/passwd" ∉ fs.read ["datasets/**"]
  · fix: keep the value inside the boundary · or declare declassify: on the task (the only door)

error[NIKA-AUTH-007]: permit bound `net.http[0]` is interpolated, not literal
  · a bound is the wall itself: declare the host/glob/program, gate the data in the body
  · fix: write the literal bound (net: { http: ["api.example.com"] }) and let the re-gate check the value
```

**How to declare the door.** When the value is legitimately outside the
author's control (a deployment-controlled vendor path, a reviewed caller
contract), declare it on the consuming task:

```yaml
tasks:
  load:
    invoke:
      tool: nika:read
      args: { path: "${{ inputs.p }}" }
    declassify:
      - from: inputs.p
        to: trusted
        because: "vendor inventory path, deployment-controlled, reviewed at release time"
```

The declaration is check-visible, greppable, and recorded in the run
receipt (event `declassify` · taint path · because · value digest). It
lifts the taint law only: the value is still matched against the declared
boundary, so `declassify:` never widens the permit. Values that stay
dynamic (no default) keep the file green at check and are re-gated at run;
`nika check` lists the deferred re-gates so CI sees the attack surface
before launch. Nothing else changes: the verbs, the boundary grammar, and
the `nika: v1` marker are untouched.

## Rejected alternatives

- **One code for both classes** · rejected: two repairs (make the bound a
  literal vs narrow/declassify the value) · the NEP-0003 argument on
  NIKA-SEC-004 applies verbatim.
- **Refuse every unresolvable untrusted argument at check** · rejected as
  the default: it makes every legitimate parameterized workflow
  (`${{ inputs.p }}` under a declared bound) unwritable without declassify.
  Deferral + mandatory runtime re-gate keeps judged = executed (invariant
  4) because the run CANNOT skip the re-gate.
- **Raw string-prefix matching** · rejected: `datasets/../datasets/x` and
  `datasets/../../etc/passwd` share a prefix; only the canonical form
  separates them (fixtures 007 vs 013).
- **Implicit trust for `config.*`** · rejected: the deployment is outside
  the file; the file IS the blast radius, it cannot vouch for what it does
  not contain. (Operator question 1 confirms.)
- **A `declassify` interpolation filter** (`${{ x | declassify }}`) ·
  rejected: invisible at review distance, splits the audit trail; the
  block form is one obvious way, greppable, receipt-bound.
