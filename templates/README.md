# Templates · instantiable skeletons (the deterministic authoring path)

> **Agents do not invent structure — they instantiate it.** Each
> template here is a COMPLETE, VALID workflow (gated by
> `conformance/runner.py all` on every push) with `# SLOT:` markers at
> every decision point. The path from intent to a correct file is
> mechanical: route → copy → fill slots → check → repair → re-check.
>
> Browse this pack as a register: <https://nika.sh/templates> (one page
> per skeleton, sha256-pinned copies) · machine catalog:
> <https://nika.sh/templates/catalog.json>.

## Intent → template routing (deterministic)

| Your intent sounds like… | Template | Patterns it locks in |
|---|---|---|
| « take data, produce words, save them » | [`chain`](chain.nika.yaml) | deterministic gather · one model job · explicit persist |
| « watch X, act when Y » | [`gate-and-act`](gate-and-act.nika.yaml) | jq extraction · CEL skip-gate · often zero model calls |
| « do this for EVERY item » | [`fanout`](fanout.nika.yaml) | runtime collection · the full leash (max_parallel · fail_fast · retry) |
| « only what changed since last run » / « survive bad input » | [`etl-state`](etl-state.nika.yaml) | state read→diff→write · `on_error: recover:` quarantine |
| « research / review / open-ended » | [`agent-loop`](agent-loop.nika.yaml) | plan-then-execute · default-deny tools · budgets · typed final message |
| « anything irreversible (deploy · send · publish) » | [`human-gated-ship`](human-gated-ship.nika.yaml) | parallel gates · assert · `nika:prompt` GO · `on_finally` record |
| « understand a site (domain · theme · assets) from a URL » | [`website-brief`](website-brief.nika.yaml) | fetch `traverse:` crawl · one typed infer · explicit persist · zero exec |
| « generate image/audio assets from a brief » | [`media-asset-pack`](media-asset-pack.nika.yaml) | `nika:image_generate` · `nika:jq` manifest · local/mock provider first |
| « call a product API: upload a file, then create from it » | [`api-upload-and-create`](api-upload-and-create.nika.yaml) | fetch `multipart:` upload · masked secrets header · mode/jq extraction |
| « read a system's state (docker · kubectl · gh), explain it, keep the report » | [`docker-report`](docker-report.nika.yaml) | argv-array exec (provable allowlist) · parallel reads · exec ledger · one artifact |

Composite jobs compose templates: a fanout whose merge feeds a
human-gated-ship, an etl-state whose delta fans out. Start from the
template matching the OUTER shape.

## The instantiation protocol (agents · follow exactly)

1. **Route** with the table above — one intent, one template.
2. **Copy** the file · rename it (kebab-case) · set `workflow:`.
3. **Fill every `# SLOT:` line** · delete the slot comment once filled.
   Creativity belongs ONLY in prompts, jq expressions and paths —
   never in structure.
4. **Check** · `nika check <file>` (engine) or
   `python3 conformance/runner.py validate <file>` (spec oracle).
5. **Repair** · every error names its rule — fix exactly that, nothing
   else. The recurring ones:
   - `NIKA-DAG-003` → you referenced `${{ tasks.X }}` without
     `depends_on: [X]`. Add the edge.
   - `NIKA-VAR-001` → undeclared `vars./with./secrets.` name. Declare
     it in the envelope or fix the typo. A declared `required: true` var
     is supplied at launch · `nika run <file> --var name=value`
     (repeatable).
   - `NIKA-PROVIDER` → `model:` must be `<provider>/<name>` with a
     canonical prefix (`canon.yaml` providers).
6. **Re-check until valid** · zero errors = done. Never ship unchecked.

## Guarantees

- Every template passes the same conformance gate as the examples —
  a template that drifts from the spec FAILS CI.
- Templates ship in the [versioned pack](../examples/manifest.yaml)
  (sha256 per file) — the engine embeds them (`nika new <template>`,
  planned) so instantiation works offline, version-locked.
- The [12 patterns](https://docs.nika.sh/guides/patterns) are the WHY
  behind every locked choice here; the
  [showcase](../examples/showcase/) shows each at full scale.

🦋 *Structure is instantiated, never invented · the slots are the only freedom.*
