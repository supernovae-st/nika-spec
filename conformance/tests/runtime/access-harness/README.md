# Access-harness behavioral contracts

Two families live here, both judged before or during the run, never by the
static gate (these fixtures use `input.nika`):

| Fixtures | Contract | Owner |
|---|---|---|
| `001` · `002` | the infer-grade meet of a subscription seat named by a launch pin | [02 §Subscription harness access](../../../../spec/02-verbs.md#subscription-harness-access-normative) |
| `003`+ | a selection declared in the file (`run.access` · `run.reasoning`) is honored exactly or refused before inference | [01 §run](../../../../spec/01-envelope.md#runaccess--runreasoning--the-route-and-the-native-effort-normative) · LAW-CONF-0501 |

The shape of a declaration is a separate, static question: its fixtures are
`core/envelope/033`–`053` and `056`–`065`, judged by `conformance/runner.py`.
A workflow that passes them proves nothing about any route.

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
          "openai/gpt-5.4": { "effort": ["low", "medium"] },
          "openai/gpt-5.5": {
            "effort": ["low", "medium", "high"],
            "service_tier": ["standard", "fast"]
          }
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
| `acp.config` | `options` · the session exposes configuration options and returns the complete resulting configuration · `legacy` · the session only acknowledges a model request (no readback, no effort option, no service tier option) |
| `acp.readback` | `options` only · `confirmed` (default) or `unconfirmed` · whether the returned configuration holds the applied values |
| `acp.default_model` | the session's model before any selection |
| `acp.models` | the models the session advertises, each with the native effort values offered AFTER that model is selected (an empty list offers none) |
| `acp.models.<model>.service_tier` | optional · the service tiers the session offers AFTER that model is selected, written in the language's words (`standard` · `fast`), in the session's own order · the first one is the session's default · absent or empty, the model has no speed control and the session lists no tier option |
| `acp.prompt` | `completes` (default) · `session_dies` · the session ends after the first prompt is received, before any answer |
| `cli.available` | a direct, non-ACP CLI path for the same application is installed and signed in |
| `api.configured` | an API credential for the route is configured · the adapter serves it with a mock endpoint, never a real provider |
| `api.responder` | the model identity the mock endpoint names in its answer, verbatim · absent names none |

All fields are closed. `acp.config` and `acp.models` are required when
`acp.available` is `true`. Everything the fixture does not declare is absent,
never ambient. A tier offer is the one premise written in the language's
words: the route's binding, not the fixture, says which native option and
values carry them (see [the command adapter](#the-command-adapter)).

### `expected-run.json` · `observed` · what the adapter saw

The run's own record (`receipt`) and the adapter's independent observation
(`observed`) are separate claims. A fixture asserts both when both matter; an
engine reporting its own success never discharges `observed`.

```json
{
  "observed": {
    "acp_config_before_first_prompt": {
      "model": "openai/gpt-5.5",
      "effort": "high",
      "service_tier": "fast"
    },
    "acp_prompts": 1,
    "api_inference_requests": 0,
    "cli_invocations": 0
  }
}
```

| Field | Observation |
|---|---|
| `acp_config_before_first_prompt` | the model, effort and service tier the peer had received and accepted through its own selection methods, and still held, when its first prompt arrived · a session default is never an applied value · an absent `effort` or `service_tier` means none was applied · `service_tier` is the language word (`standard` · `fast`) that the route's binding gives the native value the peer held |
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
| `requested_service_tier` | the language word the file declared (`standard` · `fast`) · `null` when it declared none |
| `offered_service_tier` | the native values the session listed for the route's tier option when the tier was judged, in the session's own order |
| `transmitted_service_tier` · `configured_service_tier` | the native value the engine sent to the route · the native value the route confirmed on readback |
| `turn_service_tier` · `effective_service_tier` | the tier carried on the turn itself · the tier the provider reports · facts only a witness can state, so both are `null` on a scripted peer |

A requested or acknowledged value is never promoted into `configured_*` or
`responding_model`, and a confirmed tier is never promoted into
`turn_service_tier` or `effective_service_tier`. A run that declares no tier
records none: every tier field is then `null`. A receipt assertion names only
the fields it judges: an absent field is not asserted, while an explicit
`null` asserts that the fact is unknown.

### Where a refusal happens

Every refusal sends zero inference requests; the fixtures also pin WHERE the
reference engine refuses, because that decides the observable shape:

| Plane | When | Fixture shape |
|---|---|---|
| admission | the file and the probed routes already decide it (unknown route, a protocol the route does not speak, an absent adapter, a contradicting launch option, `infer:` with no attested ACP one-shot, a service tier on a route that binds none) | `admission.accepted: false` · no workflow or task event |
| session | only the live session reveals it (a model it does not advertise, an effort it does not offer after the model is selected, a service tier it does not offer after the model and the effort are selected or has no option to apply, a read-back that does not hold the selection) | the task fails before its first prompt · `observed.acp_prompts: 0` |
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

The table also binds the language's two service tier words to each route's
own control. For `codex` that control is the session option `fast-mode`
(category `model_config`, a select): `on` is the route's value for `fast`
and `off` its value for `standard`. The `openai` API route binds neither
word. Every native tier value in a fixture comes from this binding.

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
spelling has sent another model. Options are `model` (category `model`),
the route's reasoning option (category `thought_level`), whose values
are those offered for the current model, and the route's tier option,
described below. Without `default_model` the first
advertised model is current. A model's current effort starts at its first
offered value. An unoffered value is refused (`-32602`) and changes
nothing. A model change keeps the current effort only when the new model
offers it; otherwise the effort is reset and no longer counts as applied.
An `unconfirmed` read-back answers with the configuration unchanged by the
request. A `legacy` session advertises a model list, acknowledges
`session/set_model` with `{}` and exposes no configuration option. A prompt
answers one text chunk and `end_turn`, or, with `session_dies`, is logged
and ends the process unanswered.

The route's tier option follows the same rules. It exists only while the
current model offers a tier, and its values are the route's native values
for the words that model lists, in the listed order. Its current value
starts at the first one. A value it does not list, a language word or a
boolean is refused (`-32602`) and changes nothing. A model change keeps the
current tier only when the new model offers it; otherwise the tier is reset
and no longer counts as applied, and the option disappears when the new
model offers none. An effort selection leaves the tier as it is. In the
order the contract fixes (model, effort, tier) nothing is selected after
the tier, so no fixture here shows a later selection undoing one.

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
| `requested_service_tier` · `offered_service_tier` · `transmitted_service_tier` · `configured_service_tier` | `access_selection.service_tier` · `requested` · `offered` · `transmitted` · `configured` |
| `turn_service_tier` · `effective_service_tier` | `access_selection.service_tier.turn.value` · `.effective.value` |

`access_selection.service_tier` is an optional record of that shape. It is
present exactly when the file declares a tier: a record for a file that
declares none, or no record for a file that declares one, is invalid
evidence. It is closed over eight facts. `requested` is the language word.
`option` names the route's option, `offered` lists the native values the
session offered (`null` when no offer was observed), and `transmitted`,
`configured` and `configured_source` follow the model's and the effort's
law. `turn` and `effective` are each `{value, evidence}`, with evidence
`unknown` exactly when the value is `null`. Without the record every tier
field reads `null`. A tier that moves during a turn is listed in
`changed_mid_turn` as `service_tier=<value>`.

The run's two records of one selection must also agree. The
`access_requirement` restates the file's `run.access` and `run.reasoning`
literally, a declared `service_tier` included. Its effort and its tier are
the selection's requested ones, its protocol is the one travelled, and its
`via` is the `access_id` that served.

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
there. An API reads back no configuration. A receipt asserting
`requested_effort: null` also asserts that no effort travelled: an omitted
declaration keeps the route's default and sends none.

The tier's transmitted and configured facts are judged the same way, as the
route's native values. Over ACP they are read from the route's own tier
option, by its id. A receipt asserting `requested_service_tier: null` also
asserts that no tier selection travelled: omission is not `standard`. No API
route of the table binds a tier, so a `service_tier` in an inference request
body never agrees with an asserted tier fact. The offered values are
asserted on the receipt only: what the scripted session lists is the
fixture's own premise read through the binding.

### Outcomes

- `FIXTURE-ERROR` · a malformed declaration or expectation, before any
  process starts: an unknown key, a mistyped value, missing `observed`
  counts, an effort or a service tier on a legacy session, a tier offer
  outside the language's two words, a receipt on a refused admission.
- `UNSUPPORTED` · a premise this adapter has no seam to stage. Injected
  `harness_attestations` (the reference engine admits no injected
  attestation). An `infer:` task on an agent-application route, whose
  subscription-harness attestation premise only that injection could
  state. An `env` overlay beside the route world, an unbound route, or an
  unadvertised `default_model`. Also, after the run: an admitted-run
  fixture that the engine refused before any event because the staged
  loopback endpoint has no known USD price for it. Its unknown-cost
  admission refuses that plain-HTTP route, and a reviewable route would
  still need a fresh interactive choice. The adapter never answers or
  bypasses that review; any request it observed keeps the divergence.
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
