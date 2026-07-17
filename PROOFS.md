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
