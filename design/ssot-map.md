# SSOT map — every canonical set, its one source, its projectors, its drift gate

The Nika estate runs on one discipline: **every canonical set has exactly one
source of truth; every other appearance is a projection with a gate.** Values
change spec-first — the source and its prose move in the same commit, the
projectors re-derive everything else, and each consumer follows through its own
pinned, gate-judged pull. No surface re-derives semantics locally; no count is
ever hand-written downstream. This file is the map of those arrows.

## 1 · The sets and their sources (this repo)

| Canonical set | Source of truth | Normative prose | Drift gate |
|---|---|---|---|
| Envelope marker (`nika: v1` — forever) | `spec/01-envelope.md` | same | conformance fixtures |
| The 4 verbs | `canon.yaml: verbs` | `spec/02-verbs.md` | `canon-projectors.py --check` |
| Task grammar — the two doors (`with:` / `after:`), gate v2, `when:`, `for_each` | `spec/03-dag.md` + `schemas/workflow.schema.json` | prose wins on conflict (`spec/07`) | conformance runner + reference model (`reference/semantics.py` differential) |
| Variables — namespaces, boundary law, `${{ }}` CEL | `canon.yaml: namespaces` + `spec/04-variables.md` | same | conformance fixtures |
| Type core (`types:` · `returns:` · `decode:`) | `spec/09-types.md` + `schemas/workflow.schema.json` `$defs.typeExpr` | same | `gen-type-corpus.py` corpus + conformance |
| Builtins | `canon.yaml: builtins` | `stdlib/builtins-v0.1.md` | `canon-projectors.py --check` |
| Providers (local-first order) | `canon.yaml: providers` | `stdlib/providers-v0.1.md` | same |
| Extract modes (`nika:fetch`) | `canon.yaml: extract_modes` | `stdlib/extract-modes-v0.1.md` | same |
| Error codes / namespaces / categories | `canon.yaml: error_*` | `spec/05-errors.md` (the table is the normative floor) | same + conformance |
| Gate predicates + graph edge kinds | `spec/03-dag.md` (closed sets, deliberately not counted in canon) | same | `gen-gate-matrix.py` matrix fixtures |
| Templates (the routing skeletons) | `templates/` + `canon.yaml: templates` | `templates/README.md` | sha-pinned catalogs downstream |
| Examples + showcases | `examples/` + `examples/manifest.yaml` (hashed) | same | `showcase-projector.py --check` |
| MCP oracle tools | `canon.yaml: mcp.tools` (reference: the engine's MCP crate) | same | `canon-projectors.py --check` |
| One-voice phrasing | `canon.yaml: canonical_phrasing` | quoted verbatim everywhere | prose review |

## 2 · In-repo projectors (each idempotent · `--check` in CI)

`canon-projectors.py` (counts → marked prose) · `llms-projector.py`
(`llms.txt` + `llms-full.txt`) · `showcase-projector.py` ·
`authoring-projector.py` · `starters-projector.py` · `design-projector.py`
(tokens → consumer design surfaces) · `gen-gate-matrix.py` (the gate-v2
matrix fixtures) · `gen-type-corpus.py` (the type corpus). A second run must
produce zero diff; CI runs every `--check` leg on each push.

## 3 · Downstream consumers (public repos · pinned, never tracking)

| Consumer | What it takes | How drift dies |
|---|---|---|
| `supernovae-st/nika` (engine) | the whole pack, vendored at `SPEC_PIN` (an exact commit — never a branch) | conformance suite in CI at the pin · daily `spec-pin-heal` PR advances it · its own gates judge |
| `supernovae-st/nika.sh` (site) | catalogs (templates · tools · errors · providers · language) via its `scripts/build-*.mjs` | vitest drift gates byte-diff every generated surface · `spec-resync` cron opens one idempotent PR on drift |
| `supernovae-st/nika-docs` | the canon snippet (projected from `canon.yaml`) + prose pages | docs gate re-checks the snippet · counts render from the snippet, never typed |
| `supernovae-st/nika-vscode` | `SPEC_PIN` + the JSON schema | its `spec-pin-heal` + parity CI |
| `supernovae-st/nika-client` (SDK) | conformance fixtures for its e2e | CI at the pin |
| `supernovae-st/nika-agents` (kit) | engine-mirror files byte-pinned by sha256 (`mirror.json`) | `resync-mirror.py` + versions-agree gate |
| `supernovae-st/nika-registry` | the spec as oracle — every entry re-proven (R4) at verify time | nightly `verify` re-proves all entries |

## 4 · The change protocol

1. Change the value at its source (`canon.yaml` and/or the owning chapter) —
   count and prose in the **same commit**.
2. Run the projectors (`--write`), commit the regenerated surfaces with it.
3. Consumers follow by pin-bump PRs (cron-opened or deliberate), each judged
   by its own gates — never by hand-editing a projection.
4. A release train re-certifies the release-coupled surfaces (registry
   entries, tap, mirrors) against the shipped binary.

One direction only: **spec → projections → consumers.** Anything that needs
the arrow reversed is a spec change request, not an edit.
