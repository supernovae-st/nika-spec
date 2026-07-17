---
id: ADR-105
title: "Provider catalog 16 → 17 · moonshot (Kimi) the frontier open-weight seat"
status: accepted
date: 2026-07-17
phase: ""
deciders: ["@ThibautMelen"]
tags: [providers, catalog, moonshot, kimi, open-weight, sovereignty]
affects_crates: [nika-catalog, nika-providers, nika-lsp]
affects_layers: [L1, L2]
supersedes: []
superseded_by: []
related: []
requires: []
enables: []
amends: []
fci: []
inv: []
shadow_zones: []
nika_codes: []
timeline: ""
follow_ups: ["projectors re-run on merge", "providers registry home ruling (C1 · canon/EXCEPTIONS.md) folds moonshot into the sealed row set"]
---

# ADR-105 · provider catalog 16 → 17

## Context

The catalog names ACCESS CATEGORIES, not vendors-of-the-day: direct APIs ·
one cross-vendor gateway (openrouter) · the open-weight house (huggingface) ·
the enterprise-NIM surface (nvidia) · 5 local servers · mock. One category was
still unnamed: the **frontier open-weight** seat · a model at the coding /
reasoning frontier whose WEIGHTS open on a J+10 window, reachable direct today
and self-hostable within days.

Kimi K3 (Moonshot AI · released 2026-07-16) fills it: a 1M-token thinking
model at the agentic-coding frontier, OpenAI-compatible surface, weights
scheduled open 2026-07-27 (vLLM · MXFP4). The openrouter-promotion bar (a
distinct access category · durable · demanded) passes: this is neither a
gateway nor a hub-router nor an enterprise-NIM · it is the frontier
open-weight direct API, and it is the first CN-frontier seat in the catalog.

Nika is the rail, not the locomotive. A frontier model shipping this week is
one more locomotive on the rail · adding it changes nothing about the neutral
substrate and everything about what an operator can reach with `--var model=`.
Alignment Rule 3 is preserved: local/open-weight leads the presentation order ·
moonshot is a named SEAT, never the default one.

## Decision

- `moonshot` · `https://api.moonshot.ai/v1/chat/completions` (the complete
  endpoint · openai-chat dialect) · `MOONSHOT_API_KEY` (`sk-…`).
- Default model `kimi-k3` (frontier · thinking · 1M context) · the cheaper
  seat `kimi-k2.6` · coding seats `kimi-k2.7-code` /
  `kimi-k2.7-code-highspeed` · the model name passes through verbatim.
- Caveats, pinned because they bite silently ·
  - **Thinking-model budget** · `kimi-k3` reasons before it answers from the
    SAME `max_tokens` pool · a tight `max_tokens: 64` returns an EMPTY
    completion (the budget went to thinking) · 512 is the practical floor.
  - **Temperature server-fixed at 1.0** for `kimi-k3` · a workflow
    `temperature:` is accepted but the k3 seat overrides it server-side · the
    non-thinking Kimi seats honor it.
  - **Vision** · base64 image parts only · never a public URL.
- Canon: 11 cloud + 5 local + 1 test = **17**. A Stdlib v0.1 engine MUST ship
  all 17.

## Consequences

Engine ships the native adapter same-arc (release 0.104.0 · catalog /
providers / lsp cascade · the K3 niveau-0 proof already ran green via the
`openai` + `NIKA_OPENAI_BASE_URL` hatch, the named adapter supersedes the
hatch for this seat). The escape hatch remains for the long tail. Presentation
order unchanged: local/open-weight first, then mistral (EU) · huggingface ·
openai · xai · then anthropic · never anthropic first.

The stdlib prose home (`stdlib/providers-v0.1.md`) documents the seat + the
thinking-model caveats. `canon.yaml` carries the 17th id (providers ledger row
· registry home still owed at C1 per `canon/EXCEPTIONS.md`). All count surfaces
project from `canon.yaml` (`counts.providers: 17`).

## Sovereignty posture

The hosted Moonshot API is a THIRD-COUNTRY surface: servers in China, and
training-on-inputs by default · the inverse of the OpenAI / Anthropic data
posture. The catalog names it anyway, because sovereignty here is STRUCTURAL,
not a matter of trusting a vendor's promise ·

- **Data tiering governs which seat is legal.** T0 (synthetic / already-public
  data) may reach any hosted API including moonshot. T1 (data under a DPA) is
  DPA-gated. T2 (never-leaves) NEVER touches the hosted API · it runs on
  self-hosted weights only.
- **`permits:` egress makes the tiering mechanical.** A workflow reaches a host
  only if that host is in its declared egress allowlist. A T2 workflow simply
  never lists `api.moonshot.ai` · the call is then impossible by construction,
  not by discipline · `nika check` reports the capability escape before one
  token is spent.
- **Self-host is the sovereign path, and it is near.** Weights open 2026-07-27
  · served with vLLM (MXFP4) they are reachable via the `vllm/…` provider or
  the `openai` escape hatch pointed at your own box · byte-identical workflow,
  zero third-country egress. The hosted seat is the convenience rung of the
  sovereignty ladder, the self-host seat is the sovereign one.

## Alternatives

- **Route Kimi through the `openai` escape hatch forever** · rejected · it
  hijacks the `openai` prefix (you cannot reach vanilla OpenAI and Moonshot
  from one engine config) and a frontier open-weight seat earns first-class
  one-field selection, exactly the openrouter / ADR-104 precedent.
- **Route through `openrouter` / `huggingface` only** · valid as a fallback,
  kept · but the direct API gives native latency, the thinking budget, and the
  billing seat · the direct provider and the gateways coexist.
- **Omit it on sovereignty grounds** · rejected · omission is not sovereignty ·
  the structural egress gate + data tiering is. Naming the seat while making
  its hosted use structurally gated is the honest position.

## Related

- `adr/adr-104-provider-catalog-16.md` · the huggingface + nvidia precedent
  this ADR applies.
- `stdlib/providers-v0.1.md` · the prose home (the `moonshot` entry + the
  `openai` escape-hatch var form).
- `canon/EXCEPTIONS.md` · the providers ledger row (registry home owed C1).

## Notes

Presentation-order and anti-capture (Rule 3 · `supernovae-alignment.md`) ·
moonshot enters as one more named seat, never a default. The teaching surfaces
(quickstarts · examples · README heroes) keep leading with local/open-weight
then mistral · huggingface · openai · xai, with anthropic never first.
