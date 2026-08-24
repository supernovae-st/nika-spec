# Templates · instantiable skeletons (the deterministic authoring path)

> **Agents do not invent structure — they instantiate it.** Each template
> here is a complete scaffold with `<SLOT: …>` values at every decision
> point. Those values make `nika check` refuse until the author fills them;
> comments cannot carry that invariant because YAML discards comments. The
> path from intent to a correct file is mechanical:
> route → copy → fill slots → check → run → repair.
>
> Browse this pack as a register: <https://nika.sh/templates> (one page
> per skeleton, sha256-pinned copies) · machine catalog:
> <https://nika.sh/templates/catalog.json>.

## The guarantee

Every template in this directory **runs green in an empty directory once
its named slots are filled** — offline, with no API key, no fixture, and
nothing installed. An unfilled scaffold refuses at `nika check`; it never
spends or writes output that could be mistaken for a result. That is what
makes a skeleton worth copying: you scaffold it, fill the explicit holes,
run it, watch it work, and only then point it at your own data.

```bash
nika new --from chain my-first.nika.yaml   # scaffold
nika check my-first.nika.yaml              # names every slot still to fill
nika run   my-first.nika.yaml --model mock/echo   # SEE IT WORK
```

How each one holds that promise:

- **`--model mock/echo`** — the offline seat. Deterministic, zero keys.
  `nika new` replaces a template's model with a ready model seat when the
  current binary can run it; `--model mock/echo` always keeps the rehearsal
  available without requiring that seat.
- **`on_error: recover:`** — where a template reads a file, calls an API or
  shells out, a literal recovery value stands in until you wire the real
  thing. Every one of those blocks says, in place, to delete it once the
  source is real — a rehearsal value left in production hides failures.
- **the two gated skeletons hold a real human decision.** `etl-state`
  blocks (no `default:`): headless it PAUSES (exit 4 · durable, not an
  error) and prints its own resume command. `human-gated-ship` fails
  CLOSED instead — its `default: false` answers NO for an unattended run
  (measured: rc=0, the act settles skipped) · delete that line and it
  pauses like etl-state.

## Intent → template routing (deterministic)

The primary axis is the workflow **form**. A domain such as documents, media
or operations is a secondary tag, because the same form composes across jobs.
The machine source for both fields is `canon/templates/registry.yaml`.

| Your intent sounds like… | Template | Primary form | Domain tags | Patterns it locks in |
|---|---|---|---|---|
| « take data, produce words, save them » | [`chain`](chain.nika.yaml) | `linear` | `content` | deterministic gather · one model job · explicit persist |
| « watch X, act when Y » | [`gate-and-act`](gate-and-act.nika.yaml) | `conditional-gate` | `monitoring` | jq extraction · CEL skip-gate · often zero model calls |
| « do this for EVERY item » | [`fanout`](fanout.nika.yaml) | `fanout` | `batch` | runtime collection · the full leash (`for_each.max_parallel` · `for_each.fail_fast` · retry) |
| « only what changed since last run » / « survive bad input » | [`etl-state`](etl-state.nika.yaml) | `state-resume` | `etl` | state read→parse→diff→write · `on_error: on_codes:` quarantine |
| « research / review / open-ended » | [`agent-loop`](agent-loop.nika.yaml) | `agent-loop` | `research` · `review` | plan-then-execute · default-deny tools · budgets · engine-owned typed result |
| « anything irreversible (deploy · send · publish) » | [`human-gated-ship`](human-gated-ship.nika.yaml) | `human-gate` | `release` | parallel gates · assert · `nika:prompt` GO · `after: {…: terminal}` record |
| « understand a site (domain · theme · assets) from a URL » | [`website-brief`](website-brief.nika.yaml) | `linear` | `website` | fetch `traverse:` crawl · one typed infer · explicit persist · zero exec |
| « generate image/audio assets from a brief » | [`media-asset-pack`](media-asset-pack.nika.yaml) | `linear` | `media` | `nika:image_generate` · `nika:jq` manifest · local/mock provider first |
| « call a product API: upload a file and create from it » | [`api-upload-and-create`](api-upload-and-create.nika.yaml) | `api-upload` | `product-api` · `upload` | fetch `multipart:` (file + text parts) · masked secrets header · mode/jq extraction |
| « read a system's state (docker · kubectl · gh), explain it, keep the report » | [`docker-report`](docker-report.nika.yaml) | `parallel-fan-in` | `operations` · `report` | argv-array exec (provable allowlist) · parallel reads · one artifact |
| « extract fields from a document and keep the evidence » | [`document-to-fields`](document-to-fields.nika.yaml) | `structured-extraction` | `documents` | trim · nonempty assertion · typed fields · exact source anchors |
| « answer from a corpus, or say that the answer is unknown » | [`corpus-qa`](corpus-qa.nika.yaml) | `retrieval` | `knowledge` | conflicting-id refusal · idempotent sort/unique index · empty citations on unknown |
| « classify facts and route them by a governed law » | [`classify-and-route`](classify-and-route.nika.yaml) | `decision-routing` | `operations` | typed facts · EvidenceSnapshot · `nika:decide` · fixture proof |
| « critique and improve a draft for a fixed number of rounds » | [`evaluate-and-optimize`](evaluate-and-optimize.nika.yaml) | `bounded-loop` | `quality` | two unrolled revisions · score-only final evaluation · every infer capped |

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
2. **Copy** · `nika new --from <name> <dest>.nika.yaml` · set `nika:` to the
   file's own kebab-case name.
