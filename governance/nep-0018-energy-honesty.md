# NEP-0018 · Energy honesty — the cost doctrine, transposed to watt-hours

- **NEP**: 0018
- **Title**: Extend cost honesty to energy: floors, ceilings, UNBOUNDED, and never a fabricated zero
- **Author**: Thibaut Melen (SuperNovae Studio)
- **Status**: Draft
- **Type**: Standards Track
- **Created**: 2026-07-29

## Abstract

Give energy the exact doctrine cost already has: a static `ENERGY` reading
beside `COST`, speaking the same four words — **floor · ceiling ·
UNBOUNDED · unpriced** — over the catalog's sourced watt-hour facts, with
*unknown stays unknown* as the governing law (an energy Nika cannot prove
is never rendered as `0 Wh`, a local model is *unpriced* — your watts —
never « free »). The data rail already exists (catalog schema `@1.3` ·
`energy = { wh_per_mtok_out, provenance, scope, source, measured_at }`);
this NEP is the doctrine, the render contract, and the sourcing rule that
make the rail honest instead of decorative.

## Motivation

Cost honesty shipped the vocabulary and the scar tissue: the `COST` rung
speaks ceiling (`≤`) or names each uncapped task, never a number whose
unbounded part hides — the engine measured **328×** between a printed
estimate and the real bill on the commonest first workflow (fetch a large
document · summarise it), and **126×** the other way when a floor claimed
what it could not bound. The lesson is general: *a bounded-looking number
that hides its unbounded part is worse than no number.*

Energy is the same claim shape with worse data. Vendors publish almost
nothing; the temptation is to render `0 Wh` for a local model or an
unmeasured API — which is exactly the « free » lie cost honesty killed. A
local model draws watts from the operator's wall; an unmeasured cloud call
draws watts from someone's datacenter. Both are facts without figures —
and a fact without a figure renders as **unpriced**, never zero.

Today (2026-07-29) the whole of nika-spec contains zero occurrences of
« energy »: the reference engine's catalog learned the fields
(schema `@1.3`) and vendored its first sourced figure, and the spec says
nothing. Rails without a train. This NEP is the train.

## Specification

### 1 · Vocabulary (normative · identical to cost)

Every energy surface speaks the four cost words, with the same semantics:

| Word | Meaning (energy) |
|---|---|
| **floor** (`≥`) | the provable minimum Wh — real draw can only be higher |
| **ceiling** (`≤`) | the provable worst case — per-task `max_tokens` cap × a sourced `wh_per_mtok_out`, summed over bounded tasks |
| **UNBOUNDED** | a task whose energy has no provable limit, with the WHY (`no max_tokens declared` · fixable by the author) |
| **unpriced** | tokens will be spent but no sourced energy figure exists for the model (`no energy figure (unmeasured model)` · absence over guess) |

The rendering law is the cost law verbatim: **name the bounded part,
name every unbounded task, never print a total that hides either.** A
surface that cannot honor this prints nothing rather than a wrong number.

### 2 · The data model (the `@1.3` rail · already shipped engine-side)

An energy fact is five fields, none optional within the fact:

```toml
energy = { wh_per_mtok_out = 42.0, provenance = "independent-measured",
           scope = "gpu",
           source = "ml.energy leaderboard v3.0 · H100 · vLLM · conversation workload (arXiv 2505.06371)",
           measured_at = "2025-12" }
```

- **`wh_per_mtok_out`** — watt-hours per million OUTPUT tokens, finite and
  `> 0` (a zero would claim free inference; the null is the absent fact).
  Per-OUTPUT because decode dominates measured inference energy (≥96% in
  the ML.energy v3.0 methodology): a per-total figure would dilute the
  number with nearly-free prefill and reward long prompts.
- **`provenance`** (closed set) — WHO produced the number:
  `measured-local` · `independent-measured` · `vendor-claim` ·
  `independent-estimate`. An estimate may enter — EXPLICITLY, wearing its
  label — never as a silent default.
- **`scope`** (closed set) — WHAT the number covers: `gpu` (accelerator
  only) · `device` (whole host) · `fleet` (host + idle + PUE). A GPU-only
  figure is roughly half a fleet figure for the same model: without this
  axis two truthful numbers are silently incomparable. A surface MUST NOT
  sum or compare figures across scopes without naming the mix.
- **`source` + `measured_at`** — the citable origin and the ISO month.
  Energy figures rot with hardware and runtime generations; a dateless or
  sourceless figure is refused at build time (absence over guess).

