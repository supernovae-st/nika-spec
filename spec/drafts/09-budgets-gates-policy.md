> **Status · DRAFT-PROPOSAL (overnight 2026-07-05) · NOT canon until the
> operator locks ADR-101/102/103. This chapter lives in `spec/drafts/`
> and moves to `spec/09-budgets-gates-policy.md` on lock.**

# 09 · Budgets · Gates · Policy (the v0.2 accountability clauses)

The three clauses share one design premise: by the time agents author
most workflows, the language's surviving job is **accountability** —
humans review, bound, and consent; the engine proves. Each clause is a
guard-rail, not a capability (adding freedom is what the 4-verb lock
forbids; adding accountability is what the envelope grows FOR).

| Clause | Governs | Level | Static check | Error |
|---|---|---|---|---|
| `budget:` | resources ($ · tokens) | workflow + task | cap aggregation · UNBOUNDED-under-budget = error | `NIKA-BUDGET-001/002` |
| `approve:` | human authority | task | DAG barrier rendered in PLAN | `NIKA-GATE-001` |
| `policy:` | order/shape law | workflow | named rules decided on the DAG | `NIKA-POLICY-001` |

## The orthogonality triangle (normative)

`permits:` = what a task MAY touch (capability) · `policy:` = in what
ORDER/SHAPE the workflow may act (law) · `approve:` = who CONSENTS to an
act (authority) · `budget:` = how much it may COST (resources). None
subsumes another; all four are decidable before a single token is spent.

## Grammar (v0.2 draft)

```yaml
nika: v1
workflow: quarterly-report

budget: { usd: 0.50, tokens: 200000 }     # workflow ceiling · both optional

policy:
  human_gate_before: [exec, write]
  no_exec_after: [fetch]
  providers_allowlist: [ollama, mistral]
  max_tasks: 50

tasks:
  - id: research
    budget: { usd: 0.10 }                  # tighter bound wins
    retry: { max_attempts: 2 }             # attempts SPEND the budget
    infer: { prompt: "...", max_tokens: 4000 }

  - id: ship
    approve: true                          # TTY · renders the RESOLVED action
    exec: { command: ./deploy.sh prod }

  - id: publish
    approve: { via: file, path: .nika/approvals/publish }
    invoke: { tool: "nika:notify", args: { channel: releases } }
```

## Interactions (the composition table)

- `retry:` × `budget:` — every attempt spends; retrying onto an exhausted
  cap short-circuits (`NIKA-BUDGET-002`) instead of burning a slot.
- `approve:` × `--resume` (ADR-099) — approvals are never cached hits; a
  resumed run re-presents the gate.
- `approve:` × DAG — the gate is a barrier; `nika check` PLAN renders it.
- `policy.human_gate_before` × `approve:` — the policy rule is the static
  ENFORCER of the gate clause (ADR-102 gets teeth from ADR-103).
- `for_each:` × `budget:` — iterations share the task budget.
- `agent:` budgets (`max_turns` · `max_tokens_total`) — unchanged ·
  count toward the task cap.

## Full rationale

ADR-101 (budget) · ADR-102 (approve · WYAIWYE) · ADR-103 (policy) — each
carries its research grounding (arXiv:2606.04056 · 2606.02668 ·
2603.20356) and its 2040 rationale.
