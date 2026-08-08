# NEP-0021 · The `delegation:` block — bounded, attenuated, attested sub-runs under `agent:`

- **NEP**: 0021
- **Title**: The `delegation:` block — bounded, attenuated, attested sub-runs under `agent:` (three stdlib builtins: `nika:delegate` · `nika:take` · `nika:scratch`)
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-08-08

## Abstract

An `agent:` task gains an optional `delegation:` block that lets the agent
spawn bounded child runs mid-loop, and the stdlib gains three builtins
(`nika:delegate` · `nika:take` · `nika:scratch`) that make those children
first-class: context is passed, never history; authority only ever narrows;
every crossing is traced; one root hash proves the whole tree. Absent the
block, delegation is refused — the same fail-closed shape as NEP-0003. The
four-verb surface is untouched: delegation rides `agent:` tools, the way
every new capability does.

## Motivation

1. **The language already teaches context folding — statically.** The
   sandwich (an `agent:` plans a list · `for_each` runs each item in a
   fresh window · a synthesis receives only the projected results) is the
   documented pattern (docs `guides/patterns` §context folding). What it
   cannot do is the dynamic half: the agent deciding *mid-loop*, from what
   it just read, that a sub-question deserves its own bounded run. Today
   the only escape hatch is `exec: nika run child.nika.yaml` — a raw
   re-entry with no unified budget ledger, no trace chaining between
   parent and child, and no narrowing of authority.
2. **Recursive agent work is the category, and the category's defaults
   are unsafe.** The recursive-language-model research line (recursive
   sub-calls over fresh contexts · arXiv 2512.24601) and the harness
   family at large converge on spawn-as-function-call — and ship it with
   full history inheritance, full authority inheritance, and journals
   that attest nothing. A declarative engine can offer the same shape
   with the opposite defaults: that contrast is the reason this NEP
   exists.
3. **The composition surfaces are already paid for.** Permits are
   composable (NEP-0003 · NEP-0005) · the trace is a normative,
   verifiable chain (NEP-0007 · NEP-0011) · spend is token-denominated
   and budgetable (NEP-0019). Delegation is the one place those three
   muscles must work *recursively* — and nothing today exercises that.

## Specification

### The `delegation:` block (the carrier)

An additive, optional field of the `agent:` verb body — the one-obvious-way
call: the bounds govern the task's whole agent loop, not any single tool
call, and a task-level block mirrors `permits:` exactly.

```yaml
tasks:
  lead:
    agent:
      system: "…"
      prompt: "…"
      tools: ["nika:delegate", "nika:take"]
      delegation:            # ABSENT = delegation refused (fail-closed)
        max_depth: 2         # integer ≥ 1 · recursion floor
        max_children: 6      # integer ≥ 1 · spawn ceiling per agent task
        budget_share: 0.6    # 0 < x ≤ 1 · children share ≤ this fraction
                             # of THIS task's token budget (NEP-0019 unit)
```

### The three builtins (stdlib v0.1 additive)

- `nika:delegate` — spawn a bounded child, return an immediate **handle**
  (`{id, trace_ref}`), never a payload. Two call forms:
  - **child-CONTRACT** · `{workflow: "path.nika.yaml", with: {…},
    ceiling_tokens: N}` — the child is a `.nika.yaml` file: `nika check`ed
    recursively at the parent's check, its declared permits statically
    comparable to the parent's.
  - **child-PROMPT** · `{prompt: "…", context: <jq projection>,
    ceiling_tokens: N}` — ad-hoc, bounded, permits `∅` by default (pure
    inference over the passed context).
- `nika:take` — `{child: <handle id>, query: "<jq>"}` — the ONLY way a
  child result re-enters the parent: a jq projection at the boundary.
  Every `take` is a trace line: the membrane is data.
- `nika:scratch` — `{op: set|get|list, key, value?}` — a run-scoped KV:
  values materialize at the workspace and are hashed into the trace; the
  agent's context carries *keys*, not values. (This builtin is specified
  here so the trio lands as one vocabulary; it ships without recursion —
  usable by any `agent:` task, no `delegation:` block required.)

### The seven laws (normative)

1. **No fifth verb.** Delegation is tools under `agent:` — the four-verb
   freeze holds.
