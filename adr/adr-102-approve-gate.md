---
id: ADR-102
title: "approve: gate — what you approve is what executes"
status: proposed
date: 2026-07-05
phase: ""
deciders: ["@ThibautMelen"]
tags: [approve, human-gate, wyaiwye, delegation, v0.2-seed]
affects_crates: [nika-schema, nika-cli, nika-runtime]
affects_layers: [L0, L2, L4]
supersedes: []
superseded_by: []
related: [ADR-099, ADR-101]
requires: []
enables: []
amends: []
fci: []
inv: []
shadow_zones: []
nika_codes: [NIKA-GATE-001]
timeline: ""
follow_ups: ["flip future_clause_approve_rejects_cleanly to a positive parse", "human-gated-ship template gains the clause form alongside the builtin form"]
---

> **Status · DRAFT-PROPOSAL (overnight 2026-07-05) · NOT canon until operator lock.**

# ADR-102 · `approve:` gate

## Context

Human gating exists today as a PATTERN: the `nika:prompt` builtin + the
human-gated-ship template (assert makes a RED gate terminal). It works —
and it has a structural hole the research named. arXiv:2606.02668 (« What
You Approve Is What Executes ») shows approval flows where the human
confirms an agent-WRITTEN summary, not the action itself; on the
Agentproof bench (arXiv:2603.20356) **55% of workflows violate the
human-gate-before-destructive pattern**. `nika:prompt`'s `message:` is
authored by the workflow (often via an upstream `infer:`) — the engine
cannot guarantee the text matches the action.

A first-class clause CAN: the engine renders the RESOLVED action — the
exact argv an `exec:` will run, the resolved URL+args an `invoke:` will
call, the model+prompt an `infer:` will send — variables interpolated,
nothing summarized. That property (WYAIWYE) is unreachable from a builtin.

The 2040 rationale: agents author, humans approve — approval is the
durable human-authority primitive, and its `via:` must be an open enum
from day 1 (delegation chains and signatures arrive without a major).

## Decision

```yaml
tasks:
  - id: ship
    approve: true                    # TTY prompt · renders the RESOLVED action
    exec: { command: ./deploy.sh prod }

  - id: publish
    approve: { via: file, path: .nika/approvals/publish }   # headless/CI
    invoke: { tool: "nika:notify", args: { ... } }
```

- `approve: true` ≡ `approve: { via: tty }`.
- `via:` is an OPEN enum · v0.2 ships `tty` + `file` · future values
  (`signature` · delegated chains) are additive minors. Unknown `via:` is
  a parse error in strict mode (never a silent fall-through to unattended).
- The gate blocks THE TASK · dependants wait (a barrier in the DAG ·
  `nika check`'s PLAN renders it). Refusal fails the task with
  `NIKA-GATE-001` (terminal · `on_error:` composes — `recover:` can route
  a refusal).
- **WYAIWYE (normative)** · the approval surface MUST render the resolved
  action payload — engines MUST NOT substitute workflow-authored text.
  (`nika:prompt` remains for free-form questions; `approve:` is for
  consent-to-act.)
- `nika run --resume` (ADR-099) composes: a run paused at an approval
  resumes THROUGH the same gate — approvals are never cached as hits.

## Risks (fresh-sweep 2026-07-05)

Oversight has a CAPACITY (arXiv:2606.08919): approval is a finite human
resource — reviewer fatigue and gate-flooding make an over-escalating
system LESS safe (inverted-U). `approve:` must stay SCOPED (the
irreversible acts · policy names them) and composes with `budget:` —
never a blanket gate on every task.

## Consequences

- The human-gated-ship template gains the clause form; the builtin form
  stays documented for free-form questions.
- Agentproof-class static checks (ADR-103 `policy:`) can REQUIRE this
  clause before destructive verbs — the two seeds compose.
