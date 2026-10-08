# Access-harness behavioral contracts

Two families live here, both judged before or during the run, never by the
static gate (these fixtures use `input.nika`):

| Fixtures | Contract | Owner |
|---|---|---|
| `001` · `002` | the infer-grade meet of a subscription seat named by a launch pin | [02 §Subscription harness access](../../../../spec/02-verbs.md#subscription-harness-access-normative) |
| `003`+ | a selection declared in the file (`run.access` · `run.reasoning`) is honored exactly or refused before inference | [01 §run](../../../../spec/01-envelope.md#runaccess--runreasoning--the-route-and-the-native-effort-normative) · LAW-CONF-0501 |

The shape of a declaration is a separate, static question: its fixtures are
`core/envelope/033`–`050`, judged by `conformance/runner.py`. A workflow that
passes them proves nothing about any route.

## Access-selection fixture extension

These fixtures carry the infer-grade fields of the
[runtime README](../README.md#infer-grade-harness-fixture-extension) where they
need them, plus one invocation premise and one assertion block.

### `run.json` · `access_routes` · the injected route world

The adapter stages scripted peers from this declaration. It never discovers
a host binary, reads an account store or calls a real provider.

```json
{
  "access_routes": {
    "codex": {
      "acp": {
        "available": true,
        "config": "options",
        "readback": "confirmed",
        "default_model": "openai/gpt-5.4",
        "models": {
          "openai/gpt-5.5": { "effort": ["low", "medium", "high"] }
        },
        "prompt": "completes"
      },
      "cli": { "available": true },
      "api": { "configured": false }
    }
  }
}
```

| Field | Meaning |
|---|---|
| route key | a route id as `run.access.via` spells it (kebab-case) |
| `acp.available` | `false` · the route's ACP adapter is absent or not runnable here (a probe sees it before the run) |
| `acp.config` | `options` · the session exposes configuration options and returns the complete resulting configuration · `legacy` · the session only acknowledges a model request (no readback, no effort option) |
| `acp.readback` | `options` only · `confirmed` (default) or `unconfirmed` · whether the returned configuration holds the applied values |
| `acp.default_model` | the session's model before any selection |
| `acp.models` | the models the session advertises, each with the native effort values offered AFTER that model is selected (an empty list offers none) |
| `acp.prompt` | `completes` (default) · `session_dies` · the session ends after the first prompt is received, before any answer |
| `cli.available` | a direct, non-ACP CLI path for the same application is installed and signed in |
| `api.configured` | an API credential for the route is configured · the adapter serves it with a mock endpoint, never a real provider |
| `api.responder` | the model identity the mock endpoint names in its answer, verbatim · absent names none |

All fields are closed. `acp.config` and `acp.models` are required when
`acp.available` is `true`. Everything the fixture does not declare is absent,
never ambient.

### `expected-run.json` · `observed` · what the adapter saw

The run's own record (`receipt`) and the adapter's independent observation
(`observed`) are separate claims. A fixture asserts both when both matter; an
engine reporting its own success never discharges `observed`.

```json
{
  "observed": {
    "acp_config_before_first_prompt": { "model": "openai/gpt-5.5", "effort": "high" },
    "acp_prompts": 1,
    "api_inference_requests": 0,
    "cli_invocations": 0
  }
}
```

| Field | Observation |
|---|---|
| `acp_config_before_first_prompt` | the model and effort the peer had received and accepted through its own selection methods, and still held, when its first prompt arrived · a session default is never an applied value · an absent `effort` means none was applied |
| `acp_prompts` | prompt requests received by the scripted ACP peers (session setup and configuration are discovery, never counted) |
| `api_inference_requests` | requests received by the mock API endpoints, except a model listing (`GET /v1/models`, which is discovery) |
| `cli_invocations` | direct CLI invocations: product-CLI processes started with any argv other than the route's exact discovery and sign-in probes (a version, a sign-in status or a capability listing), which are recorded separately and never counted |

Counts are exact integers. A refusal before inference asserts zeros. An
argv the adapter does not list as a probe counts as a direct invocation,
so a forbidden substitution cannot hide behind a probe-like command.

### `receipt` · the four facts kept apart

For an access-selection fixture the receipt fields are:

| Field | Fact |
|---|---|
| `access_via` · `protocol` | the route and the connection actually used |
| `requested_model` · `requested_effort` | what the file declared (`null` effort when none was declared) |
| `transmitted_model` · `transmitted_effort` | what the engine sent to the route |
| `configured_model` · `configured_effort` | what the route confirmed on readback · `null` when it confirmed nothing |
| `model_evidence` | `configured` (read back) or `accepted_request` (acknowledged only) |
| `responding_model` | the identity the route attested, verbatim · `null` when unattested (an ACP session names no responder) |

A requested or acknowledged value is never promoted into `configured_*` or
`responding_model`. A receipt assertion names only the fields it judges: an
absent field is not asserted, while an explicit `null` asserts that the fact
is unknown.

### Where a refusal happens

Every refusal sends zero inference requests; the fixtures also pin WHERE the
reference engine refuses, because that decides the observable shape:

| Plane | When | Fixture shape |
|---|---|---|
| admission | the file and the probed routes already decide it (unknown route, a protocol the route does not speak, an absent adapter, a contradicting launch option, `infer:` with no attested ACP one-shot) | `admission.accepted: false` · no workflow or task event |
| session | only the live session reveals it (a model it does not advertise, an effort it does not offer after the model is selected, a read-back that does not hold the selection) | the task fails before its first prompt · `observed.acp_prompts: 0` |
| mid-run | the session dies after the prompt | the task fails · no other route is tried |

Recorded codes are the reference engine's execution-access family
(`NIKA-1800`..`NIKA-1849`); the spec mints none of them. A transient session
failure may be retried on the SAME declared route, never on another.

## The command adapter

[`scripts/runtime_access_adapter.py`](../../../../scripts/runtime_access_adapter.py)
executes this extension for the reference engine, driven by
[`scripts/runtime-differential.py`](../../../../scripts/runtime-differential.py).
Its route registry is a closed binding table of the reference engine's
facts (today `codex` for an agent application, `openai` for an API). A
route a fixture stages outside that table is `UNSUPPORTED`. Another
implementation needs its own admitted adapter, never a fallback.

One fixture is one isolated stage: a private `HOME`, `TMPDIR`, project
(the workflow's exact bytes) and `PATH` (the stage's `bin` before
`/usr/bin:/bin`, refused when either system directory holds a registry
binary), an explicit environment, and a fake key. The adapter then runs
`nika run input.nika --json` once, adding `--access <access>` when
`run.json` declares one. It reads two independent records.

| Declared | Staged |
|---|---|
| `acp.available: true` | the route's ACP speaker: a scripted agent that answers `initialize` with an identity the engine's registry admits (never an audited completion profile's identity) |
| `acp.available` or `cli.available` | the route's product CLI, present and signed in, because the reference engine asks it for the ACP route's sign-in too. Only `cli.available` opens its direct invocation, which then answers one scripted turn; otherwise it refuses |
| `api` | a loopback inference endpoint; the engine's base-URL override always points at it, and only `configured: true` adds the fake key and a scripted answer |

The scripted ACP agent offers each model of `acp.models` as one select
value whose `value` and `name` are the fixture's model id verbatim. It
derives no native, alias or display name: an engine that sends another
spelling has sent another model. Options are `model` (category `model`)
and the route's reasoning option (category `thought_level`), whose values
are those offered for the current model. Without `default_model` the first
advertised model is current. A model's current effort starts at its first
offered value. An unoffered value is refused (`-32602`) and changes
nothing. A model change keeps the current effort only when the new model
offers it; otherwise the effort is reset and no longer counts as applied.
An `unconfirmed` read-back answers with the configuration unchanged by the
request. A `legacy` session advertises a model list, acknowledges
`session/set_model` with `{}` and exposes no configuration option. A prompt
answers one text chunk and `end_turn`, or, with `session_dies`, is logged
and ends the process unanswered.

The receipt is read from each asserted task's single terminal frame. The
frame must carry `access_id`, `access_requirement` and an `access_selection`
under `nika/access-selection@1`. That name pins the closed shape and
vocabulary: an unknown key, a mistyped fact, an acknowledged request
recorded as `configured`, a configured value without its source, or a
responder that disagrees with its evidence is invalid evidence, a
divergence. Another schema name has no admitted reading here
(`UNSUPPORTED`, never hiding a divergence of the same run).

| Receipt field | Engine record |
|---|---|
| `access_via` | `access_id` |
| `protocol` | `access_selection.protocol` |
| `requested_*` · `transmitted_*` · `configured_*` | `access_selection.model` / `.effort` · `requested` · `transmitted` · `configured` |
| `model_evidence` | `access_selection.model.configured_source`: `confirmed_selection` reads `configured`, `accepted_request` reads `accepted_request`, any other value stays itself |
| `responding_model` | `access_selection.responder.model` |

The run's two records of one selection must also agree. The
`access_requirement` restates the file's `run.access` and `run.reasoning`
literally. Its effort is the selection's requested effort, its protocol is
the one travelled, and its `via` is the `access_id` that served.

An asserted `transmitted_*` or `configured_*` fact is also judged on the
routes' own records, so a truthful-looking receipt cannot cover another
transmission. Over ACP the record comes from the session the first prompt
reached, else the last one opened. A dimension's transmitted value is the
last value that session received for it, accepted or refused. Its configured
value is the session's own read-back of a dimension that was sent, and
nothing otherwise. Both are compared verbatim. Over an API, every inference
request body is compared in the route's wire form. That form is the binding
table's explicit, route-bound mapping: the `openai` body names
`openai/<name>` as `<name>`, and an id of another provider has no wire form
there. An API reads back no configuration.

### Outcomes

- `FIXTURE-ERROR` · a malformed declaration or expectation, before any
  process starts: an unknown key, a mistyped value, missing `observed`
  counts, an effort on a legacy session, a receipt on a refused admission.
- `UNSUPPORTED` · a premise this adapter has no seam to stage. Injected
  `harness_attestations` (the reference engine admits no injected
  attestation). An `infer:` task on an agent-application route, whose
  subscription-harness attestation premise only that injection could
  state. An `env` overlay beside the route world, an unbound route, or an
  unadvertised `default_model`. Also, after the run: an admitted-run
  fixture that the engine refused before any event because the staged
  loopback endpoint is unpriced to it and its unknown-cost review needs a
  fresh interactive choice. The adapter never answers or bypasses that
  review; any request it observed keeps the divergence.
- `ENGINE-ERROR` · a crash, a signal, a timeout, or nothing at all on
  stdout, whatever the exit. An empty reply is no refusal and no run, so it
  never reaches the admission comparison.
- `DIVERGE` · every difference named: the run door's admission and
  execution judgment, each `observed` count and configuration, each
  asserted receipt field and each record that disagrees.
- `AGREE` · none of the above.

The sweep prints the adapter's own notes beside each verdict: what was
staged, every ACP process and selection outcome, the CLI probes apart from
the direct invocations, the inference requests and the engine's refusal
words. They explain a verdict and never change it. With
`NIKA_ACCESS_EVIDENCE_DIR=<dir>`, each stage (wrappers, peer code,
configuration, peer logs, engine traces), the raw engine output, a
`record.json` and an `index.json` naming the engine binary's SHA-256 and
the specification commit are kept outside the repository.

## Status

The adapter's own laws (`scripts/test_runtime_access_adapter.py`, run by
`scripts/test_runtime_differential.py`) drive scripted engine doubles
through the real stage: a conformant double agrees, and each substitution,
late or unconfirmed configuration, lost or repeated event, mislabelled
receipt or crash is caught. These are adapter tests, never engine results.
A fixture's engine result is only what a sweep against an identified binary
reports.
