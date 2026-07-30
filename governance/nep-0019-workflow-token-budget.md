# NEP-0019 · The workflow token budget — the portable cap leaves the agent verb

- **NEP**: 0019
- **Title**: Generalize the one normative in-language cap (`max_tokens_total`) from the `agent:` verb to the workflow, in the only unit that survives the freeze
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-30

## Abstract

Today the language carries exactly one normative spend cap:
`agent.max_tokens_total` ([02 §agent](../spec/02-verbs.md)) — and it is
confined to one verb of four. This NEP proposes the workflow-level twin:
a declared, statically-checkable token budget the whole run must fit
inside, refusable at check when the static ceiling already exceeds it.
**Tokens, never currency**: a dollar cap in a durable file rots with
every price change and is meaningless on a local provider, while a token
cap is portable across providers, hardware and years — money stays what
it already is in the engine, a *projection* of tokens through the
versioned pricing snapshot the trace pins (NEP-0017). This closes the
gap [08 §H7](../spec/08-out-of-scope.md) names (« reading IS
in-language · enforcement is NOT ») in the one unit that deserves to be
normative — the deferred `budget: max_cost_usd` block stays deferred,
and stays denominated in the wrong unit.

## Motivation

1. **The product promise is a bounded run; the standard promises
   nothing.** `nika check` renders cost floors and ceilings, but a
   third-party engine can claim conformance without counting anything.
   The audit-before-run story deserves at least one normative,
   verifiable cap at the workflow boundary.
2. **The right unit already won, locally.** `max_tokens_total` is
   normative today — but only inside `agent:`. An `infer:`-only
   workflow, the majority shape, has no in-language spend bound at all.
3. **The resource doctrine says the dimensionless invariant must
   lead** (the resource-algebra ratification, 2026-07-28): tokens
   compose additively under both `;` and `‖`, need no exchange rate,
   and are the denominator money and energy are projected from.

## Specification (sketch — the Discussion shapes the final grammar)

- A workflow-level declaration, e.g. under the existing `policy:`
  surface (`policy.limits.max_tokens_total: <integer>`), judged HARD at
  check: if the static token ceiling of the plan (the same arithmetic
  the COST rung already performs · `Σ max_tokens × max_attempts` per
  task, iterations counted) provably exceeds the budget, check refuses
  with a taught error; otherwise the run enforces it cumulatively and a
  breach terminates with the budget error code.
- UNBOUNDED stays honest: a plan whose ceiling cannot be bounded
  statically (dynamic fan-out) is not refused for the budget alone —
  the check names the unbounded contributor, and the runtime cap still
  binds (defense in depth, the NEP-0003 shape).
- `agent.max_tokens_total` is unchanged and nests: the verb cap bounds
  its task, the workflow cap bounds the sum (limits MEET · budgets
  escrow — the composition ruling).
- Error family: the existing budget namespace; exact codes assigned at
  Accepted.

## Compatibility

Purely additive. No existing workflow changes meaning; absence of the
field means today's behavior. The deferred `budget:` block of
[08 §Cost tracking annotations](../spec/08-out-of-scope.md) is
superseded-in-direction by this token-denominated form if accepted —
the currency-denominated cap stays out of the language.

## Open questions (for Discussion)

- Home: `policy.limits` (judged, closed vocabulary today:
  `max_tasks`) vs a sibling — the one-obvious-way call.
- Does the cap cover `infer` + `agent` only, or also tokenized tool
  surfaces (`nika:jq` is free; MCP tools are not tokens)?
- Conformance: one fixture pair minimum (a provable over-budget refusal
  · a boundary pass), runtime fixtures for the cumulative breach.
