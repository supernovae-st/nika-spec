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
├── golden.nika.yaml        the workflow the journal ran (001 only)
├── trace.ndjson            the journal under verification
└── expected-verify.json    { "verdict": …, "cost_replay"?: …, "note": … }
```

`verdict` is the WALK's (below). Two optional fields assert what the
walk does not ·

- **`cost_replay`** — the independent budget-meaning leg (15 §the
  semantic hash · the pinned pricing table): `replayed` when the pin
  names a table this engine holds and the budget verdict is re-judged ·
  `refused` when it names one the engine does not · `unrecorded` when
  the journal carries no pin at all. The three arms live at `007`,
  `006` and `001`. The legs never gate each other: a refused
  cost-replay leaves a `clean` walk clean.
- **`prologue`** — `{present: [...], absent: [...]}` over the boot
  manifest's fields (17 §the prologue). It asserts CONTENT, not a
  verdict, which is why it is a field of its own: `absent` is a real
  claim, because a manifest states only what exists and a reader says
  « unrecorded » rather than guessing. An ambient run listing `seed`
  under `absent` is the law holding, not a gap.

Absent fields mean the fixture makes no claim there.

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
about 1.7 KiB, the same trade `yaml-profile/invalid/document-over-cap.nika.yaml`
already makes on the authoring side.
