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
- **Conformance** has 3 levels (Core / Runtime / Stdlib v0.1) —
  `spec/07-conformance.md` · the one-command static gate is
  `python conformance/runner.py all` (core + stdlib surface + examples).

## Writing a workflow (the deterministic authoring protocol)

**Agents are the primary authors of Nika.** A weak model following
this protocol beats a strong model improvising. The path is mechanical:

```
INTENT ──route──▶ TEMPLATE ──fill──▶ DRAFT ──check──▶ ERRORS ──repair──▶ ✓
                  (copy · never        slots only      each error
                   invent structure)                   names its fix
```

1. **Route** · `templates/README.md` maps intent → one of the 6
   canonical skeletons (chain · gate-and-act · fanout · etl-state ·
   agent-loop · human-gated-ship). Composite jobs compose templates.
2. **Instantiate** · copy the template · fill every `# SLOT:` line ·
   creativity ONLY in prompts, jq and paths — never in structure.
3. **Check** · `python conformance/runner.py validate <file>` (this
   repo's oracle) or `nika check` (engine). NEVER ship unchecked.
4. **Repair from the error** · the codes are prescriptive ·
   `NIKA-DAG-003` = add the missing `depends_on` edge ·
   `NIKA-VAR-001` = declare the name or fix the typo ·
   `NIKA-PROVIDER` = `model:` needs a canonical `<provider>/<name>`.
   Re-check until zero errors.
5. **Match constructs to proof** · need a construct you haven't used?
   The coverage matrix (docs `examples/overview` · generated) names
   the canonical example that exercises it — read it, don't guess.

Hard rules the validator enforces (memorize · they catch 90% of LLM
errors): one verb per task · snake_case task ids · kebab-case
`workflow:` · every `${{ tasks.X }}` reference REQUIRES
`depends_on: [X]` · `when:` must be CEL boolean · `size()` is the only
CEL function · `nika:write` without `content:` writes nothing ·
`nika:done` only inside `agent.tools`.

The judgment layer (after validity) is the 12 patterns ·
docs `guides/patterns` — deterministic core · parallel by default ·
typed boundaries · leashed fan-outs · the three gates · sovereignty ·
budgets · evidence lands · jq once · callable outputs · mock-first.

## Editing rules

1. A count change = `canon.yaml` first, prose second (same commit).
2. Spec sections live in `spec/01-*.md` … — additive evolution,
   breaking changes need an engine-side MINOR + changelog entry.
3. Examples in `examples/*.nika.yaml` must stay valid against the spec.
4. Commit trailer: `Co-Authored-By: Nika 🦋 <nika@supernovae.studio>`.
