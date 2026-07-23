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

Verdict law (17 §the permit witness · NEP-0007 law 3) · `clean` = the
chain walks and every required frame is present · `finding` = the chain
walks but a NEP-0007 requirement is unmet (the absent witness on an
effectful run · old journals land here honestly) · `forged` = the chain
breaks (any byte edit, insertion, deletion, reorder).
