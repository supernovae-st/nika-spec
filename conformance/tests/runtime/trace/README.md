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

`verdict` is the WALK's (below). `cost_replay` is optional and asserts
the independent budget-meaning leg (15 §the semantic hash · the pinned
pricing table) — `refused` when the pin names a table the engine does
not know, `unrecorded` when the journal carries no pin at all. Absent
means the fixture makes no claim there. The two legs never gate each
other: a refused cost-replay leaves a `clean` walk clean.

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
  verify exit stays the tier ladder's.
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
continue — and it exits nonzero, where every walk verdict exits on the
tier ladder.

A bound fixture costs its bound: `005` carries a 1 MiB line because
that is the only way to cross a 1 MiB bound. One repeated byte packs to
about 1.7 KiB, the same trade `yaml-profile/invalid/document-over-cap.nika.yaml`
already makes on the authoring side.
