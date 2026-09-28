# Trace verify contracts · LIVE (engine-consumed)

The execution-half contracts of [17 · Trace](../../../spec/17-trace.md)
(NEP-0007): a REAL journal (`trace.ndjson` · produced by a conformant
engine · chained · byte-verifiable) plus the verify verdict the walk
MUST reach. The static gate ignores this tier (no `input.yaml`); the
executable proof is engine-side (`nika trace verify` · the reference
engine replays every fixture in its conformance battery and holds the
verdict).

## Contract shape

```
tests/runtime/trace/<NNN-name>/
├── golden.nika        the workflow the journal ran (when supplied)
├── trace.ndjson            the journal under verification
└── expected-verify.json    { "verdict": …, "cost_replay"?: …, "note": … }
```

`verdict` is the WALK's (below). Optional fields assert what the
walk does not ·

- **`cost_replay`** — the independent budget-meaning leg (15 §the
  semantic hash · the pinned pricing table): `replayed` when the pin
  names a table this engine holds and the budget verdict is re-judged ·
  `refused` when it names one the engine does not · `unrecorded` when
  the journal carries no pin at all. The three arms live at `007`,
  `006` and `001`. The legs never gate each other: a refused
  cost-replay leaves a `clean` walk clean.
  The command-level differential checks the engine's separate `COST-REPLAY`
  report; missing, ambiguous or unrecognized evidence fails this assertion.
  A known pin alone does not stand in for an actual budget re-judgment.
- **`prologue`** — `{present: [...], absent: [...]}` over the boot
  manifest's fields (17 §the prologue). It asserts CONTENT, not a
  verdict, which is why it is a field of its own: `absent` is a real
  claim, because a manifest states only what exists and a reader says
  « unrecorded » rather than guessing. An ambient run listing `seed`
  under `absent` is the law holding, not a gap.
  Optional `input_origins` is the exact input-name → channel map decoded
  from the prologue's JSON-string `inputs` field (04 §typed workflow
  inputs). Missing, malformed, duplicated or misattributed origins fail
  this assertion even if the journal's chain is intact. This names the
  supplying channel; it proves neither caller identity nor authorization.
  The command-level differential checks these fields independently of the
  chain verdict. Its selftests include negative channel substitutions.

Absent fields mean the fixture makes no claim there.

`items` optionally maps task ids to the complete expected item arrays, or
`null` when no complete table may be projected. Fixture `008` is a real
native fan-out with paged evidence; `009` removes its first page and
recomputes the unkeyed chain. Both walks are internally consistent, but
only `008` permits a complete item projection. This is a semantic
completeness check, not an authenticity claim against coherent rewriting.
The command-level differential compares these assertions to the engine's
`nika trace outputs <trace> --json` task projection. Unsupported commands,
nonzero exits, malformed output and duplicate task identities fail the
assertion; a runner never silently skips it or reconstructs the expected
table on the engine's behalf. Row order and typed field values matter.
The expectation JSON must also reject duplicate keys at every depth and
non-JSON numeric constants. A present `items` map must name at least one
nonempty task id, with an array or `null` for each value. Omit `items` to make
no claim; an empty row array is a valid assertion of a complete empty table.
An invalid expectation is a fixture error, never an engine success or failure.
Invalid UTF-8 and exponent overflow (for example `1e999`) are fixture errors
too. A `cost_replay` claim must name one of its three arms; a `prologue` claim
must be an object with correctly typed field lists and origin map. Presence
and absence lists use unique nonempty names and cannot claim both for one
field. These checks all precede the first engine invocation.
The prologue key set is closed to `present`, `absent` and `input_origins`;
unknown spellings are errors. Its reader skips leading blank journal lines,
but never skips a malformed initial event to find a later boot. An unreadable
initial event fails the prologue claim, without reclassifying the engine call
as a crash. Cost reports retain separate stdout/stderr line boundaries, and
the explicit re-judgment line must follow its marker in the same stream.

Fixtures `011` and `012` retain actual inline and paged item observations
with `failed`, `cancelled` and `never_started` rows. `013` is the historical
zero-cancelled count omission. `014` omits a required cancelled count, `015`
changes that count, and `016` substitutes an unknown paged status; their
chains remain consistent but their item projections MUST be incomplete.
Each case records its source hash, engine pin and exact mutations in
`provenance.json`. Re-chaining these unkeyed negative fixtures tests the
reader's semantic completeness rules, never authenticity against rewriting.

Verdict law · four classes, and the first three all mean « the chain
walks » ·

- `clean` (17 §the permit witness · NEP-0007 law 3) — the chain walks
  and every required frame is present, the lifecycle terminal included.
- `finding` — the chain walks but a NEP-0007 requirement is unmet (the
  absent witness on an effectful run · old journals land here honestly).
- `incomplete` (17 §the end of the run · NEP-0011 law 3) — the chain
  walks and no lifecycle-terminal frame is ever reached: the run was
  killed or crashed between writes. Its own class on purpose — never
  success, never silently failure, never forgery. A dying process cannot
  attest its own death, so the classification is the READER's, and the
  verify exit is `incomplete`'s own class (5 · engine ADR-129 · 0.118):
  never 0 (a walk that reached an end), never 2 (forged).
- `forged` — the chain breaks (any byte edit, insertion, deletion,
  reorder).

A journal whose LAST line is half-written is a fourth thing again (a
torn tail · a crash mid-write, not tampering) and the engine names it
separately: conflating it with `forged` would make every crashed run
look tampered with.

`refused` is the fifth entry and the only one that is NOT a walk
verdict: a decode bound fired **before** the walk ran (15 §the verifier
is a fortress · the 1 MiB line bound · the 256 MiB file bound), so the
journal has no verdict at all. Refusal is total — never a truncate and
continue — and it exits nonzero, where every walk verdict that reached
an end exits on the tier ladder and `incomplete` exits on its own class.

A bound fixture costs its bound: `005` carries a 1 MiB line because
that is the only way to cross a 1 MiB bound. One repeated byte packs to
about 1.7 KiB, the same trade `yaml-profile/invalid/document-over-cap.nika`
already makes on the authoring side.
