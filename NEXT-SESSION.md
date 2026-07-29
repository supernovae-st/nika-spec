# Mega prompt · the next session

Copy everything below the line into a fresh session.

---

Tu reprends l'arc Nika. Deux jours de travail ont produit 41 commits, un
fail-open **publié** fermé, un corpus refondu, et deux lois qui vivent
maintenant dans le code. Trois documents portent tout :

```
spec/repo/SSOT.md                                  la carte · où vit chaque fait
engine/repo/docs/plans/2026-07-29-ARC-RECORD.md    ce qui a été fait, et ce qui
                                                   est écrit mais PAS construit
engine/repo/docs/plans/2026-07-28-verdict-coverage.md   1055 lignes · chaque repro
```

**Lis les trois avant de toucher quoi que ce soit.** Tout ce qui suit y renvoie.

---

## §0 · AVANT LE PREMIER GESTE

```bash
export NIKA_BIN=/Users/thibaut/supernovae/ventures/nika/02-engineering/repos/engine/repo/target/debug/nika-cli
```

Le `nika` du PATH est **0.106.1 et porte le fail-open que cet arc a fermé**. Le
build de l'arbre dit `0.106.0` et c'est le BON — un build debug suit le dernier
tag, pas l'arbre, donc **le numéro le plus haut est le vulnérable**. Le hook
d'édition juge tout seul après chaque écriture ; sans l'export il te rend un vert
de la release que tu répares. C'est arrivé à trois agents simultanément.

---

## §1 · LES DEUX LOIS · elles gouvernent tout le reste

Elles sont dans `crates/nika-check/src/lib.rs` (doc de module) et `AGENTS.md`
(règles dures). Chaque tâche ci-dessous en est une application.

**Loi 1 · Couvre ce que tu affirmes, ou rétrécis ton affirmation à ce que tu
couvres.** Un vert qui vaut moins que ce qu'il dit dépense la confiance du
lecteur et ne rend rien. Quand tu ne peux pas élargir la couverture, rétrécis la
phrase et NOMME ce qui défère.

**Loi 2 · Une question indécidable en contient presque toujours une décidable.**

> Quand une obligation de preuve est levée comme indécidable, NOMME la procédure
> de décision qu'il aurait fallu. Si tu peux l'écrire, la dispense est un trou.

Quatre instances, trois rungs, trois auteurs — dont une cachait un fail-open
publié. La question qui les trouve n'est pas « sois prudent », c'est :
**quelle est l'affirmation la plus forte que je PEUX décider ici, et le code
la fait-il ?**

---

## §2 · TÂCHE 0 · L'ARBRE PARTAGÉ · à lire AVANT le premier `cargo`

**rust-analyzer tourne en continu sur le MÊME `target/`.** Diagnostiqué à la fin
de la session, après deux échecs de build qui ressemblaient à tout sauf à ça :

```
cargo test -p nika-check   →  jiff-0.2.35 · associated type `Primitive` not found
cargo build -p nika-cli    →  extern location for rustc_demangle does not exist
                              .../target/debug/deps/librustc_demangle-*.rmeta
```

Deux erreurs différentes, dans deux dépendances tierces, sur du code qui rendait
538/539 verts une heure plus tôt. La source cachée de `jiff` est INTACTE (377
lignes, module déclaré, fin propre) — ni corruption, ni features, ni mon code.

La cause, trouvée par `pgrep` :

```
PID 22630  cargo check --workspace --message-format=json --keep-going --all-targets
```

C'est le check de fond de l'éditeur. Il **supprime et réécrit des artefacts
pendant que ton build les lit**. Le symptôme change à chaque fois selon quel
`.rmeta` disparaît, ce qui le rend très facile à attribuer au mauvais coupable —
j'ai perdu trois tours à soupçonner une corruption de registre, puis une
résolution de features.

**Le remède, à utiliser systématiquement dans ce dépôt :**

```bash
export CARGO_TARGET_DIR=/tmp/nika-isolated     # un arbre à toi
```

Le premier build est complet, ensuite c'est incrémental et **plus jamais de
course**. **L'hypothèse est PROUVÉE**, mesurée en fin de session :

```
target/ partagé      cargo build -p nika-cli   rc=101 · rustc_demangle .rmeta absent
/tmp/nika-isolated   cargo check -p nika-check rc=0   · 12.15s
```

Le même code, à la même seconde. Rien à réparer dans l'arbre — il fallait
seulement cesser de le partager.

