# Runtime behavioral fixtures · RESERVED (post-announce)

This tier holds the **execution-half** fixtures — they require a running
engine and land with the reference engine's vertical slice
([07 §suite status](../../../spec/07-conformance.md#suite-status--v01-honest)).
Until then this directory carries the CONTRACT (shapes · no inputs the
static runner would pick up — `runner.py all` globs `input.yaml`, these
fixtures use `input.nika` + `run.json` precisely so the static gate
ignores them).

## Fixture shape (behavioral)

```
tests/runtime/<area>/<NNN-name>/
├── input.nika     the workflow · model: mock/echo (deterministic)
├── run.json            invocation · {"vars": {...}, "inputs": {...}, "env": {...}}
│                       (vars + inputs both thread through `--var` — the
│                        flag sets a workflow `inputs:` value · env
│                        overlays the engine's process environment)
└── expected-run.json   the assertion · see below
```

`expected-run.json` asserts on the RUN REPORT (not stdout) ·

```json
{
  "workflow_state": "success | failure | cancelled",
  "tasks": {
    "<id>": {
      "status": "success | failure | skipped | cancelled",
      "output": "<exact value>",          // optional · exact match
      "output_contains": "<substring>",   // optional · weaker assert
      "error_code": "NIKA-…",             // optional · when status=failure
      "attempts": 1                       // optional · the outcome payload's retry count (task_completed/failed carry it · task_skipped does not)
    }
  },
  "events_include": ["task.started:<id>", "task.skipped:<id>"]   // optional · order-free
}
```

Determinism rules · offline `mock` profiles — `mock/echo` output is
`mock(echo) · <prompt>` (the marker is PART of the contract: synthetic
output never masquerades as real content, and the spec's own examples
teach the same format — retuned 2026-07-30 from the aspirational
"prompt-verbatim" this parenthetical used to claim; the `nika:done`
`result:` path stays unprefixed, it carries an authored value) ·
schema → shaped defaults · no network (fetch fixtures use the engine's
HTTP mock · post-announce) · no wall-clock asserts (durations are
reported · never asserted).

The command runner validates assertion and invocation keys before execution.
A pre-admission refusal requires a nonzero exit, the exact structured error
code and each requested witness, with no workflow or task event. Compact
check reports and error documents are not runtime events. A contract needing
injected harness attestations is currently `UNSUPPORTED` by that runner,
before any engine call; this is a nonzero suite result, never agreement. An
injected route world (`access_routes`) and its receipt and observations run
through the access adapter
([contract](access-harness/README.md#the-command-adapter)). Malformed
contracts at the supported run and verify doors are
separately `FIXTURE-ERROR`; the separate doors named below are classified
before their full contract is validated.

The run command's evidence must be unambiguous: duplicate JSON members,
duplicate event-field keys, malformed NDJSON and repeated task or workflow
terminal events never agree. A task's terminal kind must match its outcome
class. An executed run needs one initial `workflow_started`, one terminal
workflow event and one final `run_settled`. Settlement statuses `succeeded`,
`failed` and `cancelled` correspond to workflow states `success`, `failure`
and `cancelled`, with command exits 0, 1 and 130 respectively. A success event
followed by a crash does not discharge an execution assertion. Pre-admission
refusals retain the separate nonzero-exit contract above.

`output` uses recursive JSON equality: booleans and numbers are distinct,
object member order is irrelevant, array order matters, and numerically
equal numbers such as `1` and `1.0` agree. Decimal JSON literals retain their
exact values during comparison; they are not rounded through binary floats.
`attempts` requires an integer count, never a boolean or decimal.
`output_contains` searches a string directly; other values are rendered as
compact JSON, with sorted object keys and lowercase JSON literals. Thus
boolean `true` contains `true`, not Python's `True`.

Each fixture has exactly one behavioral expectation and its required input:
`input.nika` for run, `trace.ndjson` for verify. Missing inputs, simultaneous
run/verify claims and misspelled expectation files fail before invoking the
engine. Discovery includes malformed neighboring fixtures rather than
silently dropping them. The separately specified resume, receipt-explanation
and energy doors are listed as `UNSUPPORTED` by this run/verify adapter once
their expectation is one well-formed JSON object; malformed bytes there are
`FIXTURE-ERROR`. That classification validates nothing more of their
contract and does not certify a well-formed fixture: they are not counted
as agreements or omitted from a complete sweep.

A verify verdict needs one positive JSON report consistent with its exit, never
prose: the command-level runner reads `nika trace verify <journal> --json
--color never` as one document framed by its exit (stdout for 0, 2 and 5;
`nika: ` and the document on stderr for 3), bound to the journal path and to
the process exit, and maps a closed table of typed families to the five
verdicts ([trace fixture contract](trace/README.md)). An empty, malformed,
doubled, contradictory or unbound reply never agrees; a torn chain, an
unknown family or another `verify_version` is `UNSUPPORTED`.

**Qualification boundaries.** The static `fetch.response` fixtures prove
policy admission only. They do not prove request counts, redirect handling,
response extraction, retry behavior or output durability. Those claims
require deterministic transport fixtures with independently observed
requests. Approval replay requires a multi-command fixture that preserves
the run and project while varying the operator store. The compose intrinsic
requires a tool-invocation adapter; running an example that completes with
`nika:done` does not invoke `nika:compose`. Until the relevant adapter
executes the contract, report it as unsupported and unqualified, never as
behavioral agreement.

The `nika:remove_file` contracts (`stdlib/behavioral/015`–`019` and
`permits/008`) assert task status, output and exact code only. The harness
takes no independent disk inventory, stages no companion entries and removes
its temporary directory before judging, so the returned path is not proof
that the file is gone; the read-after case (`018`) is an indirect witness
under its own read grant. Symlinks, FIFOs, no parent creation, unchanged
bytes on refusal, the no-I/O default backend, cancellation and confinement
are engine tests outside this corpus. Authoring a contract here does not
mean an engine has run it.

The [observation contracts](observation-contracts.md) now carry declarative
success/refusal cases for these doors, including secret export delivery and
masking. Discovery validates their closed fields and premises; it reports all
valid cases as `UNSUPPORTED` before any engine invocation. Their existence
closes the missing corpus declarations, not the missing Runtime observations.
The current run/verify adapter cannot discharge them. Invalid declarations
are `FIXTURE-ERROR`, and both categories keep the sweep nonzero.

Runtime type-error fixtures obtain the invalid value from an upstream task
through `with:`. A statically known invalid constant may be refused at check
and therefore cannot demonstrate an evaluation-time failure.

`mock/text` is the text-only probe for agent completion. It uses the same
echo and schema-shaped response rules, with the `mock(text) · ` marker for
unstructured text, but MUST emit no tool calls even when tools are offered
or requested. It lets a fixture exercise a model that keeps answering in
prose: a granted completion sentinel must lead to a budget failure instead
of a false success. `mock/echo` keeps its existing tool-call behavior.

## The areas (one per execution contract)

| Area | First fixtures (the contracts rounds 1-7 locked) |
|---|---|
| `gates/` | default gate cancels on upstream failure · explicit `when:` evaluates over terminal deps · `when: true` runs in a failing workflow (the always-pattern) |
| `for-each/` | per-iteration timeout · null placeholder at a failed index (zip alignment) · empty collection → skipped |
| `errors/` | retry honors transient-only (the non-transient half is `004-retry-never-on-non-transient` — attempts stays 1 under a declared retry · the TRANSIENT half needs a deterministic transient error and parks behind the HTTP mock, post-announce) + on_codes · on_error.skip preserves the error · recover substitutes BEFORE bindings · DAG-004-class await never deadlocks — **parked**: the engine's check refuses the await shape itself (the corpus's one divergent-by-design row, `errors/recover-task-ref-no-edge` · nika#291), so the runtime contract is unstageable by command until that lands |
| `agent/` | budget exhaustion = NIKA-AGENT-001/002 with partial in error.details · tool errors feed back EXCEPT security_error (the feed-back half is `003-tool-error-feeds-back` — the final AGENT-001 IS the proof the loop survived the tool error · the security half — a refusal that must END the loop — stays unstageable with mock/echo, which cannot be steered to synthesize an out-of-boundary argument deterministically) · nika:done result: becomes .output |
| `permits/` | NIKA-SEC-004 at the first out-of-boundary effect · permits:{} = pure compute |
| `secrets/` | under a jq and an `outputs` egress rule the sanctioned workflow completes and its derive task is observed as the JSON boolean `true` (001 · the workflow's exported value is not asserted: output export and secret masking need their own observed door) · an `outputs:` entry reading the secret itself stays a check refusal (`envelope/secrets-direct-output-egress-refused.nika`) · the absence of the secret's bytes from every export surface needs an adapter that scans exports and trace artifacts, and stays unqualified until then |
| `variables/` | jq clock forms bind to the immutable `WorkflowStarted` instant, never an ambient host clock |
| `admission/` | a `required: true` input with no `default:` and no caller value refuses with `NIKA-1708` before any task event (001 · the launch plane of [05 §Error code namespaces](../../../spec/05-errors.md) — the refusal is an admission verdict, so no task exists to retry or catch it) · a supplied value (002) and a declared default beside an absent optional input (003) succeed · Check stays source-only (core/variables/016) |
| `access-harness/` | an unattested agent seat refuses `infer:` with the failed infer-grade conjuncts; an attested one-shot seat admits the same task · `run.json.harness_attestations` is injected conformance evidence, never host discovery · a file-declared `run.access` / `run.reasoning` selection is honored exactly or refused before inference (003–017 · `run.json.access_routes` injects the route world, `expected-run.json.observed` carries the adapter's own counts · [contract](access-harness/README.md)) |

### Infer-grade harness fixture extension

An `access-harness` fixture adds these invocation fields:

```json
{
  "access": "codex",
  "harness_attestations": {
    "codex": {
      "single_turn": true,
      "no_implicit_tools": true,
      "structured_output": "json_schema",
      "model_identity": "requested"
    }
  }
}
```

The runner injects this declaration instead of discovering a host binary or
reading an account store. `expected-run.json.admission` asserts the
pre-inference meet: `accepted`, and on refusal the exact error code plus a
`witness_contains` list. This keeps the fixture hermetic while the adapter's
own repository proves its process wire with a scripted fake binary.
