# Receipt reading contracts · LIVE (engine-consumed)

The reading half of [15 · Proof](../../../spec/15-proof.md) §the one
receipt (NEP-0014 law 3): a REAL run receipt (`receipt_format: 1` ·
produced by a conformant engine, exported with
`nika trace evidence --workflow <file>`) plus what its readable
projection MUST say. The static gate ignores this tier (no
`input.yaml`); the executable proof is `nika trace receipt explain`.

## Contract shape

```
tests/runtime/receipt/<NNN-name>/
├── receipt.json            the receipt under reading
└── expected-explain.json   { "unprojected": [ … ], "note": … }
```

`unprojected` is the list of field paths the schema holds no readable
projection for — **empty is the passing state**. A receipt whose schema
covers every field it carries lists nothing.

## The law this family holds

Every field of the receipt schema carries a readable projection IN the
schema; a field without one is named rather than rendered or silently
dropped. The ratchet is the point — the readable half can never fall
behind the machine half.

And the projection is **never the evidence**. `explain` is a reading,
`verify` is the proof, and they sit at two trust levels: a surface that
lets the first pass for the second has quietly made prose
authoritative. The verb prints that sentence itself, above every
projection.

## Why a pair

`001` is the real receipt and lists nothing. `002` is `001` plus exactly
one unknown key. The two differ by one field and their readings differ
by that field — which is what makes `001`'s empty list a certificate
rather than a hopeful default: an `unprojected: []` that would stay
empty under a mutation would be proving nothing at all.
