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
   `NIKA-PARSE-002` = a missing envelope field — add `nika:`, or a
   non-empty `tasks:` (a file with no `nika:` key is not a nika file) ·
   `NIKA-PARSE-003` = `nika:` is not a kebab-case id (`^[a-z][a-z0-9-]*$`) —
   it carries the file's NAME, never a version ·
   `NIKA-DAG-001` = break the dependency cycle ·
   `NIKA-DAG-002` = a `with:`/`after:` entry names a task that doesn't exist ·
   `NIKA-VAR-021` = a `tasks.*` reference outside the boundary — hoist it into `with:` ·
   `NIKA-VALUES-001` / `NIKA-VALUES-002` = a dead `vars:` / `env:` block (or
   `${{ vars.X }}` / `${{ env.X }}` read) — classify each use: typed parameter
   → `inputs:` · a knob the deployment supplies → an `inputs:` entry with
   `required: false` and a `default:` · fixed value → `const:` · store
   reference → `secrets:` ·
   `NIKA-VALUES-003` = a `${{ }}` value read outside the three authorities
   (`inputs` · `const` · `secrets`) — the namespace is closed ·
   `NIKA-TYPE-001` = a PascalCase name in type position — named types are
   gone; write the type expression INLINE in `returns:` ·
   `NIKA-SEC-015` = the order law — an `exec:` task sits transitively
   downstream of a net-effecting task (`nika:fetch` · `nika:notify`).
   Consume the fetched value with a builtin (`nika:jq` · `nika:validate`)
   instead of a shell, or drop the edge. The diagnostic names the PATH,
   which is the witness. **Unconditional** — no block declares it and none
   can disable it ·
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
args) · snake_case task ids · kebab-case `nika:` · every
`${{ tasks.X }}` reference in `when:`/`with:`/`for_each:`/verb fields
lives at the BOUNDARY: `with:` values (the binding IS the edge) · `after:`
keys · `on_error.recover` · an `unwind` task (its producer only) · workflow
`outputs:` (the ONLY other exemptions · `extract:` is pure jq
— `${{ }}` never appears there at all — and `on_error.recover:` / an
`unwind` body read recovery/producer state · 03 §carve-out) · `invoke`
arguments live under `args:` (not `input:` / `params:`) · quote any
YAML scalar that starts with `${{` (an unquoted leading `${{` breaks
the YAML parse) · `when:` is a `${{ }}` CEL boolean OR the literal
`true`/`false` — a bare string is rejected · CEL callables are a closed
set: `size(x)` · `has(x)` · `x.size()` · `x.contains(s)` ·
`x.startsWith(s)` · `x.endsWith(s)` · `nika:write` without `content:` is
rejected ·
`nika:done` outside `agent.tools` is rejected.

(Every rule above is enforced STATICALLY by this repo's oracle — the
last four landed 2026-06-11 from eval failure clusters · check catches
them all before any model spends a token.)

One style rule the oracle cannot catch · when a task declares
`schema:`, write the prompt NATURALLY — never say « respond in JSON »
or paraphrase the schema in prose. The engine owns the format
negotiation; a prompt that re-states it fights the engine and degrades
weak-model output (the eval measures exactly this).

**Extract facts, then the law.** A model may produce closed, cited
semantic *facts*. Scoring, routing, publish/abstain is `nika:jq` or
`nika:decide` — never a second `infer:` to "pick the level". Numeric
facts are `type: integer` with a numeric `enum` (`-1|0|1|3`); a
string enum of digits (`"0"|"1"|"3"`) is the shape models do not emit
(JSON `3`). The engine hints `digit-string-enum`. The shape is
`examples/13-extract-then-law.nika.yaml`. The named bundle is
`examples/14-decide-publish.nika.yaml`. Prove the law on const
fixtures (`unproven-law`) before leaving `mock/`. An agent that
*writes* Nika grants `nika:compose` on `agent.tools` after
`nika:done` and iterates on the check JSON until `valid`
(`examples/15-compose-self-check.nika.yaml`). A standalone
`invoke: nika:compose` is `NIKA-BUILTIN-COMPOSE-001`. Checking
never executes the draft.

**Paid-infer order** (cheaper than discovering this with tokens) ·
`nika check --native-strict` → one-task `mock/echo` probe of every
new builtin → freeze the extract schema type → pin the glob
(`exclude: "**/README.md"`) → then wire a paid model.

**After valid, is there a better one-way?** A green check is legal,
not best. Recurse on the file as an environment (Zhang/Kraska/Khattab
2026 · arXiv:2512.24601): do not swallow it — inspect two examples,
decompose (`for_each` / `invoke: { workflow: }`), verify with
`nika:jq` not a second infer. Loop until `nika check --json` reports
`paid_ready: true` (the paid-run family is empty; `.next` is the first
repair and `.compiled` is the law-is-proven bit) AND
`--native-strict` is clean, or every remaining *non-paid* hint has an
in-file reason (CONVENTIONS §10). The engine hints `infer-as-law` when
a prompt asks the model to assign a belt. A second infer whose schema
is a language enum is language, not the law. The MCP `nika_check`
oracle fails `infer-as-law` and `digit-string-enum` by default.

The judgment layer (after validity) is the 12 patterns ·
docs `guides/patterns` — deterministic core · parallel by default ·
typed boundaries · leashed fan-outs · the three gates · sovereignty ·
budgets · evidence lands · jq once · callable outputs · mock-first.

## Evaluating or implementing the standard

An agent assessing Nika's standard maturity (or implementing an
engine) reads these five surfaces — they exist, in this repo ·

- [`conformance/runner-protocol.md`](./conformance/runner-protocol.md) — the third-party fixture contract
- [`CONFORMANT_IMPLEMENTATIONS.md`](./CONFORMANT_IMPLEMENTATIONS.md) — the registry + the one claim form « Nika v1 Conformant — <Level> (spec <commit>) »
- [`governance/nep-0000-the-nep-process.md`](./governance/nep-0000-the-nep-process.md) — the evolution door, DORMANT until the v1 pre-freeze (pre-freeze: edit `spec/` directly, fixtures same-PR · [`governance/README.md`](./governance/README.md) says where the twenty folded laws live)
- [`governance/certifications.md`](./governance/certifications.md) — the earned-badges matrix with evidence links
- [`GLOSSARY.md`](./GLOSSARY.md) — canonical referents for overloaded words

## Editing rules

1. A count change = `canon.yaml` first, prose second (same commit).
2. Spec sections live in `spec/01-*.md` … — additive evolution,
   breaking changes need an engine-side MINOR + changelog entry.
3. Examples in `examples/*.nika.yaml` must stay valid against the spec.
4. Commit trailer: `Co-Authored-By: Nika 🦋 <nika@supernovae.studio>`.
