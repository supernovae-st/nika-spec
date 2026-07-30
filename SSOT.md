# SSOT · where every fact about Nika lives

**Read this before editing anything that teaches Nika** — a number, an example,
a template, a snippet in a doc, a fixture in a test.

The rule that generates all the others:

> **Every fact has exactly ONE home. Everything else that shows it is a
> PROJECTION, and a projection is never hand-typed.**

This file is the map. Where a gate enforces the direction, it is named. Where
no gate exists, that is said plainly — an unenforced SSOT is a hope, not a
rule, and knowing which is which is the point of the document.

---

## §1 · The two roots, and they never mix

```
① THE LANGUAGE FACTS                    ② THE ENGINE FACTS
   spec/canon/ registries                  the binary itself
   (hub projection: canon.yaml)            AGPL-3.0
   Apache-2.0                              "N crates · N tests · N vectors"
   "4 verbs · 28 builtins · 17 providers"  changes when the CODE changes
   changes when the LANGUAGE changes
```

They are orthogonal on purpose, and the licence split mirrors it. A number that
describes the language never comes from the engine, and a number that describes
the engine never enters the spec. Conflating them is how a doc ends up claiming
a language guarantee that is really an implementation detail.

---

## §2 · Language facts · `canon/` → canon.yaml → three targets

```
canon/ registries               ★ THE SOURCE · EDIT HERE
   surface.yaml · builtins.yaml · laws/*.yaml · templates/registry.yaml
   diagnostics/registry.yaml · features.yaml
   │
   │  scripts/ssot-compiler.py --emit-canon    gate: --check-canon · rc=5
   ▼                                           (re-emits · byte-compares)
canon.yaml                      GENERATED HUB · + canon/ssot.lock
   │                              hybrid by design: the §18 EXCEPTIONS
   │                              ledger sections stay AUTHORED inside it
   └── scripts/canon-projectors.py             gate: --check
         ├──▶ THIS repo    *.md          <!-- canon:KEY -->N<!-- /canon -->
         ├──▶ nika-docs    snippets/_canon.mdx        import { CANON }
         └──▶ nika.sh      src/canon.generated.ts     import { CANON }
```

**The law**: a page interpolates `{CANON.x}`. It never hand-types a volatile
language fact. And the hub itself is a projection — a hand edit of
`canon.yaml` outside the ledger sections is refused by CI (the C0 flip),
so « edit here » means the `canon/` registries, nothing downstream.

**Why this exists, measured**: the website said *"13 providers"* in three source
sites while `llms.txt` said 14. Nobody was careless — the number simply lived in
four places and only one of them moved. (And this file inverted the root for
eleven days — it taught `canon.yaml ★ EDIT HERE` while the file's own header
said GENERATED. The map is a projection now; see §9.)

**Verify**: `python3 scripts/ssot-compiler.py --check-canon` ·
`python3 scripts/canon-projectors.py --check`

---

## §3 · Engine facts · the binary → the docs

```
the engine  ── scripts/mintlify-snapshot.sh ──▶ nika-docs _status-snapshot.mdx
```

Crate counts, test counts, hygiene vectors. **Never quote these from memory** —
they drift weekly. If you are about to type one, run the refresh instead.
Honest status: this edge is discipline today — no CI refuses a stale
snapshot (gate owed; the cross-repo rung the estate federation will carry).

---

## §4 · The corpus · one direction, one script

```
spec/examples/          ★ EDIT HERE
spec/templates/         ★ EDIT HERE
       │
       │  engine/scripts/sync-pack.sh <spec-checkout>     ← the ONLY passage
       ▼
engine/crates/nika-pack/pack/     ⚠️ MIRROR · edits here are overwritten
       │
       ├──▶ `nika new --from <t>`     what a BEGINNER receives
       ├──▶ `nika examples show <s>`  what an AGENT reads
       └──▶ nika-onboard 62/62        the gate that refuses a broken scaffold
```

**This is the surface that matters most, and it is not documentation.**

Measured 2026-07-28: six agents wrote workflows from the authoring skill alone
and took 45 check-fix rounds between them, none green first try. One then read
TWO EXAMPLES and wrote their next workflow green in zero rounds. A fresh agent
went 8 rounds to 0 the same way.

