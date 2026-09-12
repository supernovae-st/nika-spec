# AGENTS.md — nika-spec (the Nika workflow language)

Vendor-neutral agent entry per the AGENTS.md convention (agents.md).

## What this repo is

The **canonical specification** of the Nika workflow language —
Apache-2.0, runtime-agnostic (the GraphQL/OpenAPI pattern). The
reference engine lives at `supernovae-st/nika` (AGPL-3.0-or-later).

## Load-bearing facts (verify in-repo · never from memory)

- **Envelope** 9 top-level keys, frozen: `nika` · `model` · `inputs` ·
  `const` · `secrets` · `permits` · `run` · `tasks` · `outputs`. `nika:`
  carries the file's kebab-case NAME (the mark AND the name) · the document
  type is read from `tasks:` (present = workflow · absent = project), never
  from a filename. No version is typed anywhere: the family is v1, there is
  no `nika: v2` ever, and pre-1.0 breaking changes land INSIDE v1.
- **4 verbs, locked**: `infer` · `exec` · `invoke` · `agent`.
  HTTP fetch is the `nika:fetch` builtin under `invoke:` — NOT a verb.
- **Counts are projected into `canon.yaml`** from the owning `canon/` registries (see `SSOT.md`); do not hand-edit generated hub sections.
  NEVER hardcode a count in prose; cite `canon.yaml`.
- **Conformance** has 3 levels (Core / Runtime / Stdlib v0.1) —
  `spec/07-conformance.md` · the one-command static gate is
  `python conformance/runner.py all` (core + stdlib surface + examples).

## Workflow authoring

For a workflow change, use `templates/README.md` to find a relevant starting point and [the authoring guide](templates/AUTHORING.md) for task boundaries, diagnostics, structured inference and paid-readiness checks. Read only the relevant sections. A template is a starting point; the current language contract and oracle determine valid structure.

Validate authored workflows with `python3 conformance/runner.py validate <file>` or the applicable `nika check` mode. Repair errors introduced by the change. Static validation does not execute the workflow or authorize its effects. Keep the selected model and current permits; no agent/model switch or paid inference follows implicitly from authoring.

## Evaluating or implementing the standard

For standard maturity or engine conformance work, select the relevant contract:

- [`conformance/runner-protocol.md`](./conformance/runner-protocol.md) — the third-party fixture contract
- [`CONFORMANT_IMPLEMENTATIONS.md`](./CONFORMANT_IMPLEMENTATIONS.md) — the registry + the one claim form « Nika v1 Conformant — <Level> (spec <commit>) »
- [`governance/nep-0000-the-nep-process.md`](./governance/nep-0000-the-nep-process.md) — the evolution door, DORMANT until the v1 pre-freeze (pre-freeze: edit `spec/` directly, fixtures same-PR · [`governance/README.md`](./governance/README.md) says where the twenty folded laws live)
- [`governance/certifications.md`](./governance/certifications.md) — the earned-badges matrix with evidence links
- [`GLOSSARY.md`](./GLOSSARY.md) — canonical referents for overloaded words

## Editing rules

1. Change the owning `canon/` registry and regenerate the hub/prose with the compiler/projectors in `SSOT.md`; preserve its explicitly authored ledger sections.
2. Spec sections live in `spec/01-*.md` … — additive evolution,
   breaking changes need an engine-side MINOR + changelog entry.
3. Examples in `examples/*.nika.yaml` must stay valid against the spec.
4. Commit trailer: `Co-Authored-By: Nika 🦋 <nika@supernovae.studio>`.

## Completion

Finish the authorized change through relevant validation and requested publication. Keep normative behavior changes paired with their conformance fixtures as specified in `CONTRIBUTING.md`. This entry refactor does not change a language law. Preserve concurrent edits and separate pre-existing failures from failures introduced here. Shared instructions work across model choices; client capability and measured behavior remain separate qualification concerns.
