# canon/EXCEPTIONS.md · the exception ledger (SSOT-1 §18)

> Canon-flip import 2026-07-17 (C0). Every canon.yaml section that did NOT
> enter a sealed registry at the import wave is declared HERE — one row per
> section, owner + deadline + reason. Nothing is forced into a wrong-shaped
> registry (SSOT-1 §28 zero meaning change) and nothing is skipped silently
> (§29). `scripts/ssot-compiler.py --check-canon` declares each of these as
> an explicit SKIP in its output — the compiler's skip list and this ledger
> MUST stay in lockstep (a section in one and not the other is drift).
>
> The IMPORTED sections (gated by `--check-canon` · rc=5 on divergence) are:
> `verbs` · `namespaces` (→ canon/surface.yaml) · `builtins`
> (→ canon/builtins.yaml) · `templates` (→ canon/templates/registry.yaml) ·
> `error_codes` (→ canon/diagnostics/registry.yaml) ·
> `mcp.protocol_versions` (→ canon/features.yaml) · plus the
> `outcome_transitions.classes` coherence gate and the derivable half of
> `error_namespaces`.

| Section (canon.yaml) | Owner | Deadline | Reason |
|---|---|---|---|
| `counts` | C0 | C1 | counts = derived by parity gate (`--check-canon` verifies `count == len(items)` for every counted section, and registry parity for the imported ones) · never copied · the block becomes a pure projection at the flip |
| `providers` (16) | C0 | C1 | needs registry home ruling (builtins-section vs registre propre · plan row « ruler au flip ») |
| `extract_modes` (9) | C0 | C1 | needs registry home ruling (surface vs types · extract = grammaire · plan row) |
| `error_namespaces` (21 · PARTIAL) | C0 | C1 | 19/21 derived from the imported diagnostic rows and GATED (a row namespace outside the canon set = rc 5) · `NIKA-IMPL` + `NIKA-PROVIDER` carry zero v0.1 codes (canon.yaml AND spec/05-errors.md concrete table) → underivable · reserved-row ruling owed (FINDING CF-09) |
| `error_categories` (12) | C0 | C1 | the sealed `diagnosticRow` has no category field · each imported row carries its category documentarily in `notes` (greppable `category: <c>`) · registry home ruling owed (FINDING CF-10) |
| `outcome_transitions.legal` + `.payload` | C0 | C1 | the (class × cause) table-13 registry home is owed · `.classes` IS gated (`--check-canon` · vs the sealed `outcome_class` enum) · known kernel-ahead causes: `budget_exhausted` (LAW-OUTCOME-0403) + `deadline_exceeded` (LAW-OUTCOME-0402) = FINDINGS CF-07/CF-08, never silent |
| `pillars` (5) | C0 | C1 | studio vocabulary · stays authored per operator reco |
| `lifecycle_product` (4) | C0 | C1 | studio vocabulary · stays authored per operator reco |
| `lifecycle_decision` (4) | C0 | C1 | studio vocabulary · stays authored per operator reco |
| `lifecycle_risk` (4) | C0 | C1 | studio vocabulary · stays authored per operator reco |
| `diamond_layers` (7) | C0 | C1 | studio vocabulary · stays authored per operator reco |
| `steal_pattern_tiers` (4) | C0 | C1 | studio vocabulary · stays authored per operator reco |
| `severity` (4) | C0 | C1 | studio vocabulary · stays authored per operator reco |
| `mcp.tools` (9) | C0 | C1 | engine-verified projection (`crates/nika-mcp/src/tools.rs` registry) · features-registry home ruling owed (runtime_capability candidates · sister of the imported `mcp.protocol_versions`) |
| `canonical_phrasing` (10) | C0 | C1 | the F2 one-voice phrasing registry · `canon/snippets/` home ruling owed (phrase-level rows · sweep tooling reads `match:` fragments) |
| `schema_version` | C0 | C1 | canon.yaml's own projection marker (v1) · **flip disposition (CF-13)**: SURVIVES the flip verbatim — the reader contract depends on it (`scripts/canon-projectors.py` exits 2 on an unknown version · monorepo derive gates read it) · the original « dies at the flip » intent rides the C1 projector cascade, never a silent removal |

## Findings register (canon-flip import · SSOT-1 §29)

- **CF-01** · canon.yaml `namespaces` (LOCKED at v1: `vars · with · tasks ·
  env · secrets`) vs kernel laws LAW-SURFACE-0201/LAW-GRAMMAR-0201/0202
  (R3a: the four-authority family `inputs/config/const/secrets` · `vars`/`env`
  are dead forms at the refonte cascade). Timeline-scoped dual truth (v1 live
  vs refonte target) — the surface rows carry the LIVE v1 namespaces with the
  finding declared in their notes; the cascade retires them with
  `replaced_by`, never silently.