**Ce que ça explique rétrospectivement** : une grande partie de la fragilité de
cette session. Des builds qui « timeout », des tests qui passent puis échouent
sans changement, un binaire qui disparaît en plein milieu d'une mesure. Chaque
fois j'ai cherché la cause dans mon code. Elle était dans l'éditeur.

**Et une leçon de méthode**, la même que le reste de l'arc : un symptôme qui
CHANGE à chaque exécution ne vient presque jamais du code qu'on vient d'écrire.
Le premier réflexe est `pgrep -fl cargo`, pas la relecture du diff.

---

## §3 · TÂCHE 1 · COMMITER LE STAGED

Deux fichiers, verts à leur dernière compilation, jamais commités (une
interruption) :

```
crates/nika-check/src/permits_fit.rs
docs/plans/2026-07-28-verdict-coverage.md
```

Le message est prêt au **§6 de `docs/plans/2026-07-29-HANDOFF.md`** — rejoue-le
verbatim. Re-vérifie d'abord (539 tests · `clippy -- -D warnings`).

Ce qu'il porte : F16 (le conjoint d'autorité d'outil tombait avec l'argument
dynamique) et F13 (un `net.http` vide est un test de vacuité d'ensemble, donc
décidable). Les deux ont été réparés PAR la loi 2, écrite une heure plus tôt.

---

## §4 · TÂCHE 2 · TRIER LES 26 FICHIERS NON COMMITÉS

Du travail de swarms concurrents a atterri dans l'arbre sans être commité.
**Vérifie chacun, ne suppose aucun vert.**

```
crates/nika-catalog-codegen/*  ·  crates/nika-catalog/*   la lane catalogue
crates/nika-cli/src/verbs/check/*                          la lane couvertures
workflows/catalog/*                                        workflows de mesure
README.md · scripts/                                       non attribué · lis le diff
```

La lane couvertures est bonne et visible : `PERMITS literal + const: args fit
the boundary · computed + symlinks at run`, `TOOLS every named nika: tool is
canonical · globs + mcp: not checked`. C'est la loi 1 appliquée à tous les rungs.

La lane catalogue porte des trouvailles non fermées, dont une user-visible :
**10 des 11 limites de tokens écrites à la main dans `llm-providers.toml` sont
FAUSSES**, et `nika-lsp/hover.rs` les rend — le survol VS Code enseigne
aujourd'hui un plafond haiku 8× trop bas.

Garde ou jette, mais laisse l'arbre net.

---

## §5 · TÂCHE 3 ⭐ · LA PLUS IMPORTANTE · MONTRER LES 4 CONSTRUCTIONS ABSENTES

**C'est le travail qui a le plus d'effet sur ce que les agents produiront.**

Mesuré sur les 43 fichiers du corpus. Quatre constructions du langage ont
**zéro exemple**, alors que la spec en parle longuement :

| construction | exemples | mentions spec | ce qu'un agent ne fera donc JAMAIS |
|---|---:|---:|---|
| composition (`workflow:` sous `invoke:`) | **0** | 36 | appeler un workflow depuis un autre — alors que `check` embarque un rung COMPOSITION entier pour ça |
| `returns:` (la porte typée) | **0** | 47 | typer la sortie d'une tâche |
| `declassify:` | **0** | 3 | franchir un taint — la spec l'appelle « **la SEULE porte** » |
| `config:` | **0** | 16 | une des **QUATRE** autorités de valeurs |

Et deux montrées **une seule fois**, ce qui ne suffit pas à lire un motif :
`on_finally:` et le prédicat d'arête `failure`.

### Pourquoi ça coûte plus cher que n'importe quelle réparation moteur restante

Le corpus est **la surface d'ancrage des agents**, pas de la documentation.
Mesuré : six agents écrivant depuis la compétence seule ont pris 45 tours de
check-fix, aucun vert du premier coup. Un qui a lu **deux exemples** a écrit son
suivant vert **en zéro tour**.

**Une construction sans exemple est, opérationnellement, une construction que le
langage n'a pas.**

`declassify:` est le plus tranchant : un auteur qui heurte le mur du taint n'a
**aucune porte visible**. Il élargira une frontière ou abandonnera — exactement
le réflexe que deux jours ont combattu.

### Comment

- Édite dans `spec/repo/examples/`, **jamais** dans `crates/nika-pack/pack/`
  (c'est le miroir, le prochain `sync-pack.sh` t'écrase).
- Chaque nouvel exemple : `nika check --native-strict` rc=0 **zéro hint**, puis
  **RUN-le**, puis **parse son artefact**. Un run vert qui écrit du JSON
  malformé est un échec.
