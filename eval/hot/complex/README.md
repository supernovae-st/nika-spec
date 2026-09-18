# eval/hot/complex — composed authoring goldens

Twelve scenario families built from the admitted language, each with a
reference workflow, the near-misses that read well and are wrong, and the
mechanical judgment that tells them apart.

**This is composed product acceptance, not conformance.** A conformance
fixture proves one admitted law ([`conformance/tests/`](../../../conformance/tests),
one behaviour per fixture). A scenario here composes several laws and asks
whether a *candidate* — written by a person, a compiler or a model — means
what was asked. Nothing in this directory adds syntax, grants authority,
promotes a HOT family, sets a threshold or supports a comparative claim.
`hot_promotion` is `false` and the gate refuses any other value.

Owners: nika#1663 (compile semantics · the semantic oracle) · nika#1666
(patterns) · nika#1656 (measure) · nika#1664 (program identity, so that a stale
approval cannot authorise) · nika#1643 (the runtime answer door).

## Why a judge is needed at all

Every near-miss below is **valid and `--native-strict` clean** on the reference
engine unless its row says otherwise. A check-only pass proves static validity
and nothing else.

| Family | The request, in short | A near-miss that passes check | What rejects it |
|---|---|---|---|
| X01 | fan out · merge · ask · publish | the write reads a *gated task's output* and has no condition of its own | `effects_gated` · behaviour: the file is written after a refusal |
| X02 | one bad record must not sink or vanish | drop the nulls and total the rest · or type `complete: true` | `outputs_contract` · behaviour: the total is short and says nothing |
| X03 | several sources · exact provenance · contradiction | look the anchor up in the whole corpus · or let the first source win | behaviour: a misattributed citation passes · a conflict disappears |
| X04 | two repair rounds, then a rule decides | the verdict reads the score and ignores it | behaviour: a score of 35 is accepted |
| X05 | missing · empty · null · defaulted | trust `required: true` to mean non-empty | behaviour: `--var account=` writes a receipt for nobody |
| X06 | “Use Teams instead of Slack” | the swap, plus the refund limit 100 → 250 | `edit_locality` |
| X07 | summarise and post to the team channel | `nika:*` and `*` · or quietly save to a file instead | `authority_bounded` · `required_effects_present` |
| X08 | classify a hostile ticket and save a reply | the model also returns *where* to save it | `control_positions_trusted` · behaviour: the file lands where the ticket said |
| X09 | cheapest quote under two hard limits | compute the violations, report them, select the cheapest anyway | behaviour: the late quote is selected |
| X10 | exactly one queue per ticket | a fallback written as “anything that is not a login” | `branches_exclusive_total` · behaviour: two queues receive one ticket |
| X11 | ask before the refund | “Proceed with the refund?” | `gate_binds_effect_facts` · behaviour: an answer for 40 EUR pays 400 EUR |
| X12 | reuse a recorded judgment only if nothing moved | leave the threshold out of the identity · compare candidates as a set · let 0.97 stand in for a changed amount | behaviour: stale evidence is reused |

## Two layers, two kinds of proof

```sh
python3 eval/hot/complex/judge.py                  # static · CI · no engine, no model, no network
python3 -O eval/hot/complex/judge_selftest.py      # the judge can fail · CI
python3 eval/hot/complex/behaviour.py --engine /path/to/nika [--receipt receipt.json]
NIKA_BIN=/path/to/nika python3 -O eval/hot/complex/behaviour_selftest.py   # the rehearsal can fail
python3 eval/hot/complex/judge.py --scenario X01 --candidate my.nika  # exit 0 accepted · 1 rejected · 2 static-invalid
```

**`judge.py` reads declared properties from the derived graph.** Each
assertion is one property, never a comparison with the reference's bytes or
with a model's output. Together they are a *subset* of what a request means:
the defects this corpus names. A candidate that passes is free of those
defects, not proven correct, and this is not a semantic-equivalence oracle. The
`variant-*` files show that two differently built correct candidates pass; they
show tolerance for the rebuilds that were tried, not for every rebuild.

