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

## Filled lessons and bounds

[INDEX.md](INDEX.md) is the complete generated authoring index. The filled
lessons are generated from their skeletons using [rehearsals.yaml](rehearsals.yaml):
edit the template logic once, then run `python3 scripts/template-rehearsals.py --write`.
The same lesson enters the native pack and the managed documentation blocks.
The CI check rejects projection drift, and each lesson keeps its template's
independently specified golden output.

The boundary cases in [rehearsal-cases.json](rehearsal-cases.json) exercise empty,
exact-limit and oversized inputs, invalid fields, conflicting duplicates,
incorrect decision rules and narrow recovery. The engine's
`scripts/authoring-gauntlet.py` executes these cases with mock inference and
asserts that refused inputs never start the protected downstream tasks.


## The guarantee

Every template in this directory **runs green in an empty directory once
its named slots are filled** — offline, with no API key, no fixture, and
nothing installed. An unfilled scaffold refuses at `nika check`; it never
spends or writes output that could be mistaken for a result. That is what
makes a skeleton worth copying: you scaffold it, fill the explicit holes,
run it, watch it work, and only then point it at your own data.

```bash
nika compile --list                          # exact skeleton names
nika compile chain --json                    # preview only · no write
nika compile chain my-first.nika \
  --answer 'tasks.think.infer.prompt="Summarize the gathered text in five bullets."'
nika check my-first.nika
nika run   my-first.nika --model mock/echo   # SEE IT WORK
```

`nika compile` writes only a **Ready** candidate to an **explicit**
`*.nika` destination (`DEST` or `--output`). Omit the destination to
preview. An incomplete result includes `questions` and the candidate; it
does not write. Existing destinations require `--force`. Unsupported
words stay incomplete — there is no closest-skeleton substitute and no
`nika new` verb.

How each one holds that promise:

- **`--model mock/echo`** — the offline seat. Deterministic, zero keys.
  Compile does not pick a paid provider or access from ambient
  credentials; skeletons keep their authored `model: mock/echo`. Choose
  provider and access explicitly for a real run; `--model mock/echo`
  always keeps the rehearsal available.
- **`on_error: recover:`** — where a template reads a file, calls an API or
  shells out, a literal recovery value stands in until you wire the real
  thing. Every one of those blocks says, in place, to delete it once the
  source is real — a rehearsal value left in production hides failures.
- **the two gated skeletons hold a real human decision.** Both block (no
  `default:`): headless they PAUSE (exit 4 · durable, not an error) and
  print their own resume command. Fail-closed belongs to the INVOCATION,
  never to the file — `nika run <file> --answer human=false` answers NO
  unattended (measured: rc=0, the act settles skipped). A `default: false`
  in the file looks the same and is not: a defaulted gate is not blocking,
  so beside real gates (a private read) the lethal trifecta is complete and
  the file is refused `NIKA-SEC-009` at check (measured on 0.118.7 ·
  `human-gated-ship.negative.yaml` pins that refusal).

## Intent → template routing (deterministic)

The primary axis is the workflow **form**. A domain such as documents, media
or operations is a secondary tag, because the same form composes across jobs.
The machine source for both fields is `canon/templates/registry.yaml`.

| Your intent sounds like… | Template | Primary form | Domain tags | Patterns it locks in |
|---|---|---|---|---|
| « take data, produce words, save them » | [`chain`](chain.nika) | `linear` | `content` | deterministic gather · one model job · explicit persist |
| « watch X, act when Y » | [`gate-and-act`](gate-and-act.nika) | `conditional-gate` | `monitoring` | jq extraction · CEL skip-gate · often zero model calls |
| « do this for EVERY item » | [`fanout`](fanout.nika) | `fanout` | `batch` | runtime collection · the full leash (`for_each.max_parallel` · `for_each.fail_fast` · retry) |
| « only what changed since last run » / « survive bad input » | [`etl-state`](etl-state.nika) | `state-resume` | `etl` | state read→parse→diff→write · `on_error: on_codes:` quarantine |
| « research / review / open-ended » | [`agent-loop`](agent-loop.nika) | `agent-loop` | `research` · `review` | plan-then-execute · default-deny tools · budgets · engine-owned typed result |
| « anything irreversible (deploy · send · publish) » | [`human-gated-ship`](human-gated-ship.nika) | `human-gate` | `release` | parallel gates (`nika:grep` evidence · `exec:` command) · assert · a BLOCKING `nika:prompt` · `after: {…: terminal}` record |
| « understand a site (domain · theme · assets) from a URL » | [`website-brief`](website-brief.nika) | `linear` | `website` | fetch `traverse:` crawl · one typed infer · explicit persist · zero exec |
| « generate image/audio assets from a brief » | [`media-asset-pack`](media-asset-pack.nika) | `linear` | `media` | `nika:image_generate` · `nika:jq` manifest · local/mock provider first |
| « call a product API: upload a file and create from it » | [`api-upload-and-create`](api-upload-and-create.nika) | `api-upload` | `product-api` · `upload` | fetch `multipart:` (file + text parts) · masked secrets header · mode/jq extraction |
| « read a system's state (docker · kubectl · gh), explain it, keep the report » | [`docker-report`](docker-report.nika) | `parallel-fan-in` | `operations` · `report` | argv-array exec (provable allowlist) · parallel reads · one artifact |
| « extract fields from a document and keep the evidence » | [`document-to-fields`](document-to-fields.nika) | `structured-extraction` | `documents` | trim · nonempty assertion · typed fields · exact source anchors |
| « answer from a corpus, or say that the answer is unknown » | [`corpus-qa`](corpus-qa.nika) | `retrieval` | `knowledge` | conflicting-id refusal · idempotent sort/unique index · empty citations on unknown |
| « classify facts and route them by a governed law » | [`classify-and-route`](classify-and-route.nika) | `decision-routing` | `operations` | typed facts · EvidenceSnapshot · `nika:decide` · fixture proof |
| « critique and improve a draft for a fixed number of rounds » | [`evaluate-and-optimize`](evaluate-and-optimize.nika) | `bounded-loop` | `quality` | two unrolled revisions · score-only final evaluation · every infer capped |