- Permits les plus **serrés** qui couvrent le corps. Jamais élargis pour faire
  taire un message. Jamais de `**` à la racine.
- Chaque commentaire du fichier doit être **vrai**. Un modèle faux enseigné dans
  un exemple devient un modèle faux dans chaque workflow écrit ensuite — c'est
  arrivé deux fois cet arc (`agent-loop` et un commentaire sur `egress:`).
- Le contrat que le corpus honore : `spec/repo/examples/CONVENTIONS.md`.
- Puis `bash scripts/sync-pack.sh <spec-checkout>` depuis le moteur, et
  `cargo test -p nika-onboard --lib` doit rester à 62/62.

---

## §6 · TÂCHE 4 · LE CLIQUET DE COUVERTURE

Aucun des deux manques n'a de garde. **Le 29ᵉ builtin peut arriver sans vitrine
demain, et la prochaine construction aussi.**

Bâtis un test qui compare `ALL_BUILTINS`
(`crates/nika-catalog/src/data/builtins.rs`, 28 triés) au corpus et échoue sur
un orphelin — même forme que le portail existant du kit
(`the_kit_never_teaches_a_form_the_engine_refuses`).

Puis étends-le aux constructions. C'est plus dur : la liste n'est pas un tableau
Rust. Dérive-la de `canon.yaml`, ou tiens-la à la main dans le test **avec un
commentaire disant pourquoi chaque entrée y est**.

Base de référence à encoder : builtins 24/28 · 4 constructions à zéro ·
4 builtins orphelins (`nika:decide` · `nika:inspect` · `nika:compose` ·
`nika:tts_generate`). `nika:decide` est le plus coûteux : c'est le noyau de
décision **déterministe**, donc un agent qui ne le voit jamais paiera un appel
modèle pour un `if`.

---

## §7 · CE QUI RESTE APRÈS, dans l'ordre

```
SEC-009 · le message nomme son disjoint et son témoin   ← DÉCIDÉ, pas construit
runtime/agent/001 · le contrat contredit le moteur
le re-sync du miroir nika-agents
câbler warp · kimi · openclaude
la COURBE DE RENDEMENT ⭐                                ← répond « mur ou pas »
```

**SEC-009 · la décision est déjà prise**, avec son raisonnement au §DECIDED du
carnet. Deux agents ont heurté le portail de la trifecta létale en déclarant une
frontière honnête et ont recommandé de le rétrécir. J'ai vérifié leur sondage
puis lu `NEP-0002:59` : la jambe ③ **est** satisfaite, par le premier disjoint
(`net.http` non-vide), pas par le témoin qu'ils accusaient. **Le portail garde sa
sémantique ; son message doit nommer quel disjoint et quel témoin.**
**Ne rétrécis pas le portail** — faire tirer moins un portail de sécurité sur un
après-midi de sondage est exactement la forme de l'erreur qui a mis le fail-open
dans `literal_root`.

**La courbe de rendement** est la seule chose qui réponde à la question de
l'opérateur : *« on fait du sur place ? »*. 23 défauts en deux jours, c'est soit
une dette connue qui s'épuise (le taux baisse), soit une classe qui se régénère
(le taux tient). L'instrument existe
(`docs/plans/adversarial-audit-protocol.md`), **le run 2 n'a pas eu lieu**. Il
doit viser un domaine **NEUF** — refaire le même mesure la décroissance, un
nouveau mesure l'étendue, et ce sont deux questions qu'on ne mélange pas.

---

## §8 · TROUVAILLES MOTEUR OUVERTES · mesurées, non fermées

- **Le plafond de composition est contourné.** Un enfant refusé sous
  `--max-cost-usd` **tourne** quand il est appelé par un parent. Pire : le
  `check` ET le `explain` du parent disent tous deux `no inference tasks · $0
  model spend` pour un enfant qui explique seul `≤$0.0011`. Le rung COMPOSITION
  prouve déjà que le graphe d'appel est statique, typé, contenu et acyclique —
  donc une passe topologique suffit.
- **`NIKA-DRIFT-001` dit aux auteurs de supprimer des entrées `fs.read` que le
  runtime exige.** `nika:glob` est gardé sur le RÉPERTOIRE qu'il parcourt, et un
  `multipart:` sur son chemin ; le détecteur de dérive ne modélise ni l'un ni
  l'autre comme une lecture. Suivre le hint rend un fichier qui marchait mort au
  run. **C'est l'image miroir de la classe check-vert-run-mort**, et c'est dans
  un hint que les gens suivent.