2. **A child receives a CONTEXT, never the history.** Context-as-argument;
   a fresh window; the parent projects (jq) what it transmits.
3. **Attenuation.** `permits_child ⊆ (permits_parent ∩ permits_declared_child)`.
   A widening attempt is refused — at check when the child is a contract,
   at runtime otherwise.
4. **Handles, never payloads.** `delegate` returns a handle; return
   traffic passes only through `take` (jq-projected, traced).
5. **Recursive budget.** Every spawn declares `ceiling_tokens`;
   `Σ child ceilings ≤ budget_share × parent budget`, escrowed at spawn,
   the full ledger in the trace. Tokens, never currency (NEP-0019).
6. **The trace tree is ONE proof.** Each child run writes its own
   hash-chained trace; the parent trace chains the child trace hashes; a
   single root hash attests the whole tree (NEP-0007 · NEP-0011
   machinery, extended recursively).
7. **Recursion is default-deny.** No `delegation:` block → a
   `nika:delegate` call is refused — the NEP-0003 shape applied to
   recursion.

### Error family

New namespace `NIKA-DEL-NNN`; exact codes assigned at Accepted, one per
refusal class: block absent · depth bound · children bound · budget
breach · attenuation widening · contract cycle (a contract child whose
own delegation graph reaches an ancestor) · `take` on an unknown or
failed handle · scratch get of a never-set key. Each refusal teaches its
fix in the message, per the house error-voice.

### Canon and counts

At Implemented, `canon.yaml` gains the three builtins and the stdlib
count moves with them (counts are derived, never hand-typed). The spec
sections touched: `02-verbs.md` (the `agent:` body grammar) ·
`builtins-v0.1.md` (the trio) · `07-conformance.md` (the fixtures below).

## Conformance test

Fixtures land same-PR as the spec-text amendment (the NEP-0000 ratchet),
in a new `conformance/` delegation set:

- `delegate` under `agent.tools` with **no** `delegation:` block → check
  refuses with the block-absent code (the negative-first fixture).
- `max_depth` / `max_children` exceeded → refusal, each bound named.
- Child-contract declaring a permit outside the parent's → static
  refusal (attenuation, checkable form).
- `Σ child ceilings > budget_share × parent budget` → runtime refusal ·
  the ledger lines present in the trace.
- A two-level tree (contract child spawning a prompt child) → the parent
  trace chains both child hashes · the root hash verifies offline.
- `nika:scratch` · get of a never-set key → the taught error · a value
  mutated out-of-band is detected at the trace hash.

## Compatibility impact

None (additive) — and here is the surface check: `agent:` bodies without
`delegation:` parse and mean exactly what they mean today, except that a
`nika:delegate` tool call now refuses *informed* (it previously failed as
an unknown builtin); no workflow in the wild can hold `nika:delegate`
today (the name did not exist). The `exec: nika run child.yaml` escape
hatch stays legal and stays what it is: unlinked — no shared ledger, no
trace chaining, no attenuation. The four verbs, the envelope `nika: v1`,
and every existing conformance row are untouched.

## Migration plan

None — no existing workflow changes meaning.

## Rejected alternatives

- **A fifth verb (`delegate:`).** Loses to the freeze: the four-verb
  surface is the language's credibility; every new capability rides
  `invoke:`/`agent:` tools.
- **The carrier on the `tools:` entry** (per-tool config). Bounds the
  wrong scope: depth, fan-out and budget share are properties of the
  agent loop, not of one call; a task-level block is also the `permits:`
  shape authors already know.
- **Currency-denominated ceilings (`ceiling_usd`).** A dollar figure in
  a durable file rots with every price change and is meaningless on a
  local provider; tokens are the portable unit (NEP-0019), money stays
  a projection.
- **Full-history inheritance** (the child sees the parent's context).
  That is context rot with extra steps; law 2 exists because the folding
  pattern already proved its value statically.
- **A workflow-level `delegation:` block.** The spawn point is the agent
  loop; a workflow block would permit-by-default every agent task in the
  file, the opposite of fail-closed.
- **Shipping `nika:scratch` separately later.** The trio is one
  vocabulary (spawn · return · stash); splitting it teaches the membrane
  twice.
