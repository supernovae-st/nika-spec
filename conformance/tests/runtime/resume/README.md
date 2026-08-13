# Resume judgment contracts · LIVE (engine-consumed)

The cross-version half of [17 §the fold law](../../../spec/17-trace.md)
(NEP-0014 law 4): a journal that RECORDS one engine version, resumed by
another, and what the judgment must do. The static gate ignores this
tier (no `input.yaml`); the executable proof is
`nika run <workflow> --resume <trace> [--resume-compat <version>]`.

## Contract shape

```
tests/runtime/resume/<NNN-name>/
├── trace.ndjson           the journal being resumed (records its engine)
├── golden.nika.yaml       the workflow it ran (001 only)
└── expected-resume.json   { "resume_compat": …|null, "verdict": …, "exit": …, "note": … }
```

`resume_compat` is the declaration the operator makes on the command
line — `null` means none was made, which is a fixture state, not a
missing field.

## Why three, on one journal

The three journals are **byte-identical**. Only the declaration differs ·

| fixture | declaration | verdict |
|---|---|---|
| `001` | none | refused · both versions named |
| `002` | the recorded version, exactly | proceeds · attested on the new boot manifest |
| `003` | some other version | **still refused** |

`003` is what makes `002` mean anything. If any token discharged the
judgment, the door would be a force flag — and a blanket force is
precisely the silent degradation this law was written to retire: the old
implicit fallback replanned an empty plan and called it a resume.

## Constructed, and why it has to be

A second engine build cannot be produced by running something. So the
journal's recorded `engine_version` is rewritten in the boot manifest
and every later `chain` recomputed over exact previous bytes — the file
stays byte-verifiable and `trace verify` reads it `OK`. The only thing
wrong with this journal is the version it claims, which is exactly the
subject.
