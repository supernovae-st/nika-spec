# AGENTS.md — nika-spec (the Nika workflow language)

Vendor-neutral agent entry per the AGENTS.md convention (agents.md).

## What this repo is

The **canonical specification** of the Nika workflow language —
Apache-2.0, runtime-agnostic (the GraphQL/OpenAPI pattern). The
reference engine lives at `supernovae-st/nika` (AGPL-3.0-or-later).

## Load-bearing facts (verify in-repo · never from memory)

- **Envelope** `nika: v1` — frozen forever. The single version marker
  workflow authors type.
- **4 verbs, locked**: `infer` · `exec` · `invoke` · `agent`.
  HTTP fetch is the `nika:fetch` builtin under `invoke:` — NOT a verb.
- **Counts live in `canon.yaml`** (the SSOT — verbs, builtins, providers,
  extract modes, each `count:` self-checked against `items[]`).
  NEVER hardcode a count in prose; cite `canon.yaml`.
- **Conformance** has 3 levels (Core / Standard / Full) —
  `spec/07-conformance.md` + `conformance/` runner protocol.

## Editing rules

1. A count change = `canon.yaml` first, prose second (same commit).
2. Spec sections live in `spec/01-*.md` … — additive evolution,
   breaking changes need an engine-side MINOR + changelog entry.
3. Examples in `examples/*.nika.yaml` must stay valid against the spec.
4. Commit trailer: `Co-Authored-By: Nika 🦋 <nika@supernovae.studio>`.
