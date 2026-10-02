# Adapter-dependent observation contracts

These are declarative behavioral contracts for laws that the run/verify
adapter cannot observe. They are specified cases, not measured Runtime
agreements. The current command runner validates each complete contract and
reports `UNSUPPORTED` before invoking an engine. Invalid contracts are
`FIXTURE-ERROR`; both results keep the suite nonzero. Neither result can be
counted as `AGREE`, an implementation qualification or a release proof.

## Layout and admission

A directory contains exactly one of these expectation documents and its input:

| Expectation | Input | Required adapter capability |
|---|---|---|
| `expected-approval.json` | `input.nika` | `approval-session-v1` |
| `expected-http.json` | `input.nika` | `http-transport-v1` |
| `expected-compose.json` | `draft.nika` | `compose-intrinsic-v1` |
| `expected-export.json` | `input.nika` | `secret-export-v1` |

Each document has exactly `contract_version` (integer `1`), `law` (the owning
public anchor), `input` (the filename above), `given` and `observations`
(objects). Optional `note` is nonempty explanatory text, never an assertion.
`law` is the corresponding anchor below; a different or absent owner is an
invalid contract. The contract has no shell commands, host paths, real
credentials, engine version, provider credentials or source-equality oracle.

All described object fields are required and closed unless explicitly stated
otherwise. JSON members are unique, bytes are UTF-8, booleans are not integers,
and the contract's numbers are integers bounded to `0..1000000`. Floating or
nonfinite numbers are invalid in this version. The caller selects a fixture
directory; that directory itself must not be a symlink. Its deployment ancestors are canonicalized once to establish the
admitted root (for example, a system temporary-directory alias). Below this
root, paths are canonical relative POSIX paths with no symlink component.
Both the expectation and input must be regular readable nonempty UTF-8 files
inside that root; the expectation is checked before JSON is read. This is a
fixture-content boundary, not a policy for the caller's deployment ancestors.
A concurrent `run.json` or another expectation is invalid. An orphan `draft.nika` is discovered and refused, not omitted.
Admission checks the observation contract and its file premises; it does not
replace the owning Nika parser or claim that the input passed Core checking.

## Command seam and evidence

An implementation may provide a **separate command adapter** for a named
capability. Its invocation must identify the fixture directory and the pinned
engine executable. It must use the implementation's command surface, not link
the engine into the oracle. No new Nika syntax or product command is introduced
by this contract. This runner deliberately does not discover, select or invoke
such an adapter yet. A future command binding, observation decoder and judge
must be admitted together and tested with adversarial observations before they
can produce agreement. A command that only echoes expected observations cannot
qualify an implementation.

An adapter stages private temporary stores and a synthetic workspace, records
the command/input identities, ordered calls and all requested observation
surfaces, and binds its report to those artifacts. It judges the observations
below, never workflow bytes or an implementation's self-declared `pass`.
Unknown capability, missing required evidence, missing capture or ambiguous
identity is unqualified; absent evidence is never zero effects. The current
runner's pure validation is not an implementation of these observers.

No adapter may use ambient HOME, approval stores, external network, wall clock
or paid models for these cases. The injected clock, synthetic approval answers,
mock transport responses and scripted agent tool-call arguments are fixtures.
If a command surface cannot inject or capture a required fixture premise, that
capability stays unsupported. Host-port changes or disabling the SSRF boundary
to make a request work are not allowed substitutes for the mock transport.

## Approval session

Owner: `spec/10-authority.md#the-two-judges-that-remain`.

`given` has `decision` (`consumed`, `unproven`, `fresh`), `operator_store`
(`same`, `other`), `project` (`same`, `relocated`), `lineage` (`verified`,
`waived`, `historical-unbound`), `answer` (`none`, `affirmative`, `denied`),
integer `now_ms`/`expires_ms` with `now_ms < expires_ms`, and `effect_path`
(`out/approved.txt`). All stores and locations name adapter-created fixture
identities; they never resolve to the operator's actual directories.

For `consumed`, first acquire and consume the ticket through the approval door
in the seed run, retaining the issued ticket, decision attestation and observed
first effect. The tested leg attempts reuse of that same run × step × content
hash and decision. `other` substitutes a fresh operator store while retaining
the project; `relocated` moves the fixture project while retaining the run
identity. `waived` attempts that leg with the implementation's explicit chain
waiver. `historical-unbound` supplies a fixture history for which the adapter
cannot establish binding/consumption; it cannot silently manufacture missing
proof. `unproven` must be refused even with time left on its ticket.

