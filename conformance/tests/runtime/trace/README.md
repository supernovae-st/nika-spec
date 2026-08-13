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
└── expected-verify.json    { "verdict": "clean" | "finding" | "forged", "note": … }
```

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
