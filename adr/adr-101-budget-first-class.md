---
id: ADR-101
title: "budget: first-class — declarative cost caps · statically aggregated"
status: proposed
date: 2026-07-05
phase: ""
deciders: ["@ThibautMelen"]
tags: [budget, cost, static-check, affine, v0.2-seed]
affects_crates: [nika-schema, nika-cli, nika-runtime, nika-verb-infer]
affects_layers: [L0, L2, L4]
supersedes: []
superseded_by: []
related: [ADR-092, ADR-088]
requires: []
enables: []
amends: []
fci: []
inv: []
shadow_zones: []
nika_codes: [NIKA-BUDGET-001, NIKA-BUDGET-002]
timeline: ""
follow_ups: ["flip the engine forward-compat test future_clause_budget_rejects_cleanly to a positive parse", "promote spec/08 H7 PARTIAL → in-language"]
---

> **Status · DRAFT-PROPOSAL (overnight 2026-07-05) · NOT canon until operator lock.**

# ADR-101 · `budget:` first-class

## Context

The spec pre-announced this: 08-out-of-scope §Cost tracking annotations
sketches a `budget:` block and defers enforcement to v0.2 (H7 · PARTIAL —
reading ships via `nika:inspect view: cost`, the only normative in-language
cap today is the `agent:` verb's `max_turns`/`max_tokens_total`).

The research closed the case for promotion. arXiv:2606.04056 (Token
Budgets · June 2026) catalogues **63 production budget-overrun incidents
across 21 frameworks (2023-2026)** and names cause #1: *no declarative
budget primitive* — every framework leaves caps to imperative wrapper code.
No competing spec ships one. `nika check` already prints a cost FLOOR and
flags UNBOUNDED tasks as hints; the clause turns that report into a
contract.

The 2040 rationale: when agents author workflows and humans approve them,
the surviving value of the language is **accountability** — resource
sovereignty is its first pillar. Money outlives token economics; the unit
system must too.

## Decision

A `budget:` block at BOTH workflow level and task level ·

```yaml
budget: { usd: 0.50, tokens: 200000 }   # workflow-level · both optional
tasks:
  - id: research
    budget: { usd: 0.10 }               # task-level · the tighter bound wins
    infer: { prompt: "..." }
```

- Units v0.2 · `usd` + `tokens`. The unit set is OPEN (additive · a future
  `joules`/`seconds` is a minor) — engines MUST reject unknown units at
  parse (strict) so a typo never silently uncaps.
- Inheritance · task caps nest under the workflow cap; the most
  restrictive applicable bound governs. `agent:` verb budgets
  (`max_turns` · `max_tokens_total`) remain and count TOWARD the task cap.
- **Static semantics (the differentiator)** · `nika check` aggregates
  bottom-up: a task with no computable ceiling (no `max_tokens` · no
  budget) under a budgeted workflow is a check ERROR (today's UNBOUNDED
  hint hardens only in that scope — unbudgeted workflows keep the hint).
- Runtime semantics · crossing a cap fails the task with `NIKA-BUDGET-001`
  (category `budget_error` · already in the canon enum) · the workflow
  policy then applies (`on_error:` composes — a budget failure is
  retryable only onto a DIFFERENT bound, so plain `retry:` on the same
  exhausted cap short-circuits as `NIKA-BUDGET-002`).
- Composition · `retry:` attempts SPEND from the same task budget (an
  attempt is not free) · `for_each:` iterations share the task budget.

## Engine appendix (non-normative)

The Rust blueprint per 2606.04056: an AFFINE `Budget` type — `spend()` /
`split()` / `merge()` consume `self`, no `Clone` — a double-spend is a
compile error, not a runtime audit.

## Consequences

- The 08-out-of-scope H7 row flips PARTIAL → in-language on lock.
- The engine forward-compat anchor (`future_clause_budget_rejects_cleanly`
  · nika#156) flips to a positive parse when this ships.
- `nika check` output gains a hard-ceiling line where today it prints
  UNBOUNDED hints.