### 3 · The `ENERGY` reading in the static forecast

`nika check` renders an `ENERGY` rung beside `COST`, same ladder, same
grammar:

```text
 ✔ ENERGY   ≤ 2.7 Wh worst-case OUTPUT ceiling (gpu-scope · 1 of 3 tasks measured)
      brief   groq/qwen/qwen3-32b   ≤64k tk · ≤ 2.7 Wh (independent-measured · 2025-12)
      triage  anthropic/claude-…    unpriced — no energy figure (unmeasured model)
      poll    ollama/qwen3.5:4b     unpriced — no energy figure (local model · your watts)
 ⚠  ENERGY   unbounded (uncapped tasks present)
      think   …                     UNBOUNDED — no max_tokens declared
```

Rules: the rung appears whenever the workflow has ≥1 inference task (the
same suppression as `COST`'s « no inference tasks »); the headline carries
the scope axis whenever a ceiling is claimed; a mixed-scope sum names the
mix or refuses to sum; prompts stay unpriced (the same narrowing `COST`
carries — the ceiling is an OUTPUT ceiling).

### 4 · Aggregation

`nika:inspect view: cost` gains the energy aggregate under the same
honesty markers (bounded Wh where derivable · unpriced counts elsewhere),
or a sibling `view: energy` — implementation's choice, the MARKERS are the
contract.

### 5 · The gate (optional · symmetric)

`--max-energy-wh` is a **block-before-spend** gate symmetric to
`--max-cost-usd`: refuse at start when the provable part already exceeds
the budget; stop mid-run at the last pre-spend seam otherwise. The stop
mints a documented error code in the budget family (spec `05` · the id is
fixed at implementation time, adjacent to the cost stop — this NEP
reserves the semantics, not the number). A run stopped by the gate is a
refusal with a named reason, never a crash.

### 6 · The sourcing rule

A figure enters the catalog ONLY as the five-field fact above. No figure
= absent = unpriced. Deriving figures from parameter counts or vendor
marketing is forbidden as a default; third-party modelling may enter as
`independent-estimate`, labelled. First sourced row (engine, 2026-07-29):
`groq / qwen/qwen3-32b` from the ML.energy leaderboard v3.0 (H100 · vLLM ·
arXiv 2505.06371) — open-weight models are the measurable frontier, and
that asymmetry is itself honest: closed-API models stay unpriced until a
vendor discloses or an independent methodology covers them.

## Conformance test

Fixtures (engine forecast tests first; spec `conformance/` rows when the
render contract freezes — this NEP is Draft):

1. one capped task on a measured model → `ENERGY` prints `≤ cap ×
   wh_per_mtok_out` with the scope axis named;
2. the same workflow on an unmeasured model → `unpriced`, and the string
   `0 Wh` appears nowhere;
3. an uncapped task → `UNBOUNDED — no max_tokens declared`, named per
   task, no total claimed;
4. mixed scopes in one workflow → the headline names the mix or refuses
   the sum;
5. (gate) a run whose provable floor exceeds `--max-energy-wh` refuses
   before any provider is touched, with the documented code.

## Compatibility impact

Additive. No workflow-YAML surface changes (the gate is CLI, the rung is
render, the facts are catalog data). Surfaces checked: envelope (spec
`01` · untouched) · check render (new rung) · `nika:inspect` (new
fields, additive) · catalog schema `@1.3` (already shipped) · trace (the
gate stop reuses the budget-refusal shape).

## Migration plan

None (additive).

## Rejected alternatives

- **CO₂e as the primary unit** — rejected: carbon intensity varies by
  grid, hour and region; a gCO₂e constant hides a location assumption
  inside a number. Wh is the measurable; a carbon projection is a later
  informational annex taking an explicit grid factor as INPUT.
- **Estimating absent figures (parameter-count heuristics)** — rejected
  as a default: a fabricated default wearing a lab coat. The
  `independent-estimate` provenance exists so modelling can enter
  explicitly, labelled, never silently.
- **`0 Wh` for local models** — rejected: the exact « free » lie cost
  honesty killed. Local inference is unpriced — the operator's watts.
- **An `energy:` budget block in workflow YAML** — rejected: enforcement
  is an engine/CLI concern (the spec `08` §Observability precedent for
  cost budgets) · the language surface stays clean.
- **A single scopeless number** — rejected: gpu-vs-fleet differ ~2× on
  the same model; a scopeless figure makes two truths incomparable and
  every comparison a lie.