**The corpus outperforms the prose reference.** So it is the grounding surface
for every workflow anyone writes with an agent — and what has no example does
not exist, as far as that agent is concerned.

The mapping in `sync-pack.sh` IS the contract: additions to the pack are
deliberate edits to that script, never ad-hoc copies.

---

## §5 · Builtins · the source is Rust

```
engine/crates/nika-catalog/src/data/builtins.rs   ★ ALL_BUILTINS · 28, sorted
       │
       ├──▶ what `nika check` accepts
       ├──▶ what the agent kit teaches   gate: the_kit_never_teaches_a_form_the_engine_refuses
       ├──▶ canon/builtins.yaml seam     gate: the_two_builtin_roots_agree_at_the_seam
       │      (two sovereign roots — the language list and the engine list —
       │       joined at the CONSUMER: the engine test reads the vendored canon)
       └──▶ a builtin has an EXAMPLE     gate: every_builtin_is_shown_or_carries_a_named_debt
```

**The hole is gated now** (2026-07-29 · engine
`nika-cli/src/verbs/examples.rs` tests, same shape as the kit gate pointed the
other way): 24 of 28 builtins appear in the corpus, and the four that do not
ride the test's `OWED` list — each with its reason and the showcase it owes.
The 29th builtin cannot ship silently, and a debt paid by a new lesson must be
struck from `OWED` in the same arc or the test refuses.

| owed | cost of the gap while it lasts |
|---|---|
| `nika:decide` | the DETERMINISTIC decision kernel (spec 11 · W-DEC). An agent that never sees it spends a model call on an `if`. **This one costs money on every generated workflow.** |
| `nika:inspect` | cost · records · dag_info · threads, merged into one door (ADR-088). An agent cannot introspect its own run. |
| `nika:compose` | the agent loop's self-verification intrinsic (ADR-096) — the pattern for a model that WRITES Nika. |
| `nika:tts_generate` | the audio graduate. A showcase gap, not a logic gap. |

---

## §6 · Taught code OUTSIDE the corpus · the largest unguarded surface

Every fenced YAML block in a doc, a README, a test fixture or a source comment
teaches something. The count is a MEASUREMENT — run it, never quote it:

```
git grep -l 'nika: v1' -- ':!*.nika.yaml' | wc -l        # per repo, tracked files
```

Last run 2026-07-29: engine 742 · spec 320 · agents 7 (an earlier pass
reported engine 2869 by counting untracked run traces — the command above
is the reproducible form). Inside THIS repo, 112 of the 213 fenced ```yaml
blocks in tracked *.md carry `nika:` — the surface a dead-forms scanner
should cover and does not yet.

**Guarded**: the agent kit, by `agents/scripts/check-dead-forms.py` — it
extracts every fenced block and refuses a form the engine no longer accepts.

**Unguarded**: everything else. This is the biggest hole in the map, and it is
where dead syntax survives longest: a snippet in a README nobody re-reads keeps
teaching `vars:` years after the field died.

Extending the dead-forms scanner past the kit is owed work.

---

## §7 · The five rules, operationally

```
1  A NUMBER is never typed by hand.
   Import { CANON } or place the <!-- canon:KEY --> marker.

2  AN EXAMPLE is edited in spec/, never in the pack.
   The pack is a mirror. The next sync overwrites you.

3  A CODE SNIPPET in any doc must be CHECKABLE, and ideally checked.
   If it cannot pass `nika check`, it should not be shown as if it could.

4  A BUILTIN without an example is invisible.
   Adding a builtin means adding its showcase in the same arc.

5  ENGINE facts and LANGUAGE facts never cross.
   Crate counts do not enter the spec; verb counts do not come from the binary.
