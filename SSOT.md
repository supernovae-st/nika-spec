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
   spec/canon.yaml                         the binary itself
   Apache-2.0                              AGPL-3.0
   "4 verbs · 28 builtins · 17 providers"  "N crates · N tests · N vectors"
   changes when the LANGUAGE changes       changes when the CODE changes
```

They are orthogonal on purpose, and the licence split mirrors it. A number that
describes the language never comes from the engine, and a number that describes
the engine never enters the spec. Conflating them is how a doc ends up claiming
a language guarantee that is really an implementation detail.

---

## §2 · Language facts · `canon.yaml` → three targets

```
canon.yaml                      ★ THE SOURCE · 21 keys
   │                              counts · verbs · builtins · providers
   │                              error_codes · templates · extract_modes …
   │
   └── scripts/canon-projectors.py
         ├──▶ THIS repo    *.md          <!-- canon:KEY -->N<!-- /canon -->
         ├──▶ nika-docs    snippets/_canon.mdx        import { CANON }
         └──▶ nika.sh      src/canon.generated.ts     import { CANON }
```

**The law**: a page interpolates `{CANON.x}`. It never hand-types a volatile
language fact.

**Why this exists, measured**: the website said *"13 providers"* in three source
sites while `llms.txt` said 14. Nobody was careless — the number simply lived in
four places and only one of them moved.

**Verify**: `python3 scripts/canon-projectors.py --check`

---

## §3 · Engine facts · the binary → the docs

```
the engine  ── scripts/mintlify-snapshot.sh ──▶ nika-docs _status-snapshot.mdx
```

Crate counts, test counts, hygiene vectors. **Never quote these from memory** —
they drift weekly. If you are about to type one, run the refresh instead.

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
       ├──▶ canon.yaml `builtins:`       (kept in step by hand today)
       └──▶ ⚠️ NOTHING checks that a builtin has an EXAMPLE
```

**The open hole, measured 2026-07-29**: 24 of 28 builtins appear in the corpus.
Four are invisible to any agent that learns from examples:

| missing | cost of the gap |
|---|---|
| `nika:decide` | the DETERMINISTIC decision kernel (spec 11 · W-DEC). An agent that never sees it spends a model call on an `if`. **This one costs money on every generated workflow.** |
| `nika:inspect` | cost · records · dag_info · threads, merged into one door (ADR-088). An agent cannot introspect its own run. |
| `nika:compose` | the agent loop's self-verification intrinsic (ADR-096) — the pattern for a model that WRITES Nika. |
| `nika:tts_generate` | the audio graduate. A showcase gap, not a logic gap. |

Ratchet owed: a test comparing `ALL_BUILTINS` against the corpus, so the 29th
builtin cannot ship without a showcase.

---

## §6 · Taught code OUTSIDE the corpus · the largest unguarded surface

Every fenced YAML block in a doc, a README, a test fixture or a source comment
teaches something. Measured, files carrying `nika: v1` outside `.nika.yaml`:

```
engine    2869      spec  323      website  83      docs  57      vscode  55
```

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

```
✅ GATED · a machine refuses the drift
   canon.yaml → 3 targets            canon-projectors.py --check
   spec → pack                       sync-pack.sh + nika-pack integrity tests
   the agent kit                     check-dead-forms.py + 62/62 nika-onboard
   the 43 corpus files               nika check --native-strict, all of them

⚠️ UNGATED · discipline only
   taught YAML outside the kit       ~3400 files across six repos
   a builtin without an example      4 today
   a language construct without      never measured: the 4 verbs, edge
     a showcase                        predicates, for_each, on_error, retry,
                                       composition
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

### Owed

```
1  showcase the four zero-coverage constructs · composition and declassify first
2  a second example for on_finally and the failure predicate
3  the coverage ratchet, extended: a construct in the spec with no example is
   a build warning, the same way a builtin without one should be
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