`observations` has `reuse` (`refused`, `not-requested`), boolean
`fresh_ticket_required`, and integer `new_decisions`/`gated_effects`. Counts
refer only to the tested leg, excluding the recorded seed consumption. A
consumed or unproven decision, with `answer: none`, must refuse reuse, require
a fresh ticket, record zero new decisions and issue zero gated effects.
Count effects at the dispatch boundary as well as inspecting the target;
writing the same bytes twice is still two effects. An unchanged final file
alone cannot prove refusal.

The fresh controls create a new bound ticket and inject one explicit answer.
They use verified lineage, record one new decision and never request reuse.
An affirmative answer permits exactly one gated effect; denial permits zero.
The pair distinguishes single-use protection from an engine that blocks every
approval. It does not weaken existing content binding, TTL, cross-run refusal
or affirmative-consent laws, whose other cases retain their own coverage gaps.

## HTTP transport

Owner: `stdlib/builtins-v0.1.md#nikafetch`.

`given` has `method` (`GET`, `HEAD`, `POST`), `via` (`workflow`, `agent`),
`response` (null for absent policy, or the policy value), `mode` (`raw`,
`jq`), `retry` (maximum additional attempts, integer `0..2`), boolean
`keyed`, `fault`, `responses` and boolean `sibling`. An `invalid-policy` fault
means `response` is present even when null. Other policies have exactly
`accept`, a distinct integer set of size `1..16` in `200..599`. The null absent
policy is the existing default behavior. The workflow obtains policy values
through an upstream task, so revalidation is a resolved-value question.

`via: agent` supplies the same resolved call arguments to one scripted agent
tool invocation under a granted whitelist; no model chooses arguments or
produces a scoring verdict. The adapter must actually observe that tool-call
boundary. Running the direct invoke task alone does not discharge that case.

`fault` is exactly `none`, `invalid-policy`, `transport`, `permission`, `ssrf`,
`tls`, `redirect-limit`, `body-limit` or `extraction`. The mock injects the
named condition at its owning boundary without granting new authority. A
permission fixture withdraws the relevant grant at the admission boundary;
an SSRF fixture injects a disallowed resolved destination before dispatch.
The supplied source is otherwise unchanged. The capture must prove that the
named refusal, rather than a parse error or unrelated failure, was exercised.

`responses` is a sequence of at most three objects, each with integer `status`,
`final_url` (mock HTTPS URL or null), string `body`, and string-map `headers`.
Only redirect responses may precede the final response. Reserved hosts
`example.test` and `final.example.test` name injected mock routes; no host is
contacted. Userinfo, query and fragment are fixture data to be stripped from
observed route identity. Null identity is not replaced by the requested URL.
For a redirect fixture the adapter connects each listed intermediate response
to the following route; it captures each hop. Header metadata never becomes
an output field. These bounded cases use raw bodies for successful extraction;
`jq` with the input's fixed `jq: "."` exercises a received, accepted response
whose non-JSON body fails extraction. The extraction mode is the canonical
`jq` mode, not a separate `json` mode.

`observations` has `outcome` (`success`, `failure`, `refused`), integer
`requests`, integer-or-null `attempts`, `output`, `error` and `sibling`
(`retained`, `quarantined`, `not-requested`). `requests` is the independent transport journal's count;
`attempts` counts outer invocation attempts. Redirect hops increase requests,
not attempts. Task attempts alone cannot discharge the request assertion.
A pre-transport refusal observes zero requests and uses `attempts: null`,
which makes no invocation-attempt assertion. In particular, an invalid resolved
policy may already have entered the builtin before HTTP dispatch is refused;
the language's zero-request rule does not assert that no invocation began.
All other cases here observe one invocation attempt. This is a bounded mock
observation, not a claim about arbitrary physical network transmissions.

An accepted response must settle success, with no error, without retry even
when one was declared. The opt-in output has exactly `status_code`, sanitized
final `url` and extracted `body`; no `response` keeps the existing body shape.
Every listed status is compared only with the final response. An unlisted
2xx still fails. A successful sibling, staged before the probe, remains
available after success and is quarantined after an unhandled failure; the
adapter observes the published artifact, not just a task's previous value.

