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

1. **Route** · `templates/README.md` maps intent → a canonical
   skeleton (its routing table IS the list — never enumerate it here:
   a hand-typed count went stale the day the shelf grew). Composite
   jobs compose templates.
2. **Instantiate** · copy the template · fill every `# SLOT:` line ·
   creativity ONLY in prompts, jq and paths — never in structure.
3. **Check** · `python conformance/runner.py validate <file>` (this
   repo's oracle) or `nika check` (engine). NEVER ship unchecked.
4. **Repair from the error** · the codes are prescriptive ·
   `NIKA-PARSE` = the YAML shape is wrong — the message names the key
   and what the schema allows there (exactly-one-verb · snake_case id ·
   quoted duration · unknown field) ·
   `NIKA-DAG-001` = break the dependency cycle ·
   `NIKA-DAG-002` = the `depends_on` names a task that doesn't exist ·
   `NIKA-DAG-003` = add the missing `depends_on` edge ·
   `NIKA-DAG-004` = your `recover:` points DOWNSTREAM of the failing
   task (deadlock) — recover from an upstream or independent source ·
   `NIKA-VAR-001` = declare the name or fix the typo ·
   `NIKA-VAR-003` = the path into a declared `schema:` names a key the
   schema forbids — fix the path or the schema ·
   `NIKA-VAR-005` = the `${{ }}` body is outside the CEL v0.1 subset
   (chained relation · unknown function · bare non-boolean `when:`
   root) — or a jq binding doesn't compile ·
   `NIKA-VAR-008` = unclosed `${{` ·
   `NIKA-BUILTIN` = a builtin's args are wrong (the message cites
   builtins-v0.1.md · e.g. `nika:write` without `content:`) ·
   `NIKA-PROVIDER` = `model:` needs a canonical `<provider>/<name>` —
   the message lists the valid prefixes.
   Re-check until zero errors.
5. **Match constructs to proof** · need a construct you haven't used?
   The coverage matrix (docs `examples/overview` · generated) names
   the canonical example that exercises it — read it, don't guess.

Hard rules the validator enforces (memorize · they catch 90% of LLM
errors): one verb per task — the verb IS the task key (`infer:` /
`exec:` / `invoke:` / `agent:` · NEVER a `verb:` field with flattened
args) · snake_case task ids · kebab-case `workflow:` · every
`${{ tasks.X }}` reference in `when:`/`with:`/`for_each:`/verb fields
REQUIRES `depends_on: [X]` (the ONLY exemptions · `output:` is pure jq
— `${{ }}` never appears there at all — and `on_error.recover:` /
`on_finally:` read recovery/parent state · 03 §carve-out) · `invoke`
arguments live under `args:` (not `input:` / `params:`) · quote any
YAML scalar that starts with `${{` (an unquoted leading `${{` breaks
the YAML parse) · `when:` is a `${{ }}` CEL boolean OR the literal
`true`/`false` — a bare string is rejected · `size()` is the only CEL
function · `nika:write` without `content:` is rejected ·
`nika:done` outside `agent.tools` is rejected.

(Every rule above is enforced STATICALLY by this repo's oracle — the
last four landed 2026-06-11 from eval failure clusters · check catches
them all before any model spends a token.)

One style rule the oracle cannot catch · when a task declares
`schema:`, write the prompt NATURALLY — never say « respond in JSON »
or paraphrase the schema in prose. The engine owns the format
negotiation; a prompt that re-states it fights the engine and degrades
weak-model output (the eval measures exactly this).

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