- **CF-02** · pre-import `canon/builtins.yaml` carried TWO rows for
  `nika:jq` (a second truth) · merged at import, both verbatims preserved in
  the merged row's notes; the erroneous `LAW-TEMPORAL-0411` citation on jq
  (a wait-scoped law whose `builtins` ref is `nika:wait`) dropped, declared.
- **CF-03** · pre-import seed `error_plane` values (`NIKA-JQ` ·
  `NIKA-NIKAWAIT`) contradict stdlib/builtins-v0.1.md
  (`NIKA-BUILTIN-JQ` / `NIKA-BUILTIN-WAIT` families) · corrected per the doc,
  declared in row notes.
- **CF-04** · stdlib/builtins-v0.1.md category table sums 27 while its total
  row says 28 — `nika:decide` has no category row in the prose table · the
  sealed `builtinRow` enum carries `decision` · assigned per enum.
- **CF-05** · the diagnostics registry carries 11 kernel-born `NIKA-YAML-*`
  rows whose namespace `YAML` is absent from canon.yaml `error_namespaces`
  (21) · the kernel is AHEAD of the canon projection · disposition owed at
  the flip · `--check-canon` reports them as registry-ahead rows.
- **CF-06** · 3 codes are `transient: engine-assessed` at the source
  (`NIKA-INFER-001` · `NIKA-MCP-001` · `NIKA-MCP-002`) · the sealed boolean
  `retryable` cannot carry it · rows hold `false` as the declared static
  floor (not a denial) · ruling owed C1.
- **CF-07** · LAW-OUTCOME-0403 mints cause `budget_exhausted` (« nouvelle row
  table 13 ») · canon.yaml `legal.failure` does not carry it yet ·
  kernel-ahead · table-13 home owed C1.
- **CF-08** · LAW-OUTCOME-0402 mints cause `deadline_exceeded` (cancelled) ·
  canon.yaml `legal.cancelled` does not carry it yet · kernel-ahead ·
  table-13 home owed C1.
- **CF-09** · `NIKA-IMPL` + `NIKA-PROVIDER` namespaces carry zero v0.1 codes
  → underivable from rows (see ledger row `error_namespaces`).
- **CF-10** · `error_categories` unrepresentable in the sealed
  `diagnosticRow` (see ledger row).
- **CF-11** · spec/05-errors.md §namespaces TABLE lists 15 namespaces while
  its own §concrete-codes table (and canon.yaml) uses 21 — `ASSERT · COMP ·
  LOCK · DECIDE · POLICY · PORT` have codes but no namespace-table row ·
  prose-internal lag, import untouched (canon.yaml is the import source) ·
  prose fix owed at the flip cascade.
- **CF-12** (the flip · `--emit-canon`) · the 2 SSOT-1 §27 seed rows
  `NIKA-AGENT-001` + `NIKA-AGENT-002` (byte-untouched at the import wave per
  the diagnostics `$comment`) are law-minted (LAW-OUTCOME-0403/0402 · causes
  `budget_exhausted`/`deadline_exceeded`) and do NOT carry the canon.yaml
  v0.1 projection fields (their `condition` is the law-anchored reservation,
  not the canon failure text · no `category:`/`transient:` note greppables).
  Their 2 canon.yaml item lines stay AUTHORED (template-carried by the
  emitter · `SEED_CARRIED_CODES`) until the C1 diagnostics minting unifies
  them · id membership stays gated (subset check) · never silent.
- **CF-13** (the flip) · `schema_version` SURVIVES the flip verbatim (see
  ledger row) — the « dies at the flip » wording predates the reader census:
  `canon-projectors.py` refuses unknown versions (exit 2) and the monorepo
  derive/fix gates read the marker · retirement rides the C1 projector
  cascade with its own consumer sweep.

## The flip (C0 · `--emit-canon` · SSOT-1 §21-23)

canon.yaml is a **generated projection** since the flip: `--emit-canon`
re-derives the gated surfaces from the registries (counts by `len(items)` ·
verbs/namespaces from the surface spellings + the notes-carried « … »
verbatim semantics · builtins/templates from row ids · error_codes fields
from the import-c0 rows: `condition` == failure text · category/transient
note greppables · mcp.protocol_versions via the bijective id transform,
`latest` = max · outcome classes from the sealed enum) and carries the 16
ledger sections above + every prose comment + the authored item SEQUENCE
verbatim from the current file. A GENERATED header tops the file (body
sha256 · own digest detached per PAA-006). `--check-canon` verifies header
presence + file == regeneration byte-for-byte (rc 5 · CI red on any manual
edit of a generated surface — editing an authored ledger section stays
legal). Scope notes, never silent: (a) item ORDER inside gated sections is
authored presentation (the registry seeds lead with the §27/YAML rows · the
SET + field content are the generated truth); (b) a top-level section
outside the 21 known keys makes emission REFUSE (SSOT-1 §29 · closes the
doc-vs-code gap where an unlisted uncounted section could pass silently);
(c) CF-12 above carries the 2 seed-presented codes.