On failure, `output` is null and `error` has exactly `code`, `status_code`,
`accepted` and `transient`. A non-null `code` pins that diagnostic; null means
that this case asserts the failure class/boundary without pinning a code.
An unlisted status or extraction failure pins `NIKA-BUILTIN-FETCH-001`.
Null `status_code` or `accepted` asserts absence of that metadata, not invented
status zero. A received response carries its status and, when opted in, the
accepted set. Non-null `transient` is an exact boolean assertion; null makes
no transient classification claim. A non-null assertion for an unaccepted
received 4xx/5xx status must agree with the normative table: 5xx/408/429 are
transient, other 4xx are not, subject to the keyless-effect carve-out. This
status table does not invent a classification for extraction, TLS or limit
faults. A keyless POST transport failure explicitly asserts false and has no
declared retry. Transport/security/limit/extraction
failures cannot be converted into success by `response`.

## Compose intrinsic

Owner: `stdlib/builtins-v0.1.md#nikacompose--self-check-a-drafted-workflow-agent-loops-only`.

`given` has `case` (`pure`, `core-invalid`, `missing-child`, `effectful`,
`secret-flow`, `capability-escape`) and `child` (null, or `absent-child.nika`
for the missing-child case). The named absent child must not exist in the
fixture. Invoke `nika:compose` exactly once inside a scripted granted agent
turn with `workflow_yaml` equal to this draft. Do not execute the draft.
Observe the actual tool result, a child-file read monitor and the draft-effect
dispatch monitor. The monitors exclude the adapter's own staging and normal
recording of the tool invocation; they concern interpretation/execution of the
draft. Every attempted draft effect counts, even if a sandbox rejects it.

`observations` has boolean `valid`, integer `child_reads`/`draft_effects`,
`secret_findings`/`capability_escapes` (`zero`, `positive`), boolean
`certificate` and `saved_check` (`not-requested`, `NIKA-COMP-001`). Counts of
findings may differ across implementations; zero versus positive is the
behavioral distinction. The certificate assertion requires the reported
bounded summary, not a particular serialization or text.

All cases observe zero child reads and zero draft effects. Core-invalid must
report `valid: false`; pure, effectful and the two non-Core finding cases
report true while preserving their separate findings. Missing-child has a
valid in-memory report; a separate file-aware check of the saved draft refuses
with `NIKA-COMP-001`. These two observations are the one boundary distinction.
A `nika:done` example, an oracle call without a reader, or a draft that never
names an effect cannot substitute for the intrinsic's effectful witness.

## Secret export

Owner: `spec/01-envelope.md#egress--optional--sanctioned-destinations-declassification`.

`given` has `case` (`derived`, `identity`, `direct`), `secret`
(`synthetic-conformance-secret-7f29`) and `public_sentinel` (`public-control`).
Supply the secret only as `SYNTHETIC_FIXTURE_SECRET` inside the fixture
invocation; no key discovery or actual credential is permitted.

`observations` has `allowed_outcomes`, `derived_value`, integer
`secret_occurrences`, `surfaces`, `public_sentinel` and `refusal_code`.
The derived case must deliver the workflow export object with `exported`
equal to JSON boolean true and `public` equal to the sentinel. Observing the
`derive` task alone is insufficient. For identity the allowed outcomes are
`redacted` or `refused`: a delivered export must mask the secret and retain
its public sentinel; an explicit security refusal is acceptable. The direct
`${{ secrets.key }}` export must be refused with `NIKA-SEC-007` at check.
A refusal is not a silent empty success, a crash or a missing export.
`derived_value: null` makes no derived-value assertion in the identity/direct
cases. `refusal_code: null` does not pin the identity refusal's exact code.

`surfaces` is exactly `stdout`, `stderr`, `journal`, `trace-outputs` in that
order; zero `secret_occurrences` is required on all produced surfaces. Capture
stdout/stderr in all cases and the complete journal and public trace-output
projection for any booted run. A pre-boot check refusal must prove the absence
of boot/events and records journal/projection as not applicable; it must never
claim those surfaces were scanned. A booted run with either artifact missing
has incomplete evidence. Scan raw bytes and decoded JSON string values so
escaping does not hide a secret. The positive derived control must retain the
public sentinel; deleting all output is not masking. A task boolean or an
exit code alone discharges neither export delivery nor masking.

The contracts observe the named surfaces for these fixtures. They do not
claim to enumerate every UI, transport or future engine export surface.
Unexercised surfaces remain unqualified under the existing masking law.