Each candidate must be red for *exactly* the assertions its row declares and
green for every other one; a scenario whose assertion no near-miss turns red is
refused, because nothing would show that the assertion can fail.

| Assertion | The question it answers |
|---|---|
| `effects_gated` | Can the effect run after a refusal? Closure is the task's own `when:` on the answer, or an `after: success` edge from a task that has one. A `with:` edge closes nothing: a skipped producer hands null and the consumer runs. |
| `gate_blocking` | Does the gate answer itself when nobody is there? |
| `gate_binds_effect_facts` | Does the question show every fact the effect consumes? An answer is bound to the content that was shown. |
| `authority_bounded` · `required_effects_present` | Is the boundary exactly what the request needs, and is the requested effect still there? |
| `control_positions_trusted` | Can untrusted content choose a tool, a path, a host or a program? |
| `bounded` · `decision_deterministic` | What stops the loop, and who applies the rule — a model or a rule? |
| `inputs_contract` · `outputs_contract` | What may nobody guess, and is the loss visible in the result? |
| `recover_narrow` · `fanout_isolated` | Which failures may read as absence, and can one item sink the batch? |
| `branches_exclusive_total` | For every class in the closed set, how many branches open? |
| `edit_locality` | Did the edit change what was asked, all of it, and nothing else? Judged on typed parsed nodes (`byte_equality` is `false`): an empty mapping or sequence that appears or disappears is a change, and so is `true` → `1` or `1` → `1.0`, which Python would call equal. Comments, key order and quoting are not nodes. A node's place is a tuple of typed components, never a joined string, so `{"a": {"b": 1}, "a.b": 2}` has two places and a change to either is seen. |

Paths in `allowed`, `required` and in a violation are one injective spelling of
that tuple. A plain key and an index read as they always did
(`tasks.notify.retry` · `permits.net.http[0]`); any other string key is a JSON
string in brackets (`["a.b"]` · `a[""]` · `v["0"]`); a key that is not a string
says its type (`v[<int> 0]` · `[<bool> true]` · `[<null>]`). The patterns are
`fnmatch` globs, so a literal `[` is written `[[]`. A place that arrives twice,
or two places that would share a spelling, is refused: last-wins is how a change
gets lost. Documents are compared after YAML parsing, so keys a Python mapping
cannot hold apart (`1`, `1.0`, `true`) are already merged by the parser.

The `when:` reader is the decidable fragment only (boolean literals, `==`,
`!=`, `!`, `&&`, `||`, parentheses), evaluated three-valued. An expression
outside it is *unknown*, and unknown never counts as closed.

**`behaviour.py` rehearses a finite set of cases on an engine you name.** Exact inputs go in; outputs
*and effects* are judged — which tasks started, which files exist afterwards,
the exit code, the refusal code. A right final answer with a stray write in an
unchosen branch fails. Model tasks are replaced by stated outputs, including
hostile ones (a model that obeys the ticket; an extraction that misattributes a
citation), so what is proven is the deterministic membrane each workflow draws
around its model calls, on that one build. Every run is `mock/echo`, in a fresh
directory, with an empty environment; a candidate that needs a network, a
secret or a program is never executed — its engine check is recorded and it is
listed as static-only with the reason. The receipt carries the engine version
and the binary's sha256.

It does **not** prove model quality, another engine, a live connector, latency,
cost, behaviour outside the listed cases, or anything under `product_contracts`.

## Judging somebody else's candidate

```sh
python3 eval/hot/complex/judge.py --scenario X01 --candidate my.nika
```

| Exit | Meaning | Report |
|---|---|---|
| 0 | accepted: statically valid, and no assertion of the scenario is violated | `accepted: true` · `violations: {}` |
| 1 | rejected on meaning: statically valid, and an assertion is violated | `accepted: false` · `violations` |
| 2 | **refused as static-invalid, and not judged** | `accepted: false` · `refused: "static-invalid"` · `static_errors` · no `violations` |