- **`nika:jq` `scan` diverge en silence.** `[.s | scan("\\S+")]` sur
  `"one two three"` rend `["one"]`. Check vert, run vert, JSON bien formé,
  chiffre faux. `splits`, `match` global et `/` sont corrects.
- **Le cadrage FLOOR.** `nika inspect` imprime `≥ $X (floor — unbounded tasks)`
  au-dessus de `bounded_total_usd`, et le commentaire de `render.rs` établit
  lui-même que cette quantité n'est pas un plancher (mesuré $0.000242 contre un
  `≥$0.0305` annoncé). Le `≥` et le mot FLOOR sont tous deux faux.

---

## §9 · MÉTHODE · c'est elle qui a produit les résultats

Cinq fois dans cet arc, ce qui a corrigé la session n'était pas un test — c'était
**quelqu'un envoyé pour la contredire**. Adopte la posture ou le rendement
s'effondre.

```
✅ MESURER AVANT D'AFFIRMER          un agent a rendu des verdicts sur 4 fichiers
                                     qu'il n'avait jamais ouverts · 4 faux

✅ ENVOYER LA PASSE ADVERSARIALE     le swarm envoyé VALIDER un correctif a
   AVANT QUE LE CORRECTIF            trouvé que je réparais le mauvais bug · le
   SEMBLE FINI                       fail-open publié était à une fonction

✅ UNE SONDE DOIT ÊTRE MONTRÉE       le repro de F11 est refusé par les DEUX
   DISCRIMINANTE                     builds, pour des raisons OPPOSÉES · même
                                     verdict, ça se lit comme une confirmation.
                                     Mon propre scanner a rendu 7 fantômes une
                                     heure après que j'aie écrit la règle, et une
                                     sonde a compté 43 rouges alors que le
                                     binaire avait été supprimé

✅ RÉPARER À LA SOURCE                `crates/nika-pack/pack/` est le MIROIR
                                     vendoré de nika-spec

✅ CONSIGNER AUSSI LES RÉFUTATIONS   `nika run --resume` a été rapporté bloquant
                                     3× · quatre constructions ici, toutes
                                     propres · un P0 fantôme coûte une journée

❌ JAMAIS piper une commande gatée    `cargo build … | grep` a caché un timeout
❌ JAMAIS `git add -A` dans cet arbre  des lanes concurrentes sont non commitées
❌ fmt et clippy sont DEUX portails    et le clippy du rail est PLUS STRICT
                                      qu'une passe ciblée · `-- -D warnings`
```

**Commits** : sujet tout en minuscules, `type(scope): description`, jamais de
tiret cadratin (le séparateur maison est `·`), trailer
`Co-Authored-By: Nika 🦋 <nika@supernovae.studio>` — jamais Claude. Le rail
prend 5 à 8 minutes : lance-le en arrière-plan ou redirige vers un log, jamais
en timeout au premier plan.

---

## §10 · CE QUI EST ÉCRIT MAIS PAS CONSTRUIT

Pour que tu ne le confondes pas avec du fait. **Zéro ligne de Rust derrière
tout ceci** :

```
docs/plans/2026-07-28-resource-algebra.md   1535 lignes
  · 42 théorèmes, dont la pénalité des vagues (T_wave ≥ T_flow, ratio non borné)
  · les 14 dimensions de ressources + leurs règles de composition sous ; et ‖
  · 17 affirmations RÉFUTÉES, en tête du document
  · 4 ratifications opérateur avec leur raisonnement

l'ordonnanceur dataflow (~2×, optimal sous P∞)
la concurrence par fournisseur — PRÉREQUIS mesuré du précédent
l'arena / le harnais reproductible
```

C'est le chantier de fond, il n'a **pas commencé**, et c'est ce qui avait été
demandé en premier. Un fail-open publié est passé devant, à raison. Mais si tu
veux qu'il démarre, la règle à tenir est : **pendant ce chantier, une trouvaille
sécurité se CONSIGNE, elle n'interrompt pas** — sauf fail-open publié.

Sans cette règle il ne démarrera jamais : il y aura toujours une trouvaille
légitime pour passer devant.

---

## §11 · TRAVAILLE EN AUTONOMIE

Lance des swarms, commite au fil, vérifie chaque affirmation toi-même avant de
la relayer. Les agents se trompent — cinq fois cet arc ils m'ont corrigé, et
trois fois ils se sont trompés et j'ai dû les réfuter. Les deux arrivent.
