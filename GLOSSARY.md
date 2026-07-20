# Glossary · one word, one meaning

> Normative vocabulary of the Nika standard. This file exists for the
> words that carry MORE than one sense across the estate: it pins the
> canonical referents and the discipline for using them. Definitions of
> ordinary constructs live in their spec chapters — this is the
> disambiguation surface, not a second spec.
>
> **The discipline** · qualify an ambiguous term at first mention
> (« MCP oracle » · « conformance oracle » · « human gate ») · bare
> afterwards within the same document. SPDX-License-Identifier: Apache-2.0

## oracle

A component you QUESTION and that answers with a VERDICT, never an
action — the established computer-science sense (test oracle · Turing's
oracle machine · random oracle). Two public referents in the Nika estate:

- **conformance oracle** — this repo's static evaluator
  (`conformance/runner.py` + the per-domain `*_core.py`): validates any
  workflow or fixture against the spec, engine-free.
- **MCP oracle** (also « the engine's static oracle ») — the reference
  engine's read-only MCP server (`nika mcp` · <!-- canon:mcp_tools -->9<!-- /canon --> tools): validates and
  teaches, never executes.

Never write a bare « the oracle » where both could be meant. (Engine
internals use further qualified senses — SSRF range oracle · test
oracle — those never appear unqualified in spec prose.)

## gate

Five senses live under this word; each keeps its qualifier:

- **gate algebra / GATE-v2** — the DAG admission rule: every incoming
  edge's producer must settle inside that edge's pass-set
  ([03 §gate algebra](./spec/03-dag.md#the-gate-algebra-v2-normative)).
- **human gate** — the human-in-the-loop pause: an `invoke:` of
  `nika:prompt` ([10-authority](./spec/10-authority.md) · never a verb,
  never an `approve:`).
- **check gate** (engine surface) — a stage of the static-check ladder
  (PARSE · TOOLS · PERMITS · SECRETS …) reported per finding.
- **CI / quality gates** — repository automation (non-normative ·
  everyday sense).
- **gateway** — chapter [12](./spec/12-gateway.md): the backend-neutral
  execution contracts. A gateway is not a gate.

## golden

- **the golden** (engine `nika test`) — the committed
  `<file>.golden.json` a mock-provider run's typed `outputs:` are
  compared against (pin → diff → CI).
- **golden fixtures** (this repo) — expected-output cases the
  conformance corpus and decision bundles ship
  ([11 §fixtures](./spec/11-decision.md)).

Other repos' « goldens » (visual-regression snapshots · parity tests)
are their own local senses — not this contract.

## binding · edge · the two doors

A **binding** is a `${{ … }}` expression resolved against a typed scope.
A `with:` binding that references `${{ tasks.X.* }}` IS a typed **data
edge** (« the binding IS the edge » — never restate a dependency). Tasks
connect through exactly **two doors**: `with:` (data) and `after:`
(control) ([03](./spec/03-dag.md)). « Wires » is presentation-layer
vocabulary for the same edges — fine on canvases, not in normative prose.

## predicate (after:) vs status

An `after:` entry names a **predicate** over the producer's settle —
exactly `success` · `failure` · `skipped` · `terminal` (the R5 closed
set). A task's **status** is the settled value — `success` · `failure` ·
`skipped` · `cancelled`. Same nouns by design (a predicate names the
class it admits); `terminal` exists only as a predicate, `cancelled`
only as a status.

## launch inputs (inputs · `--var`)

A workflow's declared inputs are its typed `inputs:`; the caller supplies values
at launch (`nika run <file> --var key=value` · repeatable). « Launch
inputs » is the collective noun. Distinct from `const:` (fixed values baked
into the file) · from `with:` (per-task bindings) and from `config:`
(non-sensitive runtime config supplied by the deployment).

## paused · human gate · nika:prompt

One mechanism, three layers, three words — never interchangeable:
**`nika:prompt`** is the TOOL (a blocking confirm under `invoke:`) ·
the **human gate** is the CONCEPT (a task that parks the run on a
human) · **`paused`** is the STATE (the durable pause: the trace
records `workflow_paused`, the engine exits `4`, the answer rides
`--resume <trace> --answer <task>=<value>`).

## upstream cone · downstream cone

The transitive ancestors (upstream) or descendants (downstream) of a
task in the precedence graph — `nika run --task <id>` runs one task
plus its upstream cone. These two are the canonical forms; « blast
cone » · « transitive cone » · « ancestor cone » are non-canonical
synonyms to avoid in new prose.

## claim string

« **Nika v1 Conformant — <Level> (spec <commit>)** » — the ONE public
conformance claim ([07 §Claiming](./spec/07-conformance.md#claiming-conformance)).
« v0.1-compliant » in normative sentences names the level *bar*, not
the claim.

## canonical filename

`<name>.nika.yaml` ([01 §File naming](./spec/01-envelope.md#file-naming-normative)).
`.nika.yml` is accepted-and-taught-against · bare `.nika` is reserved ·
the reserved media type is `application/vnd.nika+yaml`.

## envelope · pillar · stdlib · pack

The **envelope** is the header contract (`nika: v1` + `workflow:` ·
[01](./spec/01-envelope.md)). The **5 pillars** are the immutable core
(envelope · verbs · DAG · variables · errors). The **stdlib** (providers
· extract modes · builtins) versions independently. The **pack** is the
versioned examples+templates bundle every engine embeds
(`examples/manifest.yaml` · hash-pinned).
