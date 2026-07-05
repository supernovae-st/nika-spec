---
id: ADR-103
title: "policy: block — named workflow-order rules · statically verified"
status: proposed
date: 2026-07-05
phase: ""
deciders: ["@ThibautMelen"]
tags: [policy, static-verification, safety, dfa, v0.2-seed]
affects_crates: [nika-schema, nika-cli]
affects_layers: [L0, L2]
supersedes: []
superseded_by: []
related: [ADR-102, ADR-092]
requires: []
enables: []
amends: []
fci: []
inv: []
shadow_zones: []
nika_codes: [NIKA-POLICY-001]
timeline: ""
follow_ups: ["flip future_clause_policy_rejects_cleanly to a positive parse"]
---

> **Status · DRAFT-PROPOSAL (overnight 2026-07-05) · NOT canon until operator lock.**

# ADR-103 · `policy:` block

## Context

`permits:` governs CAPABILITY (which programs · which hosts · which
tools). Nothing governs ORDER — « no exec may run after an untrusted
fetch » · « every destructive verb sits behind an approval » are
inexpressible today, checkable only by eyeball.

Agentproof (arXiv:2603.20356 · March 2026) opened this category: safety
properties compiled to a DFA, product-composed with the workflow graph,
verified sub-second at 5k nodes — on their bench 27% of workflows carry
structural defects and 55% violate the human-gate property. `nika check`
is already the pre-token audit ladder; this is its natural next rung.

AgentFlow (arXiv:2607.01640 · 2026-07-02 · the first static analysis of
imperative agent programs) proves the asymmetry by contrast: extracting
a dependency graph from LangGraph-class Python requires a heavyweight
analyzer; a declarative DSL hands the same graph to the checker for
free — the whole `policy:` layer costs Nika a parse.

The 2040 rationale: policy is organizational LAW encoded next to the
workflow — the accountability layer's third pillar (resources → budget ·
authority → approve · law → policy).

## Decision

A workflow-level `policy:` block of NAMED, CLOSED rules (v0.2 set) ·

```yaml
policy:
  human_gate_before: [exec, write]      # listed effects require approve: upstream
  no_exec_after: [fetch]                # taint rule · order property
  providers_allowlist: [ollama, mistral]
  max_tasks: 50
```

- The rule set is CLOSED per minor (additive growth) · unknown rule names
  are strict-mode parse errors. No raw LTL is exposed — patterns are named
  after the incidents they prevent (the Anka lesson: constraint IS
  usability).
- **Static semantics** · every rule is decidable at `nika check` on the
  DAG (DFA product per Agentproof is an ENGINE implementation detail).
  A violation is a check ERROR (`NIKA-POLICY-001`) BEFORE any token.
- Runtime semantics · none in v0.2 (statically decidable by
  construction). Rules whose truth needs runtime data are out of this
  ADR's scope, deliberately.
- Orthogonality (normative prose in chapter 09) · `permits:` = what a
  task MAY touch · `policy:` = in what ORDER/SHAPE the workflow may act ·
  `approve:` = who consents. The three compose without overlap.

## Consequences

- `nika check` grows a POLICY line in its ladder (GREEN/violations).
- `human_gate_before` gives ADR-102 its enforcement teeth.
- The conformance suite gains a policy fixture tier (drafts land with
  this ADR · promoted on lock).
