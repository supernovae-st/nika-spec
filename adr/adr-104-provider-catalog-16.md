---
id: ADR-104
title: "Provider catalog 14 → 16 — huggingface + nvidia named providers"
status: accepted
date: 2026-07-05
phase: ""
deciders: ["@ThibautMelen"]
tags: [providers, catalog, huggingface, nvidia, nemotron, open-weight]
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
follow_ups: ["projectors re-run on merge", "doctor shows the 2 new key rows (inherited from catalog · verify)"]
---

# ADR-104 · provider catalog 14 → 16

## Context

The catalog names ACCESS CATEGORIES, not vendors-of-the-day: direct APIs ·
one cross-vendor gateway (openrouter · promoted D-2026-06-10-N2) · 5 local
servers · mock. Two categories were missing and the operator requested both
by name (2026-07-05): the **hub-router** (Hugging Face Inference Providers —
the open-weight house: 100+ models · 18 backends · zero markup · policy
routing) and the **enterprise-NIM** surface (NVIDIA — Nemotron 3 under the
Open Model License · the same OpenAI-compatible surface cloud AND
self-hosted).

The openrouter-promotion bar (distinct access category · durable · demanded)
passes for both. Alignment Rule 3 is strengthened: huggingface makes
open-weight-serverless first-class; nvidia's NIM path keeps workflows
byte-identical between cloud and sovereign GPU deployments.

## Decision

- `huggingface` · router.huggingface.co/v1/chat/completions · `HF_TOKEN` ·
  model rest passes through verbatim (inner slash + optional
  `:provider|:fastest|:cheapest` suffix).
- `nvidia` · integrate.api.nvidia.com/v1/chat/completions ·
  `NVIDIA_API_KEY` · PROMOTION of the catalog-only `nvidia-nim` row (both
  old names live on as aliases) · defaults verified against the live
  /v1/models (121 models).
- Canon: 10 cloud + 5 local + 1 test = **16**. A Stdlib v0.1 engine MUST
  ship all 16.

## Consequences

Engine shipped same-arc (nika#167 · catalog/providers/lsp cascade · counts
pinned 33 catalog-wide). The `openai` escape hatch remains for the long
tail. Presentation order unchanged: local/open-weight first.
