# PROOFS · C0 sandbox · Structured-SSOT kernel (estate · zéro mutation repo)

> Sandbox construit le 2026-07-17 dans l'estate (`post-lot10-preparation/c0-sandbox/`).
> Zéro mutation du repo spec · zéro mutation du monorepo · zéro commit git. Quand C0
> s'ouvre (checklist 16/16), le T0/T+24h = COPIE de cet arbre + re-validation, pas une
> construction. Contrats consommés AS-IS : `schemas/law.schema.json` +
> `schemas/registries.schema.json` copiés BYTE-IDENTICAL du design pack (shasum pairs
> égaux · digests §P0) · `machine/registries-inventory.json` (les 13 composants · les
> chemins canon/*) · `machine/digest-dag.json` (lock layer 1 · digest propre DÉTACHÉ).

## P0 · Inputs scellés (consommés as-is · jamais ré-inventés)

```
schemas/law.schema.json          sha256 f2e69a48da63999135a491725b459c8fb63a4c70703dd09eb29346a73cefbd66
schemas/registries.schema.json   sha256 27fdfec1dc4fc3e543098c7b7a68d62b85e9bb046ddd87326166b6c4848d763f
(les deux = byte-identical aux fichiers du design pack · vérifié shasum au moment de la copie)
```

Loi consommée : `RULINGS_2026-07-15.md` §R11 (16 points verbatim) + SSOT-1 (§1-§33) +
SSOT-2 (§A/§B/§C). Receipts P-B : `mini-gates/f1..f5-*-receipt.json` (champ
`migration_row`) + `ANNEX_2026-07-17_minigates-winners.md` (N2-a · N2-b · D-2026-07-17-N2).
Draft consommé comme point de départ : `quickwins/proposed/C0_PILOT_R11_yaml-profile-laws.PROPOSED.json`.

## P1 · Compiler ×2 → sorties byte-identiques + digests

Commandes (jouées telles quelles · sorties dans `proofs/run1.out` / `run2.out` / `check.out`) :

```
python3 scripts/ssot-compiler.py            # run 1 · write · rc=0
python3 scripts/ssot-compiler.py            # run 2 · write · rc=0
cmp proofs/laws-index.run1.json projections/laws-index.json   → byte-identical
cmp proofs/ssot.lock.run1 canon/ssot.lock                     → byte-identical
cmp proofs/ssot.lock.sha256.run1 canon/ssot.lock.sha256       → byte-identical
python3 scripts/ssot-compiler.py --check    # rc=0 · « check OK · byte-identical ×3 outputs »
```

Digests émis (imprimés par le compiler · SSOT-1 §21-22 satisfaits) :

```
projection projections/laws-index.json  sha256:ea382f4b2b5201bf7c9f56c20e2a0b506bc6de10313bb1625762d00b09d07419
lock       canon/ssot.lock              sha256:3fa1639ce7dafa9f20ee07ee0b974d099609dc91624994b2e21077b229573f6d
           (digest propre DÉTACHÉ dans canon/ssot.lock.sha256 · PAA-006 · digest-dag layer 1 :
            le lock ne référence que des feuilles · la projection ne porte AUCUN digest de feuille)
```

Déterminisme : tri de fichiers stable · JSON canonique (sorted keys · séparateurs
minimaux) · NFC · LF · zéro timestamp · zéro chemin absolu · zéro réseau.

## P2 · MUTATION KILLS (le compiler refuse · rc ≠ 0 · diagnostic précis)

Chaque kill tourne sur une COPIE (`--root proofs/mutation-kill/kN-root`) · le sandbox
reste vert · sorties complètes dans `proofs/mutation-kill/kN.out` :

| Kill | Mutation | rc | Diagnostic (extrait) |
|---|---|---|---|
| K1 | champ requis `judgment` retiré de LAW-GRAMMAR-0103 (`broken-law.yaml`) | **2** | `entry[2] (LAW-GRAMMAR-0103) · at / · 'judgment' is a required property` |
| K2 | anchor `&own` + alias `*own` injectés dans canon/types.yaml | **3** | `YAML anchor (&own) at line 20, column 15 · R11 points 1+3: forbidden even when never referenced` |
| K3 | la forme du DRAFT rejouée : id LAW-YAML-0001 + domain YAML | **2** | `'YAML' is not one of ['SURFACE', 'GRAMMAR', ...]` + refus du pattern id |
| K4 | édition manuelle d'une projection émise puis `--check` | **1** | `DRIFT · projections/laws-index.json: bytes differ from regeneration` · restore → rc=0 |

K2 est le dogfood R11 : le loader du compiler refuse anchors · aliases · merge keys ·
duplicate keys · custom tags · non-string keys · NaN/Infinity dans NOS PROPRES sources
canon (le profil que le pilote importe s'applique d'abord à la SSOT elle-même).
K3 prouve MACHINE le finding central contre le draft (F-01/F-02).

## P3 · Le pilote valide 18/18 entrées · 16/16 points R11 couverts

`canon/laws/yaml-profile.yaml` : 18 law entries · chacune valide contre le schema
scellé (le run vert le prouve : toute entrée invalide = rc 2 par construction · K1/K3
prouvent la contraposée). Couverture point-par-point (chaque loi CITE le texte exact
entre « » avec l'ancre « R11 point N ») :

| R11 point | Où il vit (loi porteuse · les citations verbatim sont dans prose_projection/proof_obligations) |
|---|---|
| préambule + 1 | LAW-GRAMMAR-0101 (anchor) · 0102 (alias) · 0103 (merge key) |
| 2 | plié : implementation_surfaces engine+reference sur CHAQUE loi + proof_obligation verbatim (0101) |
| 3 | LAW-GRAMMAR-0101 (premise = présence seule · fixture anchor-unused) |
| 4 | LAW-DIAG-0101 (teaching_required · verbatim) |
| 5 | LAW-DIAG-0102 (namespace_scope · 4 codes mandatés) + LAW-GRAMMAR-0104 |
| 6 | plié : proof_obligations 0101 + 0102 (verbatim) |
| 7 | plié : verdict refuse toutes surfaces + proof_obligations 0101 (verbatim) + LAW-CONF-0101 |
| 8 | LAW-HASH-0101 (premise conforms_to · verbatim) |
| 9 | LAW-HASH-0101 (premise absent(anchor_expansion_ir_nodes) · verbatim) |
| 10 | LAW-CONF-0101 (engine_reference_parity · verbatim · gap sdk → F-03) |
| 11 | LAW-CONF-0102 (polarity_declared · la probe réelle est classée negative au registre) |
| 12 | LAW-CONF-0103 (intersect_empty · census courant-facing · verbatim) |
| 13 | LAW-GRAMMAR-0104..0111 (8 branches : dup keys · custom tags · non-string keys · NaN/Inf · profondeur · taille doc · taille scalar · NFC/BOM) |
| 14 | plié : closure_gates no-engine-choice-residual + caps-declared-in-grammar-registry (verbatim dans proof_obligations 0104/0105/0106/0108) |
| 15 | plié : proof_obligations 0102 + 0103 (verbatim) |
| 16 | LAW-SURFACE-0101 (one_spelling_per_meaning · verbatim) |

Squelettes : 12 composants registres · 35 rows total (`registry_row_counts` du lock) ·
tous valident contre registries.schema.json. Seed migrations : 7 rows réelles
(5 receipts P-B verbatim + N2-a + N2-b · state ratified · D-2026-07-17-N2).

## P4 · FINDINGS (SSOT-1 §29 · explicites · jamais de correction silencieuse)

- **F-01 · domaine YAML impossible sous le schema scellé.** Le brief + le draft
  demandent des ids `LAW-YAML-NNNN` (`domain: YAML`). Le schema scellé ferme le DOMAIN
  enum à 15 (pas de YAML) et `01_STRUCTURED_LAW_SCHEMA.md` §1 grave : « The DOMAIN enum
  is CLOSED (15). Adding a domain = a MIGR law + registry amendment. » Résolution
  EXPLICITE (pas silencieuse) : le pilote mappe sur les domaines existants, bloc 01xx +
  slugs `yaml/*` (table de correspondance en tête du fichier lois). Un domaine YAML
  dédié = amendement du pack scellé, geste GATED opérateur. K3 prouve le refus machine.
- **F-02 · la claim de conformité du draft est FAUSSE (mesurée).** Le draft affirme
  « Conforme au schema SCELLÉ schemas/law.schema.json @ a075125bd (18 champs requis ·
  consommé as-is, jamais ré-inventé) ». Mesure (`proofs/draft-measurement.out`) : **0/5 entrées valident**.
  Axes refusés : domain YAML (enum) · id LAW-YAML (pattern) · opérateurs `not_contains`
  / `all_distinct` / `leq` (hors enum fermé des conditions) · `domain_payload.kind:
  yaml_profile` (hors oneOf des 15 payloads) · champs `$note` (additionalProperties
  false) · `implementation_surfaces` sans préfixe (`nika-schema` · `reference/runner.py`)
  · `closure_gates` en texte libre avec espaces (pattern kebab).
- **F-03 · R11 point 10 exige la parité SDK · le schema scellé n'a pas de préfixe
  `sdk:`.** Le pattern `implementation_surfaces` admet engine|reference|cli|lsp|mcp|
  conformance seulement. La parité SDK est portée par la projection `sdk` + les
  proof_obligations de LAW-CONF-0101. Trou de surface à ruler à C0 (amendement pack ou
  doctrine « sdk = consommateur de la projection, pas une surface d'implémentation »).
- **F-04 · R11 point 13 mandate des caps SANS valeurs.** Profondeur · taille document ·
  taille scalar · NFC/BOM : le ruling exige la COUVERTURE normative, il ne fixe ni
  nombre ni disposition (refuser un BOM ou le strip · exiger NFC ou normaliser). La
  note P5 dit seulement que 200k passait (l'empirie du gap, pas le cap). Les rows
  grammar portent le TO-RULE explicitement · AUCUN nombre inventé.
- **F-05 · codes 006..011 = c0-proposed.** R11 point 5 mandate exactement 4 codes
  (anchor · alias · merge key · duplicate key). NIKA-YAML-005 (scalar cap) est hérité
  du draft (gap P5). Les branches restantes du point 13 exigent des diagnostics
  canoniques (SSOT-2 B.21) : NIKA-YAML-006..011 mintés `status: reserved` + marqués
  c0-proposed · renumérotables avant C1, jamais après mint.
- **F-06 · zéro fixture yaml-profile au repo spec (mesuré).** `find` sur
  conformance/ : 0 hit anchor/alias/merge/yaml-profile. Convention : chemins
  `to-mint-c1/...` (la forme majuscule `TO-MINT-C1` violerait le pattern fixturePath
  scellé). Seule fixture RÉELLE : `research/pre1-gate/probes/anchors.nika.yaml`
  (monorepo · `&shared` + `*shared`) · enregistrée au registre conformance
  (polarity negative · row `yaml-profile-anchors-probe`) et snippets.
- **F-07 · normalisation machine des receipts (documentée row par row).** migrationRow
  exige des machineIds lowercase : `F4-b17-temporal` → `f4-b17-temporal` · consumers
  prose → slugs machine · le VERBATIM intégral vit dans `notes` (byte-à-byte). Ruling
  mappé : familles F1/F2/F3/F5 + N2-a/N2-b → R8 (protocole mini-gates) · F4 → B-17.
- **F-08 · convention de nommage des fichiers lois.** `01_STRUCTURED_LAW_SCHEMA.md` §2
  écrit `canon/laws/<domain>.yaml` · le plan 72h T+24h nomme des fichiers par RULING
  (yaml-profile · auth · temporal...). Le sandbox suit le brief + le plan 72h
  (`yaml-profile.yaml`) · le compiler globe `*.yaml`, les deux conventions compilent.
- **F-09 · PyYAML déclaré.** La règle sandbox disait stdlib+jsonschema uniquement · les
  inputs mandatés sont YAML. PyYAML (déjà le parser du reference model spec ·
  `reference/semantics.py`) est utilisé pour le PARSING D'ENTRÉE seulement, enveloppé
  dans le loader R11-enforçant (le gate dogfood · K2). Tout le reste = stdlib.
- **F-10 · « structure vide » impossible.** registries.schema.json impose minItems 1
  sur chaque tableau : chaque squelette porte exactement 1+ row (seed réelle quand
  honnête · placeholder reserved sinon · le digest tout-zéro du templates placeholder
  est MARQUÉ, jamais revendiqué). Le schema scellé force aussi `status: retired` sur
  toute row tombstone (constaté au premier run · la row porte `retired_in: C1`).
- **F-11 · subject mono-ref des payloads DIAG.** `diagnosticPayload.subject` est UN
  typedRef · les lois des points 4/5 gouvernent une famille de 4 codes : subject
  épingle l'exemplaire NIKA-YAML-001, `inputs` porte la famille complète (encodage
  schema-légal · documenté dans les proof_obligations).

## P5 · Ce que C0 copie (le geste T0/T+24h)

```
canon/            → repo spec canon/ (13 composants · rows deferred → present)
scripts/ssot-compiler.py → repo spec scripts/ (v0 · le contrat 01 §6 complet ajoute
                    --coverage + les projections prose/canon.yaml compat à C0)
schemas/*         → NE PAS copier (le pack les possède · le spec les référence au pin)
proofs/           → rejouer les 4 kills + le ×2 byte-identical au premier commit C0
```

Re-validation à la copie : `python3 scripts/ssot-compiler.py --check` rc=0 · les 4
kills rc 2/3/2/1 · les digests changent (chemins/pins C0) et se re-scellent au receipt.

---

## §canon-flip · 2026-07-17 · l'import canon.yaml → registres + le gate --check-canon (compiler v0.2)

> DoD C0 items 4-5 amorcés (MIG-canon-yaml · « jamais deux vérités ») · plan
> `CANON_FLIP_WAVE_PLAN.md`. Le CONTENU de canon.yaml entre dans les registres
> scellés (verbatim · SSOT-1 §28) · les sections sans foyer adapté entrent au
> ledger d'exceptions (`canon/EXCEPTIONS.md` · §18) · le compiler v0.2 gagne le
> mode `--check-canon` (parité registre↔canon.yaml · **rc=5** nouveau code
> documenté · read-only · zéro réseau · déterministe). Le flip réel (canon.yaml
> GÉNÉRÉ + `--emit-canon` + test des 70+ lecteurs monorepo) reste l'étape
> suivante du plan — HORS de cette vague.
>
> → **FAIT** · la vague suivante a exécuté le flip · voir `§canon-generated`
> ci-dessous (`--emit-canon` · header GENERATED · byte-gate rc=5 · lecteurs verts).

### CF-P1 · L'import (9 surfaces gatées · sources verbatim)

```
verbs (4) + namespaces (5)      → canon/surface.yaml        rows kind=verb/namespace · status active ·
                                  law-anchored (LAW-SURFACE-0212 · LAW-SURFACE-0201/0221/0222 ·
                                  LAW-GRAMMAR-0201/0202) · semantics canon.yaml en notes verbatim
builtins (28)                   → canon/builtins.yaml       id nika:<name> · category/capability/error_plane
                                  per stdlib/builtins-v0.1.md · 11 external · 17 pure_internal ·
                                  LAW-AUTH-0311 sur chaque row (+ LAW-TEMPORAL-0411 sur nika:wait)
templates (10)                  → canon/templates/registry.yaml  digest sha256 RÉEL de chaque source
                                  (vérifiée sur disque · le placeholder digest-zéro remplacé per sa
                                  propre déclaration)
error_codes (83)                → canon/diagnostics/registry.yaml  id+namespace per spec/05-errors.md
                                  (cross-check canon↔05 = 83/83 identiques · mesuré) · champs fins =
                                  floors honnêtes déclarés note import-c0 · 15 codes câblés aux lois qui
                                  les citent · les 2 seeds NIKA-AGENT byte-intouchées · 94 rows total
                                  (+ NIKA-SEC-009 · import-c2 NEP-0002 · reserved, law_ids [] en
                                  attendant la famille de lois SEC)
                                  (+ NIKA-DRIFT-001 · import-c2 nika#661 · reserved, law_ids [] en
                                  attendant la famille de lois DRIFT · terminal:false — le premier
                                  row non-terminal : hint advisory, jamais un échec du workflow)
mcp.protocol_versions (5)       → canon/features.yaml       runtime_capability · id bijectif
                                  mcp.protocol.<v · tirets→underscores> · detection_law LAW-CONF-0510
error_namespaces (22 · partiel) → dérivés des rows (20/22 · IMPL+PROVIDER declared-empty · CF-09)
outcome_transitions.classes     → COHÉRENT (canon == enum scellé outcome_class == lois gates R5 ·
                                  terminal jamais une classe per LAW-OUTCOME-0231)
```

### CF-P2 · Le ledger d'exceptions (SSOT-1 §18 · rien de silencieux)

`canon/EXCEPTIONS.md` · 16 rows (counts=dérivés par le gate · providers +
extract_modes = home ruling owed · error_categories = pas de champ category
dans le diagnosticRow scellé · outcome_transitions.legal/payload = table-13
home owed · 7 vocabulaires studio = authored per operator reco · mcp.tools =
projection engine-verified · canonical_phrasing = home snippets owed ·
schema_version = meurt au flip) + le registre des findings CF-01..CF-11. La
liste de skips du compiler (`CANON_EXCEPTIONS`) et le ledger sont en lockstep.

### CF-P3 · Les preuves (proofs/canon-flip/ · rejouées telles quelles)

```
(a) check-canon-green.out          python3 scripts/ssot-compiler.py --check-canon → rc=0
                                   « check-canon OK · one truth · 9 gated surfaces · 16 declared skips »
(b) mutation-remove-nika-hash.out  la row nika:hash RETIRÉE de canon/builtins.yaml → rc=5 ·
                                   diagnostic exact : « builtins: canon items with NO registry row: nika:hash »
    restore-green.out              copy-back byte-exact → rc=0 (cmp = identique)
(b-bis) mutation-canon-side.out    5e verbe fantôme (ghostverb) injecté dans canon.yaml → rc=5 ·
                                   « verbs: canon items with NO registry row: ghostverb » · le gate tue
                                   la seconde vérité DANS LES DEUX SENS · restore byte-exact → rc=0
(c) check-run1.out / check-run2.out  --check ×2 → rc=0 · sorties byte-identiques (cmp) ·
                                   projection sha256:34a9ca4e… · lock sha256:db0cae16… (v0.2 re-scellés)
(d) kill-broken-law.out            broken-law.yaml (asset K1 · judgment retiré) REMPLACE yaml-profile.yaml
                                   dans une copie racine post-import → rc=2 ·
                                   « 'judgment' is a required property » · le refus schema survit à v0.2
```

### CF-P4 · FINDINGS (SSOT-1 §29 · registre complet dans canon/EXCEPTIONS.md)

CF-01 vars/env · dual-truth timeline (v1 live vs R3a E-split) déclaré aux rows ·
CF-02 duplicate nika:jq pré-import mergé (citation LAW-TEMPORAL-0411 erronée sur
jq droppée · 0411 réfère builtins:nika:wait) · CF-03 error_plane seeds
(NIKA-JQ/NIKA-NIKAWAIT) contredisaient le stdlib · corrigés déclarés · CF-04
table catégories stdlib somme 27 vs total 28 (decide sans row · enum scellé
`decision`) · CF-05 11 rows NIKA-YAML registry-ahead (namespace YAML absent des
21) · CF-06 transient engine-assessed × 3 inreprésentable dans le boolean scellé
(floor false déclaré) · CF-07/08 causes kernel-ahead (budget_exhausted ·
deadline_exceeded · lois OUTCOME-0403/0402 vs table legal canon) · CF-09
IMPL/PROVIDER zéro code (underivable) · CF-10 error_categories sans foyer scellé
(carried en notes greppables `category: <c>`) · CF-11 la table §namespaces de
spec/05 liste 15 alors que sa propre table de codes en use 21 (prose lag).

## §canon-generated · 2026-07-17 · LE FLIP · canon.yaml devient une projection générée (SSOT-1 §21-23)

> DoD C0 · la dernière vague MIG-canon-yaml. Le compiler gagne `--emit-canon`
> (mode write du flip) · canon.yaml gagne son header GENERATED · `--check-canon`
> gagne le byte-gate (header présent + fichier == sa propre régénération ·
> **rc=5** sur toute édition manuelle d'une surface générée) · le gate SSOT
> entre en CI (conformance.yml · « toute édition manuelle d'une projection
> générée rend la CI rouge » · §23 devient effectif, pas déclaratif).

### CG-P0 · Le dry-run du flip · diff NUL au premier emit

```
sha256(canon.yaml authored · pré-flip)   a566985e828a0ae531533fc6aed168f19ff3f1f09b891ecc63e848efd1d5d0a1
sha256(body émis depuis les registres)   a566985e828a0ae531533fc6aed168f19ff3f1f09b891ecc63e848efd1d5d0a1
```

Le body régénéré == le canon.yaml authored **byte-à-byte** (diff vide · zéro
finding de contenu). La preuve vit dans le header lui-même : la ligne
`# body-sha256:` du canon.yaml flippé porte exactement le sha du fichier
authored pré-flip. Ce que `--emit-canon` dérive des registres · counts par
`len(items)` · verbs/namespaces (spellings surface + sémantiques « … » verbatim
des notes) · builtins/templates (row ids) · error_codes (condition == failure ·
greppables `category:`/`transient:` des notes import-c0) · mcp.protocol_versions
(transform bijectif · latest = max) · outcome classes (enum scellé). Ce qu'il
porte verbatim · les 16 sections ledger + chaque commentaire prose + la SÉQUENCE
des items (présentation authored · les 2 codes seed-carried per CF-12).

### CG-P1 · Déterminisme ×2 + idempotence (emit-run1.out / emit-run2.out)

```
python3 scripts/ssot-compiler.py --emit-canon   ×2 (le 2e SUR le fichier flippé)
→ sha256:2f804d154b7c773a8390ff708724cd4eb60129b8a126090cc49d62590d12b3e8 les deux fois
→ cmp = byte-identique (même commit ⇒ mêmes bytes · §22) · emit(emit(F)) == emit(F)
```

### CG-P2 · La batterie de mutations (mutation-battery.out · rc capturés SANS pipe)

```
M1  item généré édité   (builtins assert→asserts)      → rc=5 (+ le gate de parité nomme nika:asserts)
M2  count généré édité  (counts.builtins 28→29)         → rc=5 (+ « 29 != len 28 » intra-canon)
M3  failure généré édité (NIKA-SEC-001 hit→HIT)         → rc=5 (byte-gate seul · le champ vient de la row)
M4  header GENERATED retiré (lignes 1-12)               → rc=5 (« header missing » + bytes differ)
M5  CONTRE-PREUVE · section AUTHORED éditée (pillars)
    + ré-émission                                       → rc=0 (les 16 sections ledger restent libres · §18)
restore byte-exact après chaque mutation                → rc=0
```

### CG-P3 · Le test des lecteurs (readers-test.out · INCHANGÉS · verts sur le canon régénéré)

```
IN-REPO (la suite CI complète · jouée dans l'arbre flippé) · 15/15 rc=0
  conformance/runner.py all (les listes stdlib dérivent de canon.yaml) · 7 selftests
  (type/decision/gateway/outcome/composition/proof/projection) · gen-type-corpus --check ·
  6 projectors --check (canon/showcase/llms/starters/authoring/design)
MONOREPO (REPO_ROOT=shadow-root · spec/repo → l'arbre flippé · le reste → le monorepo réel)
  canon-spec-counts-derive.sh --check → rc=0 (baseline réel rc=0 · sortie byte-identique)
  canon-fix.sh --check               → rc=0 · 24 target(s) all markers match (== baseline 24)
Census · 47 fichiers sous plumbing/scripts + dx référencent le canon spec · les 2
exécuteurs nommés du DoD tournent verts · le header (commentaires YAML + parse yaml/grep
counts) est invisible pour chaque classe de lecteur.
```

### CG-P4 · FINDINGS de la vague (registre complet dans canon/EXCEPTIONS.md)

CF-12 · les 2 seeds §27 (NIKA-AGENT-001/002 · byte-intouchées à l'import) ne
portent pas les champs projection v0.1 → leurs 2 lignes canon restent authored
(template-carried · `SEED_CARRIED_CODES`) · l'appartenance reste gatée (subset).
CF-13 · `schema_version` SURVIT au flip (le « meurt au flip » pré-datait le
census lecteurs · canon-projectors.py exit 2 + gates monorepo le lisent) · la
retraite ride la cascade projector C1. Scope déclaré (jamais silencieux) ·
l'ORDRE des items d'une surface gatée = présentation authored (le SET + le
contenu des champs = la vérité générée) · une section top-level hors des 21
clés connues fait REFUSER l'émission (§29 · ferme le trou doc-vs-code du
--check-canon v0.2 sur les sections non comptées).
