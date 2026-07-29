# Mega prompt · the next session

Copy everything below the line into a fresh session.

---

Tu reprends l'arc Nika. L'arc des deux jours (41 commits · le fail-open publié
fermé · le corpus refondu) a ATTERRI le 29 après-midi, à travers deux crashes
machine : tout est poussé, rien ne t'attend dans un arbre sale. Trois documents
portent l'histoire, la carte porte l'état :

```
spec/repo/SSOT.md                                  la carte · où vit chaque fait ·
                                                   §9 dit ce qui est GATED vs discipline
engine/repo/docs/plans/2026-07-29-ARC-RECORD.md    SHIPPED vs RECORDED · l'honnêteté
engine/repo/docs/plans/2026-07-28-verdict-coverage.md   1055 lignes · chaque repro
engine/repo/docs/plans/2026-07-29-HANDOFF.md       le détail du handoff d'origine
```

**Ce qui est réglé — ne le refais pas** (vérifiable `git log origin/main` des
deux dépôts) : les leçons 08→12 existent et leurs claims ont été RUN (la carte
declassify 2×2 · le refus `--var region=us` · la ligne `⊘ rollback`) · le
learning path couvre 16/16 constructs · le pack vendoré suit spec `0c25d57` ·
`nika examples teaches` imprime les trous depuis le binaire · **le cliquet
tient les deux axes en batterie lib** (`every_construct_has_a_showcase` +
`every_builtin_is_shown_or_carries_a_named_debt` · les 4 orphelins portent
leur dette écrite dans `OWED`) · la lane pricing est commitée (les 10/11
limites fausses du hover sont mortes) · les verdicts COST/FLOOR/hints disent
ce qu'ils couvrent · site 1056/1056 sur les slugs plats.

---

## §0 · AVANT LE PREMIER GESTE — toujours vrai

```bash
export NIKA_BIN=/Users/thibaut/supernovae/ventures/nika/02-engineering/repos/engine/repo/target/debug/nika-cli
export CARGO_TARGET_DIR=/tmp/nika-isolated     # rust-analyzer partage target/ · courses sinon
```

Le `nika` du PATH est **la release publiée, qui porte encore le fail-open**
que l'arc a fermé (le fix attend le prochain train). Le build debug de
l'arbre dit un numéro PLUS BAS et c'est le BON — un build debug suit le
dernier tag, pas l'arbre. Sans ces deux exports tu répares avec l'oracle
vulnérable et tes builds se font manger par l'éditeur. Prouvé, mesuré, payé
trois fois.

## §1 · LES DEUX LOIS · elles gouvernent tout le reste

Dans `crates/nika-check/src/lib.rs` (doc de module) et `AGENTS.md`.

**Loi 1 · Couvre ce que tu affirmes, ou rétrécis ton affirmation à ce que tu
couvres.** **Loi 2 · Une question indécidable en contient presque toujours une
décidable** — quand une obligation de preuve est levée comme indécidable,
NOMME la procédure qu'il aurait fallu ; si tu peux l'écrire, la dispense est
un trou.

---

## §2 · LE TRAVAIL, dans l'ordre

```
1  SEC-009 · le message nomme son disjoint et son témoin    ← DÉCIDÉ, pas construit
   (ne RÉTRÉCIS PAS le portail · §DECIDED du carnet · NEP-0002:59 la jambe ③
    est satisfaite par le premier disjoint, pas le témoin accusé)
2  runtime/agent/001 · le contrat contredit le moteur
3  le re-sync du miroir nika-agents (SKILL.md:176 cite une phrase morte)
4  câbler warp · kimi · openclaude (`nika wire`)
5  la COURBE DE RENDEMENT ⭐ · run 2 sur un domaine NEUF
   (adversarial-audit-protocol.md · refaire le même domaine mesure la
    décroissance, un neuf mesure l'étendue — deux questions, pas une)
6  une 2e vitrine pour on_finally et le prédicat failure (SSOT §10)
7  payer les dettes OWED du cliquet · decide d'abord (il coûte de l'argent
    à chaque workflow généré) · rayer de OWED dans le même arc
```

## §3 · TROUVAILLES MOTEUR OUVERTES · mesurées, non fermées

- **Le plafond de composition est contourné** — un enfant refusé sous
  `--max-cost-usd` tourne appelé par un parent, et check+explain du parent
  disent `$0` pour un enfant qui explique seul `≤$0.0011`. Le rung
  COMPOSITION prouve déjà le graphe statique/acyclique · une passe
  topologique suffit.
- **`NIKA-DRIFT-001` conseille de supprimer des entrées `fs.read` que le
  runtime exige** (`nika:glob` gardé sur son répertoire · `multipart:`) —
  suivre le hint tue un fichier vivant. Miroir de check-vert-run-mort, dans
  un hint que les gens suivent.
- **`nika:jq` `scan` diverge en silence** — `[.s | scan("\\S+")]` sur
  `"one two three"` rend `["one"]`. Vert partout, chiffre faux.

## §4 · ÉCRIT MAIS PAS CONSTRUIT — ne le confonds pas avec du fait

`2026-07-28-resource-algebra.md` (1535 lignes · 42 théorèmes · 17 réfutations
en tête) · l'ordonnanceur dataflow (~2× · optimal sous P∞) · la concurrence
par fournisseur (PRÉREQUIS mesuré : fan-out 16 plat = 12/16 morts en rate
limit · étagé = 16/16) · l'arena reproductible. **Zéro ligne de Rust derrière
tout ceci.** C'est le chantier de fond demandé en premier ; la règle pour
qu'il démarre : pendant ce chantier une trouvaille sécurité se CONSIGNE, elle
n'interrompt pas — sauf fail-open publié.

## §5 · MÉTHODE — elle a produit les résultats

Mesurer avant d'affirmer · envoyer la passe adversariale AVANT que le
correctif semble fini · une sonde doit être MONTRÉE discriminante · réparer à
la source (le pack est un MIROIR · `spec/examples/` est l'endroit) · consigner
aussi les réfutations. Jamais piper une commande gatée · jamais `git add -A` ·
le rail pre-push juge fn-length (>100) et file-loc (>1500) sur TOUT le diff
poussé — les murs des commits sœurs t'appartiennent.

Commits · sujet tout en minuscules · `type(scope): description` · séparateur
`·` jamais de tiret cadratin · trailer
`Co-Authored-By: Nika 🦋 <nika@supernovae.studio>` — jamais Claude. Le rail
prend 5 à 8 minutes : background + log, jamais un timeout au premier plan.

## §6 · GESTES OPÉRATEUR (ne les exécute pas · signale-les)

Gel W-STD-5 (produire l'ÉTAT des critères · l'op tranche · jamais de date) ·
SSOT §11 lessons/templates (3 options · « a decision, not a reflex ») ·
F-P8 substrat · prune des worktrees mergés (wt-fp6 · wt-fp27 · wt-lot3 ·
wt-r3 + 2 /tmp) · re-shoot média (session dédiée) · Skill Hub PR gitlawb ·
docs/repo ahead 4 parqué (dette rail migration 0.107).

## §7 · TRAVAILLE EN AUTONOMIE

Lance des swarms, commite au fil, vérifie chaque affirmation toi-même avant
de la relayer. Les agents se trompent — cet arc les a vus corriger la session
cinq fois ET se tromper trois fois. Les deux arrivent.