Composite jobs compose templates: a fanout whose merge feeds a
human-gated-ship, an etl-state whose delta fans out. Start from the
template matching the OUTER shape.

Not sure? List exact names; do not send arbitrary natural language to
Compile — unsupported intent stays incomplete.

```bash
nika compile --list                 # the set
nika compile chain --json           # preview · status + questions
```

## The instantiation protocol (agents · follow exactly)

1. **Route** with the table above — one intent, one template.
2. **Compile** · `nika compile <name> --json` until `status` is `ready`
   (answer every mandatory question with repeatable
   `--answer KEY=JSON_LITERAL`). Then write with an explicit destination:
   `nika compile <name> <dest>.nika` plus the same `--answer` flags.
   Compile sets `nika:` from the destination stem. Preview (`written: null`)
   is the default when `DEST` / `--output` is omitted.
3. **Fill every `<SLOT: …>` value** · the marker lives in the value because
   comments are not part of the parsed workflow.
   Creativity belongs ONLY in prompts, jq expressions and paths —
   never in structure.
4. **Check** · `nika check <file> --native-strict` · zero errors AND zero
   hints, unless a hint is one the file documents in place (three are).
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
   - `NIKA-SEC-004` → the boundary refused an effect — at CHECK when the
     miss is static (the report prints the exact fix · zero turns paid),
     at RUN when the value is computed. Grant the exact thing it names —
     never widen to `**` to make a message go away.
   - `NIKA-PROVIDER` → `model:` must be `<provider>/<name>` with a
     canonical prefix (`canon.yaml` providers).

## Three hints that are meant to stay

Most hints are defects. Three, in the two gated skeletons, are named in
place — two are the checker naming a real pause, one is the checker's limit:

- **`etl-state`** and **`human-gated-ship`** carry `[headless-prompt]`. The
  blocking gate is deliberate — adding the `default:` the hint suggests
  completes the lethal trifecta and lights `NIKA-SEC-009` (measured on
  0.118.7 for both · the human-gated-ship negative pins it).
- **`etl-state`** also carries `[inputs]` on its cursor file, and that hint
  is wrong about the run: the `on_error: on_codes: [NIKA-BUILTIN-READ-001]`
  recover carries the first run (measured). The checker names static
  `nika:read` paths without modelling recovery — a checker limitation, and
  the template says which of its two hints that is.
- **`fanout`** and **`api-upload-and-create`** used to carry
  `[NIKA-DRIFT-001]` on an `fs.read` entry the detector could not model
  (a `nika:glob` walk · a `multipart:` file part). The detector learned
  both — measured on `nika-cli 0.107`, neither file prints a hint today.
- **`fanout`** and **`media-asset-pack`** used to carry `[unproven-law]`.
  `fanout` now proves its fan-in law on a const fixture (`prove` →
  `law_holds`); `media-asset-pack` builds its manifest from the generator's
  own record, which is not a law at all — measured on 0.118.7, neither
  prints a hint. What `fanout` keeps is not a hint: `⚠ COST … 1 uncapped
  task` is a runtime fan by construction, and the run's `--max-cost-usd` is
  its cap (the template says so).

When a hint tells you to remove something, run the file before you believe it.

## Guarantees

- Every template passes the same conformance gate as the examples —
  a template that drifts from the spec FAILS CI.
- Every new form keeps its refusal beside it as `<id>.negative.yaml` and its
  replay pin as `<id>.nika.golden.json`. `conformance/runner.py all`
  requires every adjacent negative to remain invalid, and fails if the
  negative corpus is empty. Its reference oracle may report a namespace or
  refuse at an earlier validation layer. The negative's `# Expected` header
  names the exact diagnostic to assert against the native engine;
  `nika test <id>.nika`
  proves the typed outputs against the committed golden.
- Templates ship in the [versioned pack](../examples/manifest.yaml)
  (sha256 per file) — the engine embeds them, so `nika compile` works
  offline and version-locked.
- The [12 patterns](https://docs.nika.sh/guides/patterns) are the WHY
  behind every locked choice here; the
  [the jobs](../examples/README-jobs.md) show each at full scale.
- The contract every file in this corpus honours:
  [`../examples/CONVENTIONS.md`](../examples/CONVENTIONS.md).

A skeleton supplies a tested starting shape; adapt it to the actual job and recheck its contracts.