3. **Fill every `<SLOT: …>` value** · the marker lives in the value because
   comments are not part of the parsed workflow.
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
   - `NIKA-VAR-001` → undeclared `inputs./const./secrets./with.` name.
     Declare it in the matching envelope authority or fix the typo. A
     declared `required: true` input is supplied at launch ·
     `nika run <file> --var name=value` (repeatable); a `required: false`
     entry with a `default:` is the deployment's, never the caller's.
   - `NIKA-SEC-004` → the boundary refused an effect at RUN. Grant the
     exact thing it names — never widen to `**` to make a message go away.
   - `NIKA-PROVIDER` → `model:` must be `<provider>/<name>` with a
     canonical prefix (`canon.yaml` providers).

## Two hints that are meant to stay

Most hints are defects. Two, both in `etl-state`, are the checker
over-approximating, and the template says so in place:

- **`etl-state`** carries `[headless-prompt]` and `[inputs]`. The blocking
  gate is deliberate — adding the `default:` the hint suggests completes
  the lethal trifecta and lights `NIKA-SEC-009`.
- **`fanout`** and **`api-upload-and-create`** used to carry
  `[NIKA-DRIFT-001]` on an `fs.read` entry the detector could not model
  (a `nika:glob` walk · a `multipart:` file part). The detector learned
  both — measured on `nika-cli 0.107`, neither file prints a hint today.

When a hint tells you to remove something, run the file before you believe it.

## Guarantees

- Every template passes the same conformance gate as the examples —
  a template that drifts from the spec FAILS CI.
- Every new form keeps its refusal beside it as `<id>.negative.yaml` and its
  replay pin as `<id>.nika.yaml.golden.json`. The negative names the exact
  diagnostic the wrong form must keep emitting; `nika test <id>.nika.yaml`
  proves the typed outputs against the committed golden.
- Templates ship in the [versioned pack](../examples/manifest.yaml)
  (sha256 per file) — the engine embeds them, so `nika new` works
  offline and version-locked.
- The [12 patterns](https://docs.nika.sh/guides/patterns) are the WHY
  behind every locked choice here; the
  [the jobs](../examples/README-jobs.md) show each at full scale.
- The contract every file in this corpus honours:
  [`../examples/CONVENTIONS.md`](../examples/CONVENTIONS.md).

🦋 *Structure is instantiated, never invented · the slots are the only freedom.*
