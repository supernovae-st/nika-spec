# Templates · instantiable skeletons (the deterministic authoring path)

> **Agents do not invent structure — they instantiate it.** Each template
> here is a COMPLETE, VALID workflow with `# SLOT:` markers at every
> decision point. The path from intent to a correct file is mechanical:
> route → copy → fill slots → check → run → repair.
>
> Browse this pack as a register: <https://nika.sh/templates> (one page
> per skeleton, sha256-pinned copies) · machine catalog:
> <https://nika.sh/templates/catalog.json>.

## The guarantee

Every template in this directory **runs green in an empty directory** —
offline, with no API key, no fixture, and nothing installed. That is what
makes a skeleton worth copying: you scaffold it, you run it, you watch it
work, and only then do you point it at your own data.

```bash
nika new --from chain my-first.nika.yaml   # scaffold
nika check my-first.nika.yaml              # audit
nika run   my-first.nika.yaml --model mock/echo   # SEE IT WORK
```

How each one holds that promise:

- **`--model mock/echo`** — the offline seat. Deterministic, zero keys. The
  `model:` line in each file is a SLOT naming a real local seat that was
  measured, but no seat is needed to run the skeleton.
- **`on_error: recover:`** — where a template reads a file, calls an API or
  shells out, a literal recovery value stands in until you wire the real
  thing. Every one of those blocks says, in place, to delete it once the
  source is real — a rehearsal value left in production hides failures.
- **the two gated skeletons pause, they do not fail.** `etl-state` and
  `human-gated-ship` stop at a human decision (exit 4 · durable, not an
  error) and print their own resume command.

## Intent → template routing (deterministic)

| Your intent sounds like… | Template | Patterns it locks in |
|---|---|---|
| « take data, produce words, save them » | [`chain`](chain.nika.yaml) | deterministic gather · one model job · explicit persist |
| « watch X, act when Y » | [`gate-and-act`](gate-and-act.nika.yaml) | jq extraction · CEL skip-gate · often zero model calls |
| « do this for EVERY item » | [`fanout`](fanout.nika.yaml) | runtime collection · the full leash (max_parallel · fail_fast · retry) |
| « only what changed since last run » / « survive bad input » | [`etl-state`](etl-state.nika.yaml) | state read→parse→diff→write · `on_error: on_codes:` quarantine |
| « research / review / open-ended » | [`agent-loop`](agent-loop.nika.yaml) | plan-then-execute · default-deny tools · budgets · engine-owned typed result |
| « anything irreversible (deploy · send · publish) » | [`human-gated-ship`](human-gated-ship.nika.yaml) | parallel gates · assert · `nika:prompt` GO · `on_finally` record |
| « understand a site (domain · theme · assets) from a URL » | [`website-brief`](website-brief.nika.yaml) | fetch `traverse:` crawl · one typed infer · explicit persist · zero exec |
| « generate image/audio assets from a brief » | [`media-asset-pack`](media-asset-pack.nika.yaml) | `nika:image_generate` · `nika:jq` manifest · local/mock provider first |
| « call a product API: upload a file and create from it » | [`api-upload-and-create`](api-upload-and-create.nika.yaml) | fetch `multipart:` (file + text parts) · masked secrets header · mode/jq extraction |
| « read a system's state (docker · kubectl · gh), explain it, keep the report » | [`docker-report`](docker-report.nika.yaml) | argv-array exec (provable allowlist) · parallel reads · one artifact |

Composite jobs compose templates: a fanout whose merge feeds a
human-gated-ship, an etl-state whose delta fans out. Start from the
template matching the OUTER shape.

Not sure? Ask the router in plain words:

```bash
nika new --from '?'                                  # list the set
nika new --from "watch a price and ping me" p.nika.yaml   # routes to the closest skeleton
```

## The instantiation protocol (agents · follow exactly)

1. **Route** with the table above — one intent, one template.
2. **Copy** · `nika new --from <name> <dest>.nika.yaml` · set `workflow:`.
3. **Fill every `# SLOT:` line** · delete the slot comment once filled.
   Creativity belongs ONLY in prompts, jq expressions and paths —
   never in structure.
4. **Check** · `nika check <file> --native-strict` · zero errors AND zero
   hints, unless a hint is one the file documents in place (two are).
5. **Run** · `nika run <file>`. **A file that has not been run is not
   finished** — `check` cannot see interpolated paths, so a permit that
   reads fine can still refuse mid-run.
6. **Repair** · every error names its rule — fix exactly that, nothing
   else. The recurring ones:
   - `NIKA-DAG-003` → you referenced `${{ tasks.X }}` without
     the boundary. Hoist the reference into `with:` — the binding IS the edge.
   - `NIKA-VAR-001` → undeclared `inputs./config./const./secrets./with.` name.
     Declare it in the matching envelope authority or fix the typo. A
     declared `required: true` input is supplied at launch ·
     `nika run <file> --var name=value` (repeatable).
   - `NIKA-SEC-004` → the boundary refused an effect at RUN. Grant the
     exact thing it names — never widen to `**` to make a message go away.
   - `NIKA-PROVIDER` → `model:` must be `<provider>/<name>` with a
     canonical prefix (`canon.yaml` providers).

## Two hints that are meant to stay

Most hints are defects. Two, in these files, are the checker
over-approximating, and the templates say so in place:

- **`etl-state`** carries `[headless-prompt]` and `[inputs]`. The blocking
  gate is deliberate — adding the `default:` the hint suggests completes
  the lethal trifecta and lights `NIKA-SEC-009`.
- **`fanout`** and **`api-upload-and-create`** carry `[NIKA-DRIFT-001]` on
  an `fs.read` entry. The drift detector does not model a `nika:glob` walk
  or a `multipart:` file part as a read; the runtime does. **Following that
  hint deletes the entry and kills the run.**

When a hint tells you to remove something, run the file before you believe it.

## Guarantees

- Every template passes the same conformance gate as the examples —
  a template that drifts from the spec FAILS CI.
- Templates ship in the [versioned pack](../examples/manifest.yaml)
  (sha256 per file) — the engine embeds them, so `nika new` works
  offline and version-locked.
- The [12 patterns](https://docs.nika.sh/guides/patterns) are the WHY
  behind every locked choice here; the
  [the jobs](../examples/README-jobs.md) show each at full scale.
- The contract every file in this corpus honours:
  [`../examples/CONVENTIONS.md`](../examples/CONVENTIONS.md).

🦋 *Structure is instantiated, never invented · the slots are the only freedom.*
