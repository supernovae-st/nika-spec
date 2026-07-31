# NEP-0020 · The affirmative-consent law — a refused confirm must not reach an effect

- **NEP**: 0020 (next free integer · 0001 reserved for the v1 surface · 0002 the trifecta gate · 0003 absent permits · 0004 the parameterization taint · 0005 the environment permit · 0006 the data-as-code sink · 0007 the trace and the equivalence oracle · 0008 the egress projection · 0009 the effective path identity · 0010 the run declaration · 0011 the run lifecycle · 0012 the receipt as untrusted input · 0013 the approval ticket · 0014 the thin-laws lot 3a · 0015 preview-commit · 0016 the provenance tiers · 0017 the thin-laws lot 3b · 0018 the energy honesty · 0019 the workflow token budget)
- **Title**: The affirmative-consent law — `false` triggers exactly zero effects, judged at check
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-31

## Abstract

A REFUSED confirm-mode `nika:prompt` settles the task **success with
value `false`** — the Deny lives in the approval attestation
(NEP-0013), never in the task status. Every route that does not consume
the answer therefore passes the effect through. This NEP makes that a
check-time refusal: an egress-capable task reachable from a confirm
gate over a route no affirmative gate closes is **`NIKA-SEC-014`**
(`security_error` · before any token). The advisory hint of 2026-07-30
escalates to the law it was measuring.

## Motivation

The 2026-07-30 UX audit (P0-2) measured the hole on the house's own
corpus: a confirm whose `default:` answers `false` unattended, followed
by `after: { ask: success }` into an irreversible `exec:` — the refusal
settles `success`, the edge admits it, the push fires. The author wrote
a gate; the file contains a rubber stamp. Two of this repo's own
examples were exactly this defect (`release-notes` · `pr-review-fanout`
— both repaired in this PR, which is the census). A gate that cannot
block is worse than no gate: it spends the reviewer's trust and returns
nothing. The hint named the defect; a hint is a plea, and the audit's
closure condition is a refusal — *false déclenche exactement zéro
effet*.

## Specification

### The law

For every confirm-mode human gate — an `invoke:` of `nika:prompt` whose
`mode:` is absent (the runtime default) or the literal `confirm` — and
every **egress-capable** task (the ONE effect table: `exec:` · a net or
fs-**write** builtin · `mcp:*` · an `agent:` whose whitelist admits an
egress tool), judged over the derived graph every judge reads
([03](../spec/03-dag.md)): **every route from the gate to the task must
be closed.** A route is closed by —

1. an **affirmative gate**: a `when:` that evaluates to FALSE under the
   refusal substitution (below) — the house pattern
   `with: { go: "${{ tasks.ask.output }}" }` + `when: ${{ with.go == true }}`;
2. `when: false` — the documented never-pattern: no route THROUGH the
   task carries the refusal anywhere;
3. a **closer confirm gate** — the nearest gate owns its closure (the
   approval-batch precedent, NEP-0013 law 3): the walk stops, and the
   bare route past the second gate is the second gate's own obligation.

An egress-capable task reached on a route closed by none of these is
**`NIKA-SEC-014`** (`security_error` · check-time · the diagnostic names
the gate AND the sink and teaches the affirmative pattern).

### The refusal substitution (normative · the decidable fragment)

The gate's settled facts under a refusal are substituted into each
`when:` on the route: `tasks.<gate>.output` → `false` ·
`tasks.<gate>.status` → `"success"` (a refusal settles success — a
status read is NOT consent, and is decidable exactly). The expression
is evaluated in Kleene-3 over the consent fragment (boolean literals ·
`==`/`!=`/`in` on resolved literals · `!`/`&&`/`||`/ternary · the exact
single-island `with:` binding carries its target's value):

- **FALSE** — the gate closes the route (affirmative).
- **TRUE** — the gate is PROVEN open under the refusal
  (`go == true || go == false` blocks nothing): the route stands.
- **Unknown** — the gate cannot be decided statically: a nested
  template binding (`"go: ${{ tasks.ask.output }}"` inside a larger
  string), an expression beyond the fragment. The route is NOT a
  refusal — the defect is unproven, and an unproven defect is the
  advisory hint's ground, never a code's (**sound: no false red**).

A task with no `when:` forwards the refusal by construction. A `when:`
that never reads the answer (directly or through a binding) and cannot
be proven false under the substitution is Unknown, not affirmative —
mere adjacency to a gate is not consent.

`mode: choice` is out of scope: its answer is a string, the affirmative
pattern differs, and the lane claims nothing there (silence, never
wrong).

### The code

`NIKA-SEC-014` joins the SEC family (the check-plane security refusals
· SEC-009 the trifecta · SEC-012 the write-write law · SEC-013 the
endorsement mode) — registry row in `canon/diagnostics/registry.yaml`,
summary row in [05 §the error table](../spec/05-errors.md), normative
prose in [10 §the affirmative-consent law](../spec/10-authority.md).
Not POLICY: the law binds with or without a `policy:` block, and
`NIKA-POLICY-001` is reserved to violations OF a declared `policy:`
rule.

## Conformance test

Three fixtures land with this NEP in `conformance/tests/core/policy/`
(the human-gate family) —

- `011-consent-bare-after-refused` — confirm + bare
  `after: { ask: success }` into an `exec:` → `NIKA-SEC-014`.
- `012-consent-affirmative-clean` — the human-gated-ship pattern →
  valid (whole-spec legal: the affirmative gate closes the one route).
- `013-consent-status-gate-is-not-consent` — a `when:` reading
  `tasks.ask.status` instead of the answer → `NIKA-SEC-014` (the status
  provably reads `"success"` on the refusal; nothing consumed).

The reference oracle (`conformance/deep_static.py`) implements the same
walk, so the fixtures bind both oracles.

## Compatibility impact

Not none, and argued: a workflow that was GREEN with a confirm gate and
a **provably** non-affirmative route to an effect now refuses at check.
The census is this repo: every `examples/` and `templates/` file was
validated — exactly two carried the defect (`release-notes` ·
`pr-review-fanout`), both repaired to the affirmative pattern in this
PR; the rest already consume the answer (`invoice-chaser` ·
`ceo-monday-brief` · `incident-war-room` · `release-train` ·
`human-gated-ship` · `etl-state`). Workflows the substitution cannot
decide see the same advisory hint as before — the escalation changes
verdicts only where the defect is proven.

## Migration plan

The repair is mechanical and the diagnostic teaches it verbatim: bind
the answer (`with: { go: "${{ tasks.<gate>.output }}" }`) and gate on
it (`when: ${{ with.go == true }}`). The codemod is the author's one
line pair per route root; the teaching string names both the gate and
the sink.

## Rejected alternatives

- **`NIKA-POLICY-002`.** The POLICY family judges violations of a
  DECLARED `policy:` block; this law binds without one. A second policy
  code would also mint the first family with two members for one
  sentence — the SEC family is where check-plane security laws live.
- **Keep the hint, never refuse.** The audit's closure condition is
  blocking; a hint is measurable ignorance, and the measured defect
  class is a rubber-stamp gate on irreversible effects.
- **Refuse on undecidable gates too.** Unsound: a gate the fragment
  cannot evaluate may well close the route (a nested binding carrying
  the answer into a comparison). A false red on a correct file teaches
  authors to dismiss the code — the Unknown case stays advisory,
  forever.
- **Judge at run, not check.** The run already records the Deny
  (NEP-0013); the defect is static (the route's shape, not the answer's
  value) and the spec's standing promise is judgment before any token.