```

---

## §8 · Where to look when you are unsure

| You are about to change… | Edit here | Then |
|---|---|---|
| a count, a verb, a builtin name, a provider | `canon.yaml` | run `canon-projectors.py` |
| an example or a template | `spec/examples/` · `spec/templates/` | `sync-pack.sh` from the engine |
| a builtin's behaviour or args | `nika-catalog/src/data/builtins.rs` | update `canon.yaml`, add a showcase |
| a doc page's prose | that page | never hand-type a fact — import it |
| the engine's own numbers | nothing — they are derived | `mintlify-snapshot.sh` |

---

## §9 · Honest state of enforcement

<!-- estate:map -->

The rows below are DERIVED from `estate.yaml` — regenerate with
`python3 scripts/ssot-map-projector.py --write`; a hand edit here is
refused by `--check` (exit 5), the same contract every projection has.

| generated surface | emitted by | drift refused by |
|---|---|---|
| `.github/requirements.txt` | `uv pip compile --generate-hashes` | `pip install --require-hashes` |
| `canon.yaml` | `python3 scripts/ssot-compiler.py --emit-canon` | `scripts/ssot-compiler.py --check-canon` |
| `canon/laws-index.json` | `python3 scripts/ssot-compiler.py` | `scripts/ssot-compiler.py --check` |
| `canon/ssot.lock` | `python3 scripts/ssot-compiler.py` | `scripts/ssot-compiler.py --check` |
| `canon/ssot.lock.sha256` | `python3 scripts/ssot-compiler.py` | `scripts/ssot-compiler.py --check` |
| `conformance/type-corpus/corpus.jsonl` | `python3 scripts/gen-type-corpus.py --write` | `gen-type-corpus.py --check` |
| `examples/manifest.yaml` | `python3 scripts/showcase-projector.py --write` | `scripts/showcase-projector.py --check` |
| `llms-full.txt` | `python3 scripts/llms-projector.py --write` | `scripts/llms-projector.py --check` |
| `llms.txt` | `python3 scripts/llms-projector.py --write` | `scripts/llms-projector.py --check` |

Provenance floor: 1269 tracked files classified · authored 941 · generated 130 · pinned-copy 4 · testimonial 193 (estate schema 2 · mode observation).

<!-- /estate:map -->

Beyond the derived rows above, gates that live OUTSIDE this repo's estate:

```
✅ GATED elsewhere
   the corpus files                  nika check --native-strict, all of them
   the agent kit                     check-dead-forms.py + 62/62 nika-onboard
   canon ↔ engine builtin roots      the_two_builtin_roots_agree_at_the_seam (engine lib)
   a builtin without an example      every_builtin_is_shown_or_carries_a_named_debt (engine lib)
   a construct without a showcase    every_construct_has_a_showcase (engine lib)

⚠️ UNGATED · discipline only
   taught YAML outside the kit       §6 — run the measurement, then extend the scanner
   engine facts → docs snapshot      §3 — no CI refuses a stale snapshot
