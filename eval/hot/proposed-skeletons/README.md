# Proposed skeletons — NOT CANON

These files **must not** enter `templates/` or `canon/templates/registry.yaml`
until they have: real sha256 row, INDEX generation, negative fixture, golden,
and `nika check` + mock rehearsal.

They exist so compiler work can **read a composition law** without pretending
the 22-file registry grew.

| File | Decision | Why not canon tonight |
|---|---|---|
| `lookup-and-enrich.nika.yaml` | PATTERN + proposed | Needs digest/INDEX/rehearsal; lookup is a JSON fixture, not HubSpot |
| `facts-to-draft.nika.yaml` | PATTERN + proposed | Fact-preservation law; chain does not keep `facts` as output |
| `known-path-agent-fallback.nika.yaml` | PATTERN + proposed | agent-loop is whole-workflow EXPLORE; this is the exceptional branch |

`approve-and-apply` and `notify-effect` are **not** here: factor
`human-gated-ship` and `gate-and-act`.
