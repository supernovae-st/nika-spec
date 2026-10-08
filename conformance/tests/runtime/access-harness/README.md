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
| `acp_config_before_first_prompt` | the model and effort the peer had received and accepted through its own selection methods when its first prompt arrived · an absent `effort` means none was applied |
| `acp_prompts` | prompt requests received by the scripted ACP peer (session setup and configuration are discovery, never counted) |
| `api_inference_requests` | inference requests received by the mock API endpoints |
| `cli_invocations` | direct CLI processes started |

Counts are exact integers. A refusal before inference asserts zeros.

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

## Status

No command adapter executes this extension yet: every fixture here is
`UNSUPPORTED`, which is never agreement. The scripted ACP peer, mock API
endpoint and CLI spawn counter belong to a separate adapter that must be
qualified with adversarial observations before any result counts.