```

---

## §10 · Construct coverage · measured, and worse than the builtins

Measured 2026-07-29 over the 43 corpus files. Builtins came back 24/28. The
language's CONSTRUCTS are the same question with a bigger blast radius, and
they came back worse.

**Four core constructs have ZERO examples**, while the spec discusses each of
them at length:

| construct | examples | mentions in `spec/*.md` | what an agent therefore never does |
|---|---:|---:|---|
| composition (`workflow:` under `invoke:`) | **0** | 36 | never calls one workflow from another — despite `check` shipping a whole COMPOSITION rung for it |
| `returns:` (the typed door) | **0** | 47 | never types a task's output; reaches for `schema:` (the out-of-core hatch) or nothing |
| `declassify:` | **0** | 3 | the spec calls it *"the ONLY door"* through the permit-parameterisation taint, and nobody has ever seen one |
| `config:` | **0** | 16 | one of the FOUR value authorities, entirely unwitnessed |

**Two more are shown exactly once**, which is not enough to read a pattern from:

| construct | examples |
|---|---:|
| `on_finally:` | 1 |
| the `failure` edge predicate | 1 |

Everything else is healthy: `invoke:` 37 · `infer:` 30 · `const:` 30 · `on_error:`
23 · `when:` 16 · `schema:` 16 · `after:` 12 · `inputs:` 12 · `for_each` 8 ·
`retry` 7 · `agent:` 4.

### Why this is the most expensive gap on the map

The corpus is the grounding surface (§4). The spec explaining a construct in
prose does not put it in an agent's reach — **measured, examples beat the prose
reference 8 rounds to 0.** So a construct with no example is, operationally, a
construct the language does not have.

Two of these are not conveniences. `declassify:` is the only sanctioned way
through a taint, so an author who meets that wall has no visible door and will
either widen a boundary or abandon the workflow. And composition is how anything
non-trivial is built at all.

### Owed — settled 2026-07-29 PM

```
1  ✔ the four zero-coverage constructs have their lessons (08-config ·
     09-returns · 10-compose ×2 · 11-declassify · 12-failure-routing) —
     the path covers 16/16, and the claims in those files were RUN, not
     written (the door map, the config refusal, the ⊘ gate line)
2  still open · a second example for on_finally and the failure predicate
3  ✔ the ratchet holds both axes in the engine's lib battery:
     every_construct_has_a_showcase refuses the 17th uncovered key,
     every_builtin_is_shown_or_carries_a_named_debt refuses the silent 29th
```


---

## §11 · The next cut · lessons and templates teach the SAME shapes

Found while measuring the learning path with the construct index, 2026-07-29.
Not acted on — recorded because it is the largest remaining duplication and it
needs a decision, not a reflex.

### The measurement that surfaced it

Turning the index on the path itself gave a clean result and one anomaly:

```
01-hello                infer:
02-parallel-fanout      ⚠ nothing new
03-exec-pipeline        exec: · when: · after: · on_finally:
04-schema-retry         retry: · schema: · inputs:
05-fetch-chain          invoke: · on_error:
06-code-review          agent:
07-for-each-locales     for_each:
08-config-values        config:
09-returns-typed-door   returns:
10-compose-child        ⚠ nothing new      (the callee half of lesson 10)
10-compose-pipeline     workflow:
11-declassify-the-door  declassify:
12-failure-routing      ⚠ nothing new

⟹ 16/16 constructs covered · none missing
```

**The path now covers the whole language.** The three ⚠ rows are not bad
lessons — they are the index's blind spot. `02` teaches fan-out-and-merge, `12`
teaches how failures route, and neither introduces a KEY. They teach a SHAPE:
a combination of keys that forms a recognisable pattern.

So there are two axes, and the index sees one:

```
KEYS     what syntax exists            for_each: · declassify:
SHAPES   how keys COMBINE              fan-out+merge · failure routing · composition
```

### The duplication

Templates are named by shape. Lessons, it turns out, teach the same shapes:

```
TEMPLATE (fillable)      LESSON (readable)        same shape
agent-loop               06-code-review               ✓
fanout                   02-parallel-fanout           ✓
                         07-for-each-locales          ✓
chain                    05-fetch-chain               ✓
gate-and-act             03-exec-pipeline             ~
```

13 lessons + 10 templates = 23 files, with five pairs teaching one thing twice
under two names in two directories.

### The question, unanswered on purpose

A lesson is MINIMAL — it introduces one idea with nothing else in the way. A
template is COMPLETE — it is a working shape with the holes marked. Those are
genuinely different artifacts for genuinely different moments.

**But is that difference worth two directories and two names for one shape?**

Since the corpus rebuild all ten templates run green offline, so a template is
no longer "the broken one until you fill it". The distinction weakened, which is
exactly when a merge becomes thinkable and exactly when it should be examined
rather than assumed.

Three ways to go:

```
1  MERGE ON SHAPE   one file per shape, SLOT-marked, readable AND fillable
                    23 files → ~18 · one name per idea
                    cost: loses the minimal-teaching version

2  KEEP BOTH, name the relationship
                    05-fetch-chain says « the fillable form is templates/chain »
                    zero files moved · the duplication becomes navigable

3  KEEP AS IS       the two artifacts serve two moments and the cost is 5 files
```

### What is owed either way

**The index must learn the SHAPES axis.** Today `nika examples teaches` answers
« which file shows `for_each:` » and cannot answer « which file shows fan-out
and merge », which is the question an author with an intent actually has. The
routing table in the authoring skill already carries the shape vocabulary
(chain · gate-and-act · fanout · etl-state · agent-loop · human-gated-ship) and
it is not derived from anything — a hand-maintained list beside a derived one.
