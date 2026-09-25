# 🦋 Nika Project OS

**One public operating surface. Zero second backlog.**

`project-os.yaml` is the projection contract. It declares the sources,
field writers, visual grammar, eight lenses, six Pulse charts and automation.
`timeline/timeline.yaml` remains the source of the record and gates.
GitHub Issues, pull requests and releases remain the sources of live work.

The Project overview begins with `project.product_brief` from the same manifest:
the product goal, each component's role, the dated qualification boundary and
links to the existing acceptance issues. Refresh this authored brief when a
delivery changes the evidence; the projector publishes it with the operating
guide. It neither creates a second backlog nor changes issue acceptance.

The projector follows six laws:

1. Stable `SSOT ID` values match items across runs.
2. A field has one writer.
3. Reconciliation is incremental. It never wipes the Project.
4. Unknown and retired items are retained as `◇ quarantined` or
   `◌ orphaned`, so Insights history is not destroyed.
5. Every projector-owned classification carries one stable semantic sigil.
6. `Signal` is derived attention. `Priority` and `Effort` remain human choices.

Closed sources settle in place. The reconciler reads each retained item's
actual source state from the Project snapshot; a closed or merged source
moves to its terminal Stage — `● settled · completed at source`,
`● settled · merged at source` or `○ closed · not integrated` — with Signal
`● settled`, leaving the active lenses. Closure is never shipment: `Proof`
stays `◌ pending` until the record itself proves the work. A source that
cannot be read keeps no lifecycle claim: the orphan is cleared to
`? unknown`, never painted done.

## 🚨 Signal

| Value | Meaning |
|---|---|
| `🚨 attention` | blocked, failing or changes requested |
| `👀 review` | a pull request needs a human decision |
| `▶ active` | owned work is moving |
| `⏭ queued` | ready for an owner or its turn |
| `✓ ready` | approved and green, ready to integrate |
| `● settled` | already part of the record |

Run the offline audit:

```bash
python3 project/verify.py --offline
```

Preview a live reconciliation without writing:

```bash
BOARD_PROJECT_TOKEN=... python3 -m project.cli --check
```

Apply the live reconciliation:

```bash
BOARD_PROJECT_TOKEN=... python3 -m project.cli --apply
```

GitHub does not expose view and Insights creation through its public
API. Their complete browser recipe lives in `project-os.yaml`, and the
live audit verifies every view property that GitHub does expose. View
membership and layouts are API-verifiable; saved tab order remains a
browser QA check because the API returns creation order.
