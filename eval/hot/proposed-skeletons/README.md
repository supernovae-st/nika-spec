# Proposed skeletons — NOT CANON

These files **must not** enter `templates/` or `canon/templates/registry.yaml`
until they have: real sha256 row, INDEX generation, negative fixture, golden,
and `nika check` + mock rehearsal.

They exist so compiler work can **read a composition law** without pretending
the 22-file registry grew.

| File | Decision | Why not canon tonight |
|---|---|---|
| `lookup-and-enrich.nika` | PATTERN + proposed | Needs canon admission; lookup is a local JSON fixture, not HubSpot |
| `facts-to-draft.nika` | PATTERN + proposed | Fact-preservation law; chain does not keep `facts` as output |
| `known-path-agent-fallback.nika` | PATTERN + proposed | agent-loop is whole-workflow EXPLORE; this is the exceptional branch |

`approve-and-apply` and `notify-effect` are **not** here: factor
`human-gated-ship` and `gate-and-act`.

Run `python3 eval/hot/rehearsal.py --engine /path/to/nika` from the repository
root to check and rehearse the candidates offline. The harness creates a
temporary directory with the fixture data; it performs no network or paid model
calls. It checks missing-data refusal, preserves the typed facts beside generated
prose, and exercises both known classes and the unknown-only agent branch.
These are wiring proofs, not HOT promotion or classifier quality measurements.
