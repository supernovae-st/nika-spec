# FINDINGS — reference-engine observations vs spec (conformance v0.1 polish, 2026-07-08, nika 0.97.0)

Non-blocking observations recorded while proving the corpus green. Neither is
asserted BY the corpus (headers were chosen so both engine behaviors conform);
both deserve an upstream look. The one asserted divergence stays
`errors/recover-task-ref-no-edge.nika.yaml` (spec 05 §recover await ·
supernovae-st/nika#291 · verdict DIVERGENT by design).

## F-1 · Unknown tool: check refuses without the spec wire code

`verbs/invoke-unknown-tool-reject.nika.yaml` — spec 05 §errors: `NIKA-INVOKE-001 |
unknown tool (unresolvable nika:/mcp: id) | validation_error`. `nika check` (0.97.0)
refuses correctly but reports only the TOOLS gate verdict
(`✖ TOOLS \`nika:nonexistent_builtin_xyzzy\` … is not a canonical builtin`) — the
INVOKE-001 wire code never appears on the check surface. Same convention across the
permits/secrets gates (spec-05 SEC-004-class refusals print `✖ PERMITS/SECRETS`
verdicts, no code). The corpus encodes this as the `check-reject (gate verdict)`
header class; an engine that additionally prints the wire code is equally
conformant. Upstream question: should check-time gate refusals surface the
canonical wire code (one-voice)?

> **Re-measured 2026-07-30 · nika 0.106.1 — EVOLVED, and the question
> sharpened.** The surface now emits a CODE (`NIKA-BUILTIN-001` in
> `check --json`, probed on the same unknown-`nika:*` shape) — the
> codeless half of this finding is closed. What remains is a family
> question: BUILTIN-001's registered condition is the *statically-checkable
> arg contract*, while 05 assigns *unknown tool* to `NIKA-INVOKE-001` —
> the engine speaks a neighbouring code. Same one-voice genre as the
> codeless-rungs owe (supernovae-st/nika#761); parked with it rather than
> filed separately.

## F-2 · Out-of-range index / missing map key → VAR-001 "unresolved reference" (whole expression as ref name)

Probed (lab `cel/c12-index-out-of-range`, `cel/c14-missing-map-key` — NOT in corpus):
`when: ${{ vars.xs[10] == 1 }}` on a 3-element list fails at RUN with
`NIKA-VAR-001 · unresolved template reference "vars.xs[10] == 1"` — likewise for a
missing map key. Two observations: (a) CEL standard semantics ("no such index" /
"no such key" eval error) read as a NIKA-VAR-006-class evaluation error, and the
spec does not enumerate the case — spec-clarification candidate; (b) the error
message reports the ENTIRE expression as the unresolved reference name —
message-quality issue. Because the normative code is ambiguous, c12 was swapped out
of the corpus for `cel/c15-string-method-type-mismatch` (spec 03 side-constraint 1
is explicit, engine fires exactly `NIKA-VAR-006`); index-out-of-range sits in the
v0.2 backlog pending the spec call.

> **Re-measured 2026-07-30 · nika 0.106.1 — STANDS unchanged.** The same
> probe (a `when:` indexing past a 3-element list) still fails at run as
> `NIKA-VAR-001 · unresolved template reference` with the whole
> expression as the reference name. Both halves of the finding hold; the
> v0.2 spec call stays owed.

## F-3 · Every binary-differential is dark: the corpus is ahead of the shipped engine

**Measured 2026-08-13 · `nika 0.108.0` (the shipped binary).** Both
differentials that run the real binary against this repo's corpus agree on
*nothing*, and it is one cause, not two ·

```
python3 reference/differential.py --seeds 120     →   0/120 agree
python3 scripts/oracle-differential.py --bin nika →   0/50 agree · 50 unexplained
```

Every divergence is the same line ·
`NIKA-PARSE-003 · invalid `nika:` version "<id>" — the value is exactly `v1``.
The shipped engine still requires the OLD envelope (`nika: v1`); the corpus,
the templates and `reference/generate.py` already carry the NEW identity form
(`nika: <workflow-id>`). The workflow is refused at parse, so every task reads
`engine=None` and the comparison has no subject.

**This is a cascade state, not a defect on either side.** The teaching surface
was migrated first, by design; the engine arm lands with the envelope window.
Both harnesses go green again on their own when it ships — no fixture and no
model needs a change here.

**What it costs while it lasts, and why it is written down.** Two proof
surfaces read GREEN in prose and BLACK in fact: `reference/README.md` published
`120/120 agree` beside the command until 2026-08-13. A differential that
compares nothing reports no divergence, so *the failure mode is silence* — it
cannot be distinguished from success by anyone who does not run it. Until the
engine arm lands, the proofs that hold are the ones with no binary in the
loop · `reference/selftest.py` (28 laws · 300 seeds) · `scripts/gen-gate-matrix.py
--check` · `scripts/lints-differential.py --selftest` (5/5) ·
`scripts/mutation-adequacy.py --check` (15/15 selftests die under a permissive
judge). All green at this commit.

## F-4 · The 1 MiB decode grain has three independent definitions, not one

**Measured 2026-08-13 · reference engine `origin/main`.** The
untrusted-decode bounds of [15 §the verifier is a fortress](../spec/15-proof.md)
are stated as spec constants precisely so a second implementation
inherits them. The reference engine's own tree carries the 1 MiB grain
in **three** places that no gate ties together ·

```
crates/nika-dap/src/bounded.rs:27        MAX_ARTIFACT_BYTES = 1024 * 1024
crates/nika-registry-client/src/lib.rs:70  MAX_ARTIFACT_BYTES = 1024 * 1024   (own const)
crates/nika-harness/src/client.rs:39     MAX_LINE_BYTES    = 1024 * 1024   (own const)
```

`nika-dap`'s journal walk is the one that composes correctly —
`chain.rs:110` aliases `MAX_LINE_BYTES` **to** `bounded::MAX_ARTIFACT_BYTES`
rather than restating the literal, so those two can never drift apart.
The registry client and the harness restate it. Three literals agreeing
today is not one source; it is three sources that happen to agree, and
the failure mode is silent — a bound raised in one place leaves the
other two quietly stricter, and nothing goes red.

**Also measured, and worth writing down because the prose invites the
opposite reading:** on the JOURNAL surface only the line bound and the
whole-file bound are enforced. A journal line carrying a 300-byte
identifier, or forty levels of nesting, walks clean — those two bounds
guard the ARTIFACT decoder (`decode_untrusted_json`), never the walk.
Spec 15's table now names the surface per bound for that reason.

Not blocking, and not asserted by any fixture: a conformance corpus
cannot see a second implementation's internal constants. This is an
upstream note — one const, re-exported, or a gate that proves the three
agree.

## F-5 · `never-run` is an energy-arm class: COST still prices a task that cannot execute

**Measured 2026-08-13 · `nika 0.108.0`.** A task whose `for_each`
iterates a literal EMPTY list provably never executes. The two spend
rungs of `nika check` describe it differently ·

```
 ✔ COST    $0.0006 – $0.0006 worst-case output ceiling …
   jamais  groq/qwen/qwen3-32b  ≤1000 tk  $0.0000      ← a row, priced zero
   vrai    groq/qwen/qwen3-32b  ≤1000 tk  $0.0006
 ✔ ENERGY  ≤ 0.087 Wh worst-case OUTPUT ceiling · gpu scope · 1 of 2 tasks measured · 1 never-run …
   vrai    groq/qwen/qwen3-32b  ≤1000 tk  ≤ 0.087 Wh   ← no row for `jamais`
```

The energy arm carries the `never_runs` counter and withholds the row;
the cost arm has no such class and prints `$0.0000`. The engine's own
header records why the class was born (`nika-check/src/energy.rs`): a
ceiling over a task that cannot execute is invented, and the probe that
found it in July saw *« two adjacent rungs disagreeing about the same
task »*. That sentence still describes the pair — the fix landed on one
side.

`$0.0000` here is a PROVEN zero, not the fabricated zero
[15 §the spend-honesty law](../spec/07-conformance.md) bans, so nothing
is dishonest. What is left is the asymmetry: the same task is a row on
one rung and a counted absence on the other, and a reader has to know
which arm they are reading to interpret it. Spec 07 law 3 names the
residual inline rather than claiming a parity that does not exist.

Not blocking · upstream: give the cost arm the same class, or say in the
COST legend that a `$0.0000` row can mean « provably never runs ».

## F-6 · The suite has a family for the workflow and one for the journal — none for the receipt, none for the registry

**Measured 2026-08-13**, after the NEP fold moved twenty design records
into normative spec text. Fourteen distinct laws landed in `spec/` and
`registry/`. The conformance suite proves **three** ·

| Law | Where it lives | Fixture |
|---|---|---|
| journal line bound | 15 §the verifier is a fortress | `runtime/trace/005` |
| `incomplete` | 17 §the end of the run | `runtime/trace/004` |
| the pinned pricing table | 15 §the semantic hash | `runtime/trace/001` + `006` |

The other eleven have none, and the reason is **structural, not
negligence**. The suite has exactly two fixture families ·

- `tests/core/**` — a workflow (`input.yaml`) judged by a static check,
  asserting `valid` + `errors`.
- `tests/runtime/trace/**` — a journal (`trace.ndjson`) judged by the
  walk, asserting a verdict.

Every uncovered law needs a surface neither family models ·

| Uncovered | What it would need |
|---|---|
| artifact decode bounds (`Oversized` · `TooDeep` · `ProofFlood` · `IdOverflow`) | a **receipt** fixture family — these guard the whole-document decoder, not the walk |
| the readable-receipt projection · input origins · blame polarity | the same: a receipt fixture, asserting fields and their rendering |
| the teardown seal (`receipt_digest` · budgets · effects) · the quarantine fold | a journal carrying a VALID ed25519 seal — producible only by running with a key, never by construction |
| the boot manifest (`spec_pin` · `stamper_kind` · `clock` · `seed`) | a shape that asserts prologue CONTENT; absence is honest here, so there is no verdict to key on |
| judged ≠ booted | nothing to hold it: the refusal fires BEFORE the first frame, and the lazy-open law means no journal exists to verify |
| cross-version resume | two engine versions in one fixture |
| provenance tiers (`NIKA-REG-008`) | a **registry** fixture family — a fetch, a policy file, a cache record |
| the spend-honesty rungs (ENERGY · COST) | a shape that asserts RENDERED text; `valid` + `errors` cannot express a rung |

Two of the three fixtures written today only exist because the trace
family could be **extended** (a fourth walk verdict, then a fifth entry
that is not a walk verdict at all, then an optional second leg). That
lever is spent: the next laws need a family, not another field.

Named, not blocking. A law without a fixture is not wrong — all fourteen
were verified against the shipped binary before being written — but
[NEP-0000 §Relationship to conformance](../governance/nep-0000-the-nep-process.md)
is explicit that the proof is the suite's job, so the gap belongs on the
record rather than in the gap between two people's memories.