A verdict always comes with a JSON report on stdout. A usage error also exits 2
(that is `argparse`), and prints no report.

A candidate is admitted before it is judged. The repository's reference static
oracle — the function behind `conformance/runner.py validate`, with its schema
and its unique-key loader, nothing re-implemented here — must accept the
source first. `yaml.safe_load` keeps the last of two duplicate keys and says
nothing, so a parsed document alone is not evidence of what a file says: a
second `permits:` block can hide `nika:*` behind the legitimate one, a second
`when:` can hide an open condition, and parsed last-wins both satisfy every
assertion. They are refused (`NIKA-PARSE-017`), as are a malformed schema, an
unknown key and text that is not YAML. A refused source carries no
`violations`: it was not judged, and a verdict on a lossy parse would prove
nothing.

The file is read **once**, and that one text goes to the oracle and to the
parser, so the two cannot disagree about what was judged. The oracle resolves
skill paths and child workflows against the candidate's own directory. The
corpus's own candidates pass through the same door, so the command and the
gate cannot drift apart.

## What a green run says about Compile: nothing

Every reference, variant and near-miss is **hand-authored**, and each row says
so (`provenance`); the judge reports `compiler-generated: 0` and
`model-generated: 0`. Accepting a hand-authored reference measures the judge
and the fixtures. It is not a generated Compile case and must not be counted as
one. When a compiler or a model proposes candidates for these scenarios they
are judged with the same command and recorded under their own provenance,
beside these and never in their place. The only cases that exercise the
Compile door today are the four `compile_door` cases of X06, in its
conservative exact and edit modes.

## What is declared and refused

[`scenarios.json`](scenarios.json) owns the corpus. Each scenario declares its
`status`, its `owner` and `laws`, the exact `intent` and `facts`, the
`expected_outcome`, what `must_not_guess`, the Socratic questions its
assertions answer, its candidates with the verdict each oracle must give, its
behaviour cases, and the command that validates it.

- **`product_contracts`** — eight acceptance cases (a conversation that
  survives a restart · an approval bound to its effect whatever the question
  says · a late answer to a superseded revision · a resume after an effect of
  unknown outcome · a preference that does not cross a workspace · local and
  remote parity · a question on an incomplete outcome · comments that survive
  an edit). Each is `UNQUALIFIED_PRODUCT_CONTRACT`: given · when · then · must
  never · why unqualified. The gate refuses a contract that carries a
  candidate, an assertion or any other status. A workflow file cannot prove
  these, so none pretends to.
- **`retained_gaps`** — three places where the rehearsal found the expected
  behaviour missing. They stay red on purpose (`baseline: expected_fail`). When
  an engine starts to show the expected behaviour the rehearsal **fails** until
  the gap is retired in the same change, so a fix cannot hide behind a stale
  baseline.

  | Gap | Expected | Observed on the rehearsed build |
  |---|---|---|
  | KG01 | a route closed only by a skippable data edge is refused (`NIKA-SEC-014`) | both oracles accept it; a refusal still writes |
  | KG02 | an answer does not authorise a changed effect, whatever the question said | a generic question lets the old answer pay the new amount |
  | KG03 | a one-constant edit keeps the licence header | the candidate is re-serialised and every comment is gone |

## Adding a scenario

Start from the questions, not from the YAML: which fact is missing · what must
never be guessed · which smallest counterexample defeats the judge · can a
plausible incorrect workflow pass · what evidence is required before an
irreversible effect · what change invalidates a prior approval · which
invariants survive an edit, a retry or a restart · what happens if every
candidate is wrong. Turn each answer into an assertion or a behaviour case,
then write the workflow that *fails* it and watch it fail. Expected outputs are
reasoned from the fixtures by hand; they are never regenerated from a model's
or an engine's output, and a disagreement is investigated, not overwritten.
