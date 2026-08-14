[简体中文](README.md) | [English](README.en.md) | [Français](README.fr.md) | [Español](README.es.md)

# lit-panel (Comité de lecture littéraire)

*An eleven-seat, mutual-blind literary review panel for Chinese memoir / narrative text — a Claude Code / Codex skill.*

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg) ![Version: 0.4.1](https://img.shields.io/badge/version-0.4.1-lightgrey.svg)

Pour un même texte de mémoires ou texte narratif en chinois, onze sièges d'évaluation lisent de manière autonome, sans voir les conclusions des autres. Une logique d'orchestration basée sur des règles explicites effectue la synthèse — produisant une attribution de bande, des preuves mot à mot et des scores multidimensionnels dérivés mécaniquement d'un vecteur de critères (les sièges d'évaluation pratiquent eux-mêmes la zéro notation ; les scores constituent une vue dérivée et non un jugement direct des sièges).

## Pourquoi ce projet existe

Attribuer une note de « 7,5/10 » à un chapitre de mémoires peut sembler objectif, mais cela revient en réalité à compresser une infinité de jugements incommensurables en un nombre d'une précision illusoire — changez la formulation de la consigne ou changez de modèle, et ce nombre dérivera souvent sans vous indiquer ce qui fonctionne, ce qui échoue ou qui a décidé quoi.

L'absence de notation numérique n'est pas une préférence esthétique, mais un choix fondé sur des preuves. Plusieurs critères de ce projet (la série TW pour les sièges 04/05/06/07/09) sont adaptés du **TTCW** (*Torrance Test of Creative Writing*). Lorsque le TTCW évalue la qualité d'une écriture créative, il s'appuie sur un ensemble de critères binaires évalués point par point par des écrivains professionnels plutôt que sur un score continu ; ses recherches originales ont également testé de grands modèles de langage comme évaluateurs TTCW, concluant que les jugements des modèles ne s'alignaient pas fréquemment avec ceux des écrivains professionnels. Les scores numériques écrasent silencieusement ce désalignement sous un chiffre en apparence certain ; lit-panel choisit de préserver les divergences plutôt que de les aplanir.

La réponse de lit-panel consiste à abandonner l'échelle continue pour ne produire que trois éléments concrets :

- **Critères** — la vérification du respect d'un comportement textuel spécifique et observable ;
- **Preuves** — les citations mot à mot appuyant le verdict, vérifiées mécaniquement (toute évaluation s'appuyant sur une citation introuvable est directement invalidée) ;
- **Bandes** — une classification qualitative A/B/C au lieu d'une échelle continue.

Le produit final du rapport est composé d'une **classification par bande (A/B/C) + citations mot à mot + zone de divergence + paquet de révision + tableau de notation multidimensionnel dérivé mécaniquement du vecteur de critères** (nouveauté depuis la v0.4.0). **Les sièges d'évaluation eux-mêmes pratiquent la zéro notation** — le contrat d'entrée/sortie de la section 3.4 n'a pas changé d'un seul mot ; les sièges ne génèrent et n'ont besoin d'aucune conscience des chiffres. Les scores sont une **vue** dérivée par une formule publique à partir du vecteur de critères, reproductible sur l'ensemble du texte (voir `SKILL.md` §5.8). Le système s'oppose aux chiffres d'une précision illusoire issus des impressions d'un modèle (incapable d'expliquer d'où provient un « 7,5/10 » et dérivant à chaque nouvelle tentative), et non à la présence de chiffres en soi. Les bandes qualitatives restent des conclusions qualitatives, et les scores sont une autre présentation des mêmes preuves basées sur des critères — les deux ne se contredisent ni ne se remplacent.

## Mécanisme central

Cette section présente une vue synthétique des mécanismes pour les utilisateurs. La référence d'exécution fait foi dans `skills/lit-panel/SKILL.md` (l'unique logique d'orchestration partagée par les deux plateformes de distribution) ; les spécifications de conception se trouvent dans `docs/DESIGN.md`. En cas de conflit, `SKILL.md` prévaut.

### Comité de lecture à onze sièges

| Siège | Orientation | Condition d'activation | Rôle dans la bande / Permissions spéciales |
|---|---|---|---|
| **01** `lit-fidelity` | Sources uniquement : vérification des affirmations avec étiquettes à cinq états (SUPPORTED/PERMISSIBLE_INFERENCE/UNSUPPORTED/CONTRADICTED/UNVERIFIABLE) | Lorsque `--source` est fourni | Source unique de la bande de fidélité ; droit de veto ligne rouge |
| **02** `lit-continuity` | Cohérence interne au texte : temporalité, personnages, faits et normes | Toujours | Siège de preuves ; droit de veto ligne rouge sur les contradictions avérées |
| **03** `lit-slop` | Traces spécifiques d'IA : marquage des segments selon la bibliothèque de motifs (léger/lourd) | Toujours | Siège de preuves + caractéristiques ; aucun droit de veto |
| **04** `lit-structure` | Structure narrative : scène/résumé, préparation/résolution, agencement des chapitres | Toujours | Siège central de la bande littéraire |
| **05** `lit-character` | Personnages et psychologie : continuité des motivations, ton des dialogues, refus de l'embellissement | Toujours | Siège central de la bande littéraire |
| **06** `lit-prose` | Langue et rythme : cohérence de la voix, enchaînements, précision du vocabulaire | Toujours | Siège central de la bande littéraire |
| **07** `lit-resonance` | Émotion et impact : expérience façonnée vs vécue, refus des émotions forcées | Toujours | Siège central de la bande littéraire |
| **08** `lit-naive-reader` | Lecteur naïf : aucun critère avant lecture, rapport d'expérience pure, vérification post-lecture | Toujours (exécution stricte en deux étapes) | Participant au jugement synthétisé, exclu du vecteur de critères ; modèle d'évaluation post-lecture |
| **09** `lit-originality` | Originalité et clichés : stéréotypes de l'écriture humaine, voix personnelle | Toujours | Dimension de bonus (depuis v0.4.1 exclu de la bande, problèmes rétrogradés en suggestions de peaufinage) |
| **10** `lit-brief` | Intention éditoriale : respect des éléments de la consigne et des objectifs dramatiques | Si la portée du préréglage contient 10 ET que `--brief` est fourni | Exclu de la bande ; les éléments non atteints sont convertis en révisions |
| **11** `lit-ethics` | Éthique et altérité : qualification unilatérale des personnages, nécessité de la vie privée, dignité des personnes vulnérables | Activé par défaut pour les mémoires (une exclusion explicite via `custom` déclenche toujours un avertissement) | Exclu de la bande ; les constatations nécessitent toujours un arbitrage humain |

**Niveaux de préréglages** : `quick`=01,02,03,08 ; `standard`=01–09+11 (ne comprend pas 10 ; lorsque `--brief` est fourni, 10 est automatiquement inclus sans qu'il soit nécessaire d'utiliser `custom`) ; `full`=01–11 (si 01/10 ne sont pas activés par manque d'entrée, ils sont indiqués avec un niveau d'**avertissement** sous « Sièges ignorés et motifs », car l'intention explicite de full est d'activer l'ensemble des onze sièges) ; `custom(<liste>)`=sélection de numéros de sièges dans le tableau ci-dessus, par exemple `--preset custom(01,03,08)`. Les numéros doivent être enregistrés dans `registry.md`, sinon cela est traité comme une erreur de paramètre et interrompt immédiatement l'exécution. Les sièges conditionnels sont automatiquement ignorés lorsque les conditions ne sont pas remplies, avec mention du motif dans l'en-tête du rapport.

### Processus en trois phases

```
Entrée : Texte évalué + optionnel --source (matériel source) / --brief (consigne éditoriale)
        │
        ▼
Phase Zéro · Pré-vérification mécanique —— Passerelle d'échec fatal : texte tronqué/non clos → interruption immédiate ;
                      extraction de métadonnées, vérification de genre, contrôle mécanique des contraintes du brief
        │
        ▼
Phase Un · Évaluation parallèle à aveugle mutuel —— 11 sièges évaluent indépendamment avec leurs propres fichiers de critères,
                          aveugle mutuel (le Siège 08 s'exécute en 2 étapes : expérience pré-lecture → vérification post-lecture)
        │
        ▼
Phase Deux · Vérification mot à mot des citations —— Vérification mot à mot de chaque citation par rapport à la source ;
                          les citations non vérifiées sont invalidées (mécanisme d'invalidation) ——
                          c'est la ligne de défense empêchant les citations fabriquées d'empoisonner la chaîne de preuves
        │
        ▼
Phase Trois · Synthèse explicite basée sur des règles —— Alertes ligne rouge / vecteur de critères / attribution de bande /
                          export de score / zone de divergence / arbitrage humain / recommandation de décision / paquet de révision,
                          synthétisés mécaniquement sans adjudication esthétique secondaire
        │
        ▼
Sortie : Rapport d'évaluation structuré + Fichier annexe (sidecar) des détails
     (structure references/report-template.md + <nom_du_rapport>-details.md)
```

`--stability` ajoute une seconde exécution indépendante après la Phase Trois pour comparer le taux de basculement au niveau des critères ; `/lit-compare` utilise un pipeline de comparaison indépendant (voir « Référence des paramètres ») sans réutiliser la matrice d'attribution de bande / de décision de la Phase Trois.

### Attribution de bande par critères à trois niveaux

La bande de fidélité (Siège 01) et la bande littéraire (Sièges 04/05/06/07) sont évaluées sur leurs ensembles de critères distincts et ne sont jamais fusionnées en une bande globale unique.

Les critères de la bande littéraire se divisent en trois niveaux :

- **veto** — au maximum ≤2 critères centraux vitaux par siège ; un problème identifié représente un effondrement structurel dans cette dimension. Par exemple, le Siège 07 (Résonance) remplit ses 2 emplacements de veto : émotion totalement non dramatisée et simplement annoncée par le narrateur / émotion dramatisée de force jusqu'à l'altération — atteindre l'un de ces deux extrêmes symétriques signifie que le traitement émotionnel dans ce chapitre a fondamentalement échoué. Voir `criteria/CHANGELOG.md` v0.2.0 pour la liste des critères par siège et les motifs de sélection.
- **core (ordinaire)** — les critères ordinaires restants dans le tableau des critères centraux du siège.
- **extended** — critères supplémentaires ne participant pas à l'attribution des bandes, mais évalués normalement et intégrés dans le vecteur de critères.

L'évaluation de la bande suit les règles de priorité de haut en bas, s'arrêtant au premier critère correspondant :

1. Présence d'un problème sur un critère veto et severity=**HIGH** → Bande littéraire plafonnée à **C** ;
2. Présence d'un problème sur un critère veto mais severity=MEDIUM/LOW → Plafond maximal à **B** (ne déclenche pas C) + transfert obligatoire vers la Zone d'arbitrage humain ;
3. Les conditions 1 et 2 ne sont pas remplies, mais au moins un critère core ordinaire présente un problème → Plafond maximal à **B** ;
4. Veto + core sont entièrement validés → **Candidat Bande A** — le statut de candidat n'est pas une confirmation définitive ; la texture du texte doit être comparée à `anchors/band-a.md` pour confirmer son équivalence avec les exemples ancres ; si le texte est nettement inférieur, il est rétrogradé en B.

**La sévérité (severity) n'est pas un ornement descriptif, mais un interrupteur direct agissant sur quatre mécanismes** :

1. Seuil de la bande de fidélité — seul un statut UNSUPPORTED avec severity=HIGH déclenche le plafonnement à la Bande C de fidélité ; les problèmes avec severity=LOW sont plafonnés à B ;
2. Admission en Zone Ligne Rouge — seuls le statut UNSUPPORTED du Siège 01 avec severity=HIGH et le statut NO du Siège 02 pour une contradiction avérée avec severity=HIGH entrent dans la Zone Ligne Rouge ;
3. Classification du niveau veto — pour les problèmes sur un même critère veto, severity=HIGH plafonne à C, tandis que severity=MEDIUM/LOW plafonne à B et transfère vers l'arbitrage humain ;
4. Ordre du paquet de révision — la sévérité (HIGH/MEDIUM/LOW) détermine l'ordre de priorité pour les sessions de révision, sans se traduire par des déductions numériques.

### Bonus d'originalité (Siège 09, exclu de l'attribution de bande)

Depuis la v0.4.1, le Siège 09 (Examen de l'originalité et des clichés) sort du système de bande à trois niveaux veto/core ci-dessus — sans pénalité de points ni plafonnement de bande. Le Siège 09 est évalué comme d'habitude (verdicts + citations + opinion libre inchangés), mais ses résultats déclenchent exclusivement des **bonus** de score global, selon les règles mécaniques détaillées dans `SKILL.md` §5.8 :

- Critères de réussite de la série O (O2/O3/O5/O6) **tous** à YES et zéro problème identifié sur la série O → Score total **+5** ;
- Critères de réussite ≥3 éléments à YES et zéro problème identifié → Score total **+3** ;
- Tous les autres cas (y compris tout problème identifié sur la série O) → **+0**, **aucune déduction de points en aucune circonstance**.

Les problèmes identifiés (comme l'utilisation excessive de clichés pour O1) sont rétrogradés en suggestions de peaufinage optionnelles, figurant dans les sections « Problèmes et suggestions de révision » et « Commentaires individuels des jurés » du rapport sans être masqués ni affecter la bande. La position produit de ce changement : l'originalité pour les mémoires est une valeur ajoutée et non une obligation centrale — un récit de vie simple mais authentique demeure un mémoire acceptable et ne doit pas voir sa bande abaissée par manque de nouveauté littéraire (motifs détaillés dans `criteria/CHANGELOG.md` v0.4.1).

### Alarme du lecteur naïf

Lorsque tous les critères veto+core des quatre sièges centraux de la bande littéraire **sont entièrement validés**, ce qui devrait normalement produire un Candidat Bande A, une vérification supplémentaire est effectuée : la quatrième question du lecteur naïf (Siège 08) après lecture — « Accepteriez-vous de raconter ce texte à quelqu'un d'autre ? » (n'accepte que « Oui » / « Non », rejetant les réponses floues comme « Ça dépend »).

- **N=1** : Réponse « Oui » → Le Candidat Bande A est confirmé normalement et poursuit vers l'évaluation par ancres. Réponse « Non » → Déclenchement de l'alarme : **n'attribue pas automatiquement la Bande A, ni ne rétrograde à cause de cela** ; la recommandation de décision est réécrite en « **Candidat Bande A (En attente de confirmation manuelle — divergence entre critères et ressenti du lecteur)** », avec transfert obligatoire vers la Zone d'arbitrage humain.
- **N>1** : La décision est régie par la majorité des réponses « Oui » / « Non » ; les égalités sont traitées comme un « Non » — préférant déclencher une vérification manuelle supplémentaire plutôt qu'une validation silencieuse.
- L'alarme n'a de sens que sous le préalable de « zéro problème sur les critères core » — si l'évaluation des critères a déjà plafonné la bande à B ou C en raison de problèmes veto/core, une réponse « Non » du lecteur naïf ne déclenche pas d'alarme supplémentaire, le problème ayant déjà été capturé par les critères.

Ce mécanisme remplace la conception v0.1.1 abandonnée de la « participation positive du lecteur naïf aux conditions de la Bande A ». L'ancienne conception faisait participer directement le lecteur naïf aux verdicts A/B/C ; la nouvelle exclut le lecteur naïf de l'attribution de bande, l'utilisant uniquement comme ultime contrôle du ressenti du lecteur quand les critères « semblent parfaits » — en cas de divergence entre critères et expérience du lecteur, la décision est confiée aux humains et non au mécanisme.

### Conception à aveugle mutuel et anti-biais

- **Double évaluation par inversion d'ordre (uniquement pour `/lit-compare`)** : En mode comparaison, chaque siège évalue la préférence entre A et B à deux reprises — une fois présentée sous l'ordre (A,B), une fois sous l'ordre (B,A). Préférer le même texte deux fois → enregistre la préférence du siège ; préférence inversée selon l'ordre de présentation → enregistre **TIE**. Cette conception est spécifiquement destinée à détecter le biais de position où un évaluateur favorise simplement l'ordre de présentation. La sortie ne fournit que des décomptes de distribution, sans les convertir en scores globaux ou classements pondérés.
- **Isolation structurelle dans la voie parallèle** : Sous Claude Code, les onze sièges sont des sous-agents Task parallèles avec des contextes naturellement isolés, offrant une garantie structurelle d'aveugle mutuel.
- **Déclaration explicite d'oubli dans la voie séquentielle** : Codex ne dispose pas de capacités parallèles natives. Lorsque la session principale incarne chaque siège de manière séquentielle, elle doit déclarer explicitement « L'examen de ce siège se termine ici ; abandon de toutes les conclusions de ce siège » avant de passer au siège suivant. Cela utilise des instructions explicites pour inciter le modèle à simuler l'oubli — car en exécution séquentielle, le contexte de dialogue est continu. Cette déclaration n'est pas une formalité ; c'est la seule mise en œuvre de la discipline d'aveugle mutuel dans un environnement non parallèle (cela reste une simulation, détails ci-dessous dans « Limites connues et risques »).
- **Recommandation d'évaluation croisée multi-familles** : Si la génération et l'évaluation utilisent le même modèle ou la même session, le champ « Divulgation du modèle et de la session » dans l'en-tête du rapport doit le mentionner honnêtement, en recommandant une évaluation croisée multi-familles (par exemple génération par Claude → évaluation par Codex, ou inversement) pour réduire les angles morts d'auto-évaluation où le même ensemble de biais produit et juge le texte.
- **Champ d'opinion libre & conception anti-Goodhart** : Chaque contrat de sortie de siège contient une section « Opinion libre » à côté de son tableau de critères (1 à 3 paragraphes d'intuition professionnelle non contraints par les critères). Avec le mécanisme « aucun critère avant lecture » du Siège 08, ce sont les deux seuls espaces d'expression en dehors du tableau de critères qui ne peuvent pas être contournés en « révisant pour l'examen » — voir la discussion sur le risque Goodhart ci-dessous.

## Installation

### Claude Code (mode extension / plugin)

Trois méthodes, au choix :

```bash
# Méthode 1 : Copie manuelle dans le répertoire local skills (chargé automatiquement comme lit-panel@skills-dir au prochain lancement de claude)
cp -r /path/to/lit-panel ~/.claude/skills/lit-panel
# Les liens symboliques sont également pris en charge pour faciliter les mises à jour :
ln -s /path/to/lit-panel ~/.claude/skills/lit-panel
```

```bash
# Méthode 2 : Enregistrement comme marketplace local puis installation (activé de manière permanente, autre voie officielle)
# Le répertoire racine du dépôt contient déjà .claude-plugin/marketplace.json, inutile de le créer.
claude plugin marketplace add /path/to/lit-panel
claude plugin install lit-panel
```

Testé et validé dans un environnement `HOME` isolé (`HOME=$(mktemp -d) claude plugin marketplace add ...`), les deux commandes affichent :

```
✔ Successfully added marketplace: lit-panel (declared in user settings)
✔ Successfully installed plugin: lit-panel@lit-panel (scope: user)
```

`claude plugin details lit-panel` confirme le manifeste des composants : 3 compétences (`lit-panel` / `lit-review` / `lit-compare`) + 11 agents, correspondant à la structure des répertoires source. Si le nom d'enregistrement de votre marketplace local diffère du nom du plugin (par exemple si vous avez modifié le champ `name` dans `marketplace.json` après un fork), vérifiez le nom avec `claude plugin marketplace list`, puis installez avec `claude plugin install lit-panel@<nom_enregistre>`.

**Un détail découvert lors des tests** : Après installation en tant que plugin, les noms des composants agents listés par `claude plugin details` sont les **noms de fichiers** (comme `ethics-reviewer`) et non le champ `name` du frontmatter de définition de l'agent (comme `lit-ethics`) — la « règle de dégradation de l'attribution » de `SKILL.md` §3.3 est conçue pour cette situation : si l'attribution du sous-agent Task par nom d'agent dans `registry.md` échoue, l'exécution réessaie avec l'identifiant réellement listé par la plateforme.

```bash
# Méthode 3 : Chargement temporaire pour une seule session (sans installation permanente, idéal pour essayer)
claude --plugin-dir /path/to/lit-panel
```

Une fois l'installation terminée, les commandes `/lit-review` et `/lit-compare` sont prêtes à l'emploi. Les onze sièges d'évaluation sont ordonnancés en parallèle comme sous-agents de manière native par Claude Code.

### Codex (mode compétence / skill)

```bash
# Recommandé : Utiliser le script d'installation (détecte une installation existante et demande confirmation avant de remplacer)
./scripts/install-codex.sh

# Ou copier manuellement
cp -r skills/lit-panel ~/.agents/skills/lit-panel
```

**Les compétences nouvellement installées ne sont pas automatiquement découvertes dans la session en cours** : Codex ne scanne les répertoires de compétences qu'au démarrage de la session ; les sessions ouvertes ne seront pas réanalysées. Pour les utiliser immédiatement après l'installation, deux options : démarrer une nouvelle session Codex ; ou demander directement à Codex de lire `~/.agents/skills/lit-panel/SKILL.md` via son chemin absolu sans s'appuyer sur la découverte automatique.

Codex ne dispose pas du mécanisme de sous-agents parallèles natif de Claude Code. Par conséquent, les onze sièges d'évaluation sur Codex sont ordonnancés par `SKILL.md` pour une **exécution séquentielle siège par siège** — la sémantique de l'aveugle mutuel vise l'équivalence (chaque siège reste un contexte indépendant et invisible aux autres), mais comme décrit ci-dessous dans « Limites connues et risques », il s'agit d'une simulation au mieux et non d'une véritable isolation de contexte.

## Démarrage rapide

```bash
# Évaluation d'un texte unique : préréglage standard (01–09+11) avec matériel d'entretien pour activer le Siège 01 Examen de fidélité
/lit-review chapitre.md --source entretien.md --preset standard
```

```bash
# Comparaison A/B : deux textes de même origine/mission, évaluation comparative par défaut sur les 11 sièges avec double évaluation par inversion d'ordre
/lit-compare a.md b.md
```

À quoi ressemble le rapport : Un rapport `/lit-review` (restructuré depuis la v0.4.0) contient strictement huit sections fixes, **sans numérotation dans les titres de section, l'ordre physique correspondant à l'ordre de lecture** — Synthèse globale (style revue de comité, 2 à 3 paragraphes), Alerte Ligne Rouge (apparaît uniquement en présence de source et si elle est déclenchée, immédiatement après la synthèse et avant la carte de score), Carte de score global (score total / niveau de bande / verdict en une phrase, dérivé mécaniquement), Tableau de notation multidimensionnel (quatre dimensions littéraires + dimension bonus d'originalité + propreté IA + expérience lecteur, avec ajout de la fidélité si une source est fournie), Commentaires individuels des jurés (un paragraphe par siège avec le ton d'un juré, citations des problèmes intégrées dans le texte, tableaux interdits), Problèmes et suggestions de révision (format rédigé du paquet de révision), Arbitrage humain requis (apparaît uniquement en présence de contenu ; entrées narratives détaillant les parties, leurs positions respectives et la raison pour laquelle une décision humaine est requise, aucun tableau de critères), Archives de l'évaluation (tableau d'en-tête simplifié) — structure fixe, indépendante de la longueur du texte ou du nombre de problèmes. Les tableaux complets de critères par siège, les journaux de vérification de la Phase 2 et les tableaux de critères bruts pour l'arbitrage humain **ne sont pas intégrés dans le rapport principal**, mais déplacés dans le fichier annexe (sidecar) `<nom_du_rapport>-details.md`, avec des pointeurs dans les Archives de l'évaluation. Pour la structure complète, voir `skills/lit-panel/references/report-template.md`. `/lit-compare` utilise une structure de sortie de comparaison indépendante (préférences par siège + justification + distribution du comité), sans réutiliser ce cadre de bande / notation / décision.

## Référence des paramètres

| Paramètre | Valeurs | Description |
|---|---|---|
| `--preset` | `quick\|standard\|full\|custom(<liste>)` | Détermine la portée des sièges candidats pour cette session, par défaut `standard`. La définition des quatre préréglages se trouve ci-dessus dans « Comité de lecture à onze sièges » ; les numéros de sièges dans `custom(<liste>)` doivent être enregistrés dans `registry.md` ; les numéros non enregistrés interrompent directement l'exécution lors de la pré-vérification mécanique. |
| `--source <chemin_source>` | Chemin de fichier ou de répertoire | Fournit les notes d'entretien ou le matériel source. Active le Siège 01 (Examen de fidélité, source unique de la bande de fidélité, droit de veto ligne rouge). En son absence, la bande de fidélité indique N/A et une ligne d'avertissement obligatoire est affichée sous le titre du rapport. |
| `--brief <chemin_brief>` | Chemin de fichier | Fournit la consigne éditoriale / cahier des charges. Condition nécessaire pour activer le Siège 10 (la portée du préréglage doit également inclure 10) ; déclenche le pré-traitement du brief en Phase 0 (extraction de l'objectif dramatique central + résumé des tâches dramatiques clés) et le contrôle mécanique des contraintes strictes (plage de mots / début et fin spécifiés / composants structurels / mots-clés interdits). |
| `--stability` | Interrupteur (sans valeur) | Déclenche l'auto-contrôle de stabilité : exécute deux évaluations complètes et silencieuses sur le même texte et la même configuration (en aveugle mutuel entre les exécutions), indiquant le taux de basculement au niveau des critères par siège (sans taux global unique). Sortie supplémentaire indépendante du rapport d'évaluation principal, sans effet sur les recommandations de décision. |
| `--readers=N` | Entier positif, par défaut `1` | Nombre d'instances de lecteurs indépendants pour le Siège 08 (Lecteur naïf). N lecteurs sont mutuellement aveugles, chacun exécutant le processus en deux étapes « aucun critère avant lecture → vérification post-lecture » ; le rapport liste les sections par numéro de lecteur. Sans rapport avec le filtrage des sièges ; pour filtrer les sièges participants, utiliser `--preset custom(<liste>)`. |
| `--fast-compare` | Interrupteur (sans valeur), désactivé par défaut | Valable uniquement pour `/lit-compare`. Par défaut, la double évaluation par inversion d'ordre reste active ; la transmission de cette option exécute une seule évaluation par siège (sans inversion d'ordre) + déclaration d'auto-contrôle au niveau du siège pour gagner en vitesse, avec mention obligatoire en en-tête : « Double évaluation par inversion d'ordre omise ; biais de position non protégé ». Adapté aux phases d'itération, déconseillé pour les validations finales. |

## Performances attendues

Voici les références de temps d'exécution mesurées lors des tests (non contractuelles, le temps réel dépendant de la longueur du texte, du modèle, du réseau et du débit d'appel) :

- **Codex (niveau d'inférence xhigh)** : préréglage `quick` (4 sièges en séquentiel) environ 10 minutes ; préréglage `standard` (10–11 sièges en séquentiel) environ 30–45 minutes — le parcours séquentiel effectue un appel complet au modèle par siège, le temps augmentant de manière approximativement linéaire avec le nombre de sièges activés.
- **Claude Code (sous-agents parallèles)** : préréglage `standard` environ égal au **siège individuel le plus lent** (5–8 minutes), car les onze sièges sont des appels Task parallèles groupés dont la durée totale est plafonnée par le siège le plus lent et non cumulée.

**Recommandations** :

- Utilisez `quick` pour les cycles d'itération (modifier un projet, vérifier un problème) ; utilisez `standard` ou `full` pour les validations finales (évaluation finale avant publication, décisions de livraison officielles) — ne réduisez pas les préréglages lors des validations finales pour gagner du temps ; `quick` ne contient aucun siège central de la bande littéraire, produisant une base incomplète pour l'attribution de bande.
- Sur le parcours séquentiel Codex, le niveau de raisonnement pour les sièges d'évaluation peut utiliser `medium` au lieu de `xhigh` — répondre aux tableaux de critères est une tâche de vérification structurée point par point et non une création ouverte nécessitant un raisonnement élevé ; le niveau medium est généralement suffisant et réduit considérablement le temps cumulé des sièges.
- Pour `--source`, ne fournissez que la retranscription/le matériel directement lié au chapitre concerné ; ne transmettez pas un ensemble de chapitres non pertinents — la vérification des citations côté source (Phase 2) recherche dans ce matériel ; plus le matériel est volumineux, plus la vérification est lente, sans améliorer la précision de la bande de fidélité.

**Effet attendu des optimisations de performance de la v0.3.0 (estimation, en attente de vérification)** : La hiérarchisation des obligations de citation (les verdicts de réussite de la plupart des critères ne nécessitent plus de citation obligatoire) et l'optimisation de l'envoi unique du texte sur le parcours séquentiel (le texte principal n'est envoyé qu'une seule fois au début de la session sous Codex) devraient réduire le temps d'exécution séquentiel de `standard` sous Codex de 30–45 minutes à environ **15–20 minutes**. Il s'agit d'estimations basées sur les économies de jetons et d'appels de chaque optimisation, en attente de validation chronométrée de bout en bout sur machine réelle ; la section devra être mise à jour une fois les chiffres confirmés.

## Interprétation du rapport

Un rapport est assemblé strictement selon la structure de `references/report-template.md` (huit sections, voir « Démarrage rapide » ci-dessus, les titres de section ne comportant pas de numérotation, l'ordre physique étant l'ordre de lecture). Voici comment lire chaque section et d'où proviennent les scores.

**D'où proviennent les scores** — Les sièges d'évaluation pratiquent la **zéro notation** du début à la fin : le contrat de sortie de la section 3.4 ne contient que verdict/quote/location/severity/note sans aucun champ numérique. Chaque chiffre de la Carte de score global et du Tableau de notation multidimensionnel est **dérivé mécaniquement a posteriori** par l'orchestrateur en Phase Trois en appliquant les formules déterministes de `SKILL.md` §5.8 au vecteur de critères — les quatre dimensions littéraires (Structure/Personnages/Langue/Émotion) démarrent chacune à une référence de 90 points, les problèmes sur critères veto étant plafonnés selon la sévérité (HIGH → ≤45, MEDIUM/LOW → ≤65), les problèmes sur critères core ordinaires entraînant −12 points chacun, et extended −5 points chacun ; les formules des dimensions Propreté IA (dérivée du Siège 03), Expérience lecteur (dérivée de la série R du lecteur naïf) et Fidélité (extraite de la lettre de la bande de fidélité lorsque la source est fournie) fonctionnent de manière indépendante ; score total = moyenne simple des quatre dimensions littéraires, superposée aux ajustements du Siège 03 (−3 par problème, plafond max −10), au **Bonus d'originalité** (ajout v0.4.1 — critères de réussite de la série O du Siège 09 tous à YES et zéro problème → +5, ≥3 YES et zéro problème → +3, autres avec problèmes → +0, uniquement des ajouts sans réduction) et aux plafonds de score total de la bande de fidélité (Bande C de fidélité → score total plafonné à 45 avec décision forcée à « Recommandation de réécriture » ; Bande B de fidélité → plafonné à 75, les deux restant effectifs après l'ajout des bonus). Les formules sont entièrement publiques, permettant à quiconque de recalculer et de vérifier par rapport au vecteur de critères — c'est précisément la différence entre une évaluation « guidée par les preuves » et une « notation à l'impression » : ce qui est rejeté n'est pas le chiffre, mais le chiffre aux origines inexplicables. La carte de score elle-même est présentée avec un titre H2 + texte en gras (comme « ## Total Score: 45/100 · C »), le rapport complet ne comportant qu'un seul titre H1.

**Signification des bandes qualitatives** — Les bandes sont deux voies qualitatives indépendantes parallèles aux scores, non fusionnées en un score global ni déduites à l'envers des scores :

Bande de fidélité (entièrement basée sur la distribution à cinq états du Siège 01 ; inscrite comme N/A lorsque `--source` est omis, auquel cas la ligne de fidélité n'apparaît pas dans le tableau de notation multidimensionnel) : A = distribution à cinq états totalement propre ; B = aucun CONTRADICTED et aucun UNSUPPORTED avec severity=HIGH, mais présence de problèmes avec severity=MEDIUM/LOW, ou uniquement des statuts PERMISSIBLE_INFERENCE/UNVERIFIABLE sans UNSUPPORTED/CONTRADICTED ; C = présence de CONTRADICTED ou présence de UNSUPPORTED avec severity=HIGH.

Bande littéraire (basée sur les critères veto/core des Sièges 04/05/06/07 ; non produite sous le préréglage `quick` en l'absence de sièges centraux. L'originalité du Siège 09 sort de cette bande depuis la v0.4.1 pour un « Bonus d'originalité » indépendant, voir « Bonus d'originalité (Siège 09, exclu de l'attribution de bande) » ci-dessus) : Règles de classification voir « Attribution de bande par critères à trois niveaux » ci-dessus ; comprend également un état spécial — « **Candidat Bande A (En attente de confirmation manuelle — divergence entre critères et ressenti du lecteur)** », produit lors du déclenchement de l'Alarme du lecteur naïf. Si les deux bandes sont N/A (par exemple préréglage `quick` sans `--source`), la recommandation de décision devient « **Diagnostic uniquement** », listant uniquement les problèmes identifiés pour référence sans afficher de valeurs par défaut de matrice pour simuler de vraies décisions ; la Carte de score global ne produit pas non plus de score conventionnel.

**Alerte Ligne Rouge** — Les sources sont au nombre de deux seulement : Siège 01 évaluant CONTRADICTED ou UNSUPPORTED avec severity=HIGH ; Siège 02 évaluant un problème de contradiction avérée NO avec severity=HIGH. En présence de source et si déclenchée, cette zone apparaît après la Synthèse globale et avant la Carte de score, sous forme de citations associées (citation du verdict + citation source/de comparaison). Une Zone Ligne Rouge non vide ne signifie pas que le rapport s'arrête là — toutes les autres sections sont produites normalement et la Carte de score apparaît de façon habituelle (avec un score total plafonné à 45 sous la Bande C de fidélité).

**Comment sont rédigés les Commentaires individuels des jurés** — Un paragraphe par siège, provenant exclusivement d'extraits et de légères éditions de l'opinion libre du siège / du rapport d'expérience du lecteur naïf. Les citations des problèmes sont intégrées sous forme de citations dans le texte, la couche de synthèse s'interdisant d'ajouter toute évaluation sans source dans ce matériel — le commentaire est un travail d'« édition » et non d'« évaluation », une règle stricte inscrite dans `SKILL.md` §5.9.

**Arbitrage humain requis (présentation fusionnée des anciennes zones de divergence et d'arbitrage humain, apparaissant uniquement en présence de contenu)** — Cette section **interdit totalement les tableaux**, chaque catégorie étant rédigée sous forme d'entrées narratives : parties concernées, position en une phrase, citations dans le texte, et motif nécessitant une décision humaine (les tableaux de critères bruts sont déplacés dans le fichier annexe sous la section « Détails de la zone d'arbitrage humain », avec un pointeur à la fin de cette section). Divergence : coexistence d'un « verdict de problème » et d'un « verdict de passage » sur un même segment de texte, ou opinion libre d'un siège contredisant explicitement la conclusion d'un autre siège, sont comptabilisées comme des divergences — **sans moyenne, sans pondération, sans décision sur le vrai ou le faux**, les deux positions étant juxtaposées sous forme narrative pour décision humaine/éditoriale. Arbitrage humain : les catégories de verdicts suivantes ne sont jamais automatiquement validées ni bloquées —

1. Tous les verdicts ABSTAIN (y compris les statuts ABSTAIN rétrogradés depuis « NA sans motif d'applicabilité ») ;
2. **Tous** les verdicts du Siège 11 (Éthique et altérité), quel que soit le verdict — les constatations éthiques ne sont ni automatiquement validées ni bloquées ;
3. Les verdicts échouant à la vérification mécanique de la Phase 2 et invalidés (avec le motif d'invalidation, pour vérifier si la vérification elle-même s'est trompée) ;
4. Les verdicts de problème sur critères veto avec severity=MEDIUM/LOW (le jugement de sévérité affectant directement l'attribution de bande, une vérification manuelle est nécessaire) ;
5. Les statuts NA sur critères veto (NA nécessitant toujours un motif d'applicabilité ; sans motif, ils sont traités comme ABSTAIN et relèvent de la catégorie 1 ci-dessus ; les critères veto ayant un impact direct sur le plafonnement de bande, NA signifie un niveau de jugement manquant) ; les statuts NA sur critères core ordinaires/extended (avec motif) ne relèvent pas de cette catégorie et sont présentés normalement dans le fichier annexe sans transfert vers cette section ;
6. Les enregistrements de déclenchement de l'Alarme du lecteur naïf.

Si l'une des catégories ci-dessus est vide, l'ensemble de la section n'apparaît pas, sans laisser de titres vides.

**Comment réinjecter les Problèmes et suggestions de révision dans une session de génération** — Synthétise les éléments de la Zone Ligne Rouge + tous les « verdicts de problème » du vecteur de critères, chaque élément = emplacement + citation dans le texte + motif + conseil de révision, ordonnés par sévérité, avec des identifiants d'éléments conservant les id de critères, pouvant être collés directement dans la session de révision suivante comme liste de tâches. Lorsqu'un même emplacement de texte touche plusieurs critères, une seule tâche fusionnée est générée (prenant la sévérité la plus élevée et fusionnant les conseils de révision), évitant la répétition d'un même emplacement dans la liste. **Avis de vérification manuelle** : la vérification mécanique garantit uniquement que les citations existent réellement dans le texte original, mais ne garantit pas que la citation appuie l'affirmation du verdict — une note est ajoutée au bas de la section recommandant une vérification manuelle élément par élément avant exécution.

**Archives de l'évaluation et fichier annexe des détails** — Version simplifiée du tableau d'en-tête d'origine, contenant le nom du texte / le préréglage et les sièges activés (les sièges ignorés étant regroupés en une phrase) / la divulgation du modèle et de la dégradation / les statistiques de vérification / la version des règles, ainsi qu'un pointeur de chemin vers le fichier annexe des détails. Les tableaux de critères complets par siège + les journaux de vérification de la Phase 2 + les tableaux de critères bruts pour l'arbitrage humain ne sont plus intégrés dans le rapport principal, mais conservés dans le fichier annexe `<nom_du_rapport>-details.md` selon l'ancien format « Résumé des tableaux de critères par siège » augmenté d'une section « Détails de la zone d'arbitrage humain ». En l'absence de `--source`, la section ajoute une ligne : « Aucun --source fourni dans cette session ; vérification factuelle omise ; le score reflète uniquement la qualité intrinsèque du texte » — c'est l'unique emplacement d'affichage de la clause de non-responsabilité de fidélité depuis la v0.4.0, remplaçant les bannières d'avertissement complètes sous le titre principal (la Carte de score global elle-même rappelant le même fait en petit texte, ce qui est suffisant).

## Personnalisation et extension

**Les fichiers de critères sont modifiables** : La formulation des critères dans `skills/lit-panel/references/criteria/*.md` peut être peaufinée, mais leur sémantique et leur polarité (`[Pass]` / `[Risk]`) ne peuvent pas être altérées — modifier la sémantique revient à modifier les normes d'évaluation elles-mêmes, ce qui nécessite de suivre la procédure d'extension de sièges / CHANGELOG ci-dessous au lieu d'une simple retouche de texte.

**Consigner les abandons dans CHANGELOG** : La sélection, le remplacement et la dépréciation des critères doivent être consignés dans `skills/lit-panel/references/criteria/CHANGELOG.md`, à raison d'une ligne par entrée avec indication des motifs. La v0.2.0 constitue un exemple de référence — consignant les motifs de sélection des ≤2 critères veto pour chacun des quatre sièges centraux de la bande littéraire, ainsi que les résultats d'audit issus de la lecture des 11 fichiers de critères pour vérifier le chevauchement sémantique.

**Critères privés (modèle `criteria/99-private.md`)** : Tous les fichiers de critères sont distribués publiquement avec le paquet. Pour restaurer l'effet d'un « examen à l'aveugle » (critères supplémentaires inconnus du modèle créateur), vous pouvez créer `skills/lit-panel/references/criteria/99-private.md` (ou un nom similaire), l'ajouter à votre `.gitignore` (non distribué avec le dépôt, hors du bassin de critères public), puis le monter en tant que nouveau siège ou le fusionner dans un fichier de critères existant en suivant les étapes d'extension ci-dessous. Il s'agit d'un renforcement optionnel pour l'environnement local ; lit-panel lui-même ne prédéfinit aucun contenu de critère privé.

**Extension de siège (ouvrir un nouveau siège d'évaluation complet)** : Actions synchrones sur trois éléments, tous obligatoires —

1. Ajouter une ligne dans `registry.md` « Tableau des sièges » (fichier agent / nom agent / chemin du fichier de critères / orientation en une phrase / condition d'activation / rôle dans la bande / permissions spéciales, 8 colonnes sans cellule vide) ;
2. Ajouter un nouveau fichier de définition de siège `agents/*.md` ;
3. Ajouter un fichier de critères correspondant `criteria/*.md`, et consigner les choix dans CHANGELOG.

Avant d'ouvrir un nouveau siège, vous devez valider les « Quatre règles d'admission » (répondant à la question « faut-il ouvrir un siège complet » et non à la qualité d'un critère individuel) :

1. **Méthode de lecture indépendante** — l'approche de lecture diffère des onze sièges existants et ne constitue pas un sous-ensemble détaché d'un tableau de critères existant ;
2. **Chevauchement des critères <20%** — le chevauchement des jugements substantiels avec tout siège existant doit être inférieur à 20 %, sinon il doit être fusionné dans un siège existant ;
3. **Forme de preuve exclusive** — capable de produire une forme de preuve ou un rôle de processus irréalisable par d'autres sièges (comme les citations côté source du Siège 01, le processus en deux étapes du Siège 08, l'arbitrage humain obligatoire du Siège 11) ;
4. **La suppression manquerait une classe d'erreurs** — si le siège est retiré du préréglage `full`, existe-t-il une classe de défauts réels qu'aucun siège restant ne pourrait capturer ? La réponse « Non, d'autres sièges couvrent ce cas » échoue à l'admission.

Les quatre règles doivent être satisfaites pour ajouter un siège. Une deuxième vérification indépendante — **les nouveaux critères eux-mêmes** (qu'ils soient ajoutés à un siège existant ou nouveau) doivent respecter les méta-spécifications de conception de critères (fin de `docs/criteria-pool.md`) : les quatre éléments RaR, les trois règles HealthBench, l'avertissement de contexte Antislop, l'avertissement d'ablation. Les deux vérifications régissent deux sujets différents (faut-il ouvrir un nouveau siège / un critère individuel est-il bien rédigé) et ne se remplacent pas. Pour la procédure complète, voir `registry.md` « Guide d'extension de sièges ».

## Limites connues et risques (Zone de transparence)

Un outil visant à éliminer les biais artificiels de l'IA perdrait toute crédibilité si son propre README évitait d'aborder ses risques et ses limites.

**La vérification des citations empêche la fabrication, pas les fausses interprétations de citations réelles** : La vérification mot à mot de la Phase Deux ne résout qu'un problème — savoir si la phrase figure réellement dans le texte original. Elle protège contre la « fabrication d'une citation inexistante dans l'original », mais n'empêche pas une situation où « la citation existe, mais l'assertion/interprétation qui en est faite dans la note est infondée ». Ce dernier point dépasse les capacités de la vérification mécanique et relève de l'évaluation croisée en aveugle mutuel et de l'arbitrage humain. Les utilisateurs du rapport doivent savoir que cette ligne de défense s'arrête là — ne lisez pas « citation vérifiée » comme « le verdict est nécessairement fondé ».

**L'aveugle mutuel en parcours séquentiel est une simulation au mieux, non une isolation de contexte** : Sous Claude Code, les onze sièges sont des sous-agents Task parallèles avec un contexte naturellement isolé, offrant une garantie structurelle d'aveugle mutuel. Codex ne disposant pas de mécanisme de sous-agents parallèles, la session principale incarne chaque siège de façon séquentielle, en s'appuyant sur « la déclaration explicite d'abandon des conclusions du siège précédent » pour simuler le comportement d'évaluateurs humains ne communiquant pas entre eux — il s'agit d'un jeu de rôle au sein d'un même contexte de dialogue et non de processus ou sessions réellement indépendants. La sémantique vise l'équivalence, mais les mécanismes sous-jacents diffèrent ; les scénarios exigeant une rigueur absolue d'aveugle mutuel doivent prendre en compte cette distinction.

**La transparence des critères est une épée à double tranchant (Loi de Goodhart)** : La distribution publique de tous les fichiers de critères fournit la base d'un outil « auditable, vérifiable et réfutable », mais signifie également que si les modèles de génération sont entraînés ou incités spécifiquement à « réviser » ces critères, ils pourraient théoriquement présenter des tableaux de critères impeccables sans améliorer la qualité réelle du texte — lorsqu'un indicateur devient un objectif, il perd sa valeur d'indicateur. Le lecteur naïf (Siège 08) et les champs d'« opinion libre » des sièges constituent des surfaces anti-baccalauréat naturelles : le lecteur naïf ne voit aucun critère avant lecture et l'opinion libre n'est pas contrainte par les tableaux de critères, aucun des deux n'étant un objectif fixe pouvant être contourné par « le par cœur ». Pour les scénarios nécessitant une résistance renforcée, voir « Critères privés » ci-dessus.

**Le Siège 11 ne remplace pas l'accord préalable hors champ avant publication** : Le Siège 11 évalue si la **présentation interne au texte** comporte des risques éthiques (qualification unilatérale, nécessité de la vie privée, mauvaise attribution, dignité des personnes vulnérables), sans remplacer les vérifications d'accord/d'autorisation hors champ auprès des personnes réelles concernées. Une présentation correcte dans le texte ne signifie pas que l'accord de publication des personnes concernées a été obtenu — cette étape doit toujours être réalisée séparément par des humains en dehors du texte.

**Le jugement littéraire des LLM a un plafond ; le comité réduit la variance, mais ne remplace pas l'édition finale** : L'aveugle mutuel sur onze sièges + la vérification mécanique + la synthèse explicite permettent de réduire la subjectivité arbitraire et les variations ponctuelles d'une « notation à l'impression », rendant le jugement vérifiable, consultable et contestable. Ce que le système ne peut pas faire, c'est remplacer le jugement éditorial final d'un éditeur ou d'un critique humain — la zone de divergence conserve intentionnellement le fait que « les sièges d'évaluation peuvent être en désaccord entre eux », sans chercher à aplanir les divergences sous une synthèse artificielle pour simuler un consensus.

### Limites de vérification (au v0.4.1)

Les mécanismes suivants **bénéficient de preuves d'exécution sur machine réelle** (au moins une évaluation complète exécutée avec des journaux enregistrés) : distribution en aveugle mutuel (les parcours sous-agents Task parallèles de Claude Code et la simulation séquentielle de Codex ont tous deux été exécutés) ; vérification mot à mot + invalidation pour falsification (réexécution de la vérification après altération d'une citation, confirmant que le pipeline de vérification bloque réellement les citations fabriquées) ; assemblage des rapports sous les préréglages `quick` et `standard` ; évaluation croisée entre familles de modèles (exécution de l'évaluation entre familles de modèles sans déviation du processus) ; **chaîne complète de fidélité** (test final des règles v0.2.1 : vérification fichier par fichier du répertoire `--source`, étiquettes à cinq états, statut CONTRADICTED déclenchant la Zone Ligne Rouge et la Bande C de fidélité, sortie de matrice « Recommandation de réécriture » — le siège de fidélité ayant identifié une inexactitude factuelle majeure dans le texte évalué, avec 7/7 citations sources validées) ; **attribution de bande à trois niveaux veto** (problème de sévérité sur critère veto → branche « Max B + révision manuelle » validée en test réel, contrastant avec l'ancien plafonnement erroné à la Bande C pour un simple critère core ordinaire) ; **règles NA** (statut NA avec motif lorsque le préalable d'un critère core est absent, évitant le plafonnement mécanique de bande) ; **contrat de notes avec citations doubles** (89/89 vérifications avec zéro invalidation et zéro violation de format, élimination des anciennes citations concaténées avec « / ») ; **protocole de gestion des déconnexions** (retour des dix sièges, contrastant avec la perte permanente d'un siège dans les anciennes sessions) ; processus en deux étapes du lecteur naïf avec collecte des questions complémentaires.

Les mécanismes suivants **n'ont pas encore fait l'objet d'une vérification d'exécution de bout en bout sur machine réelle** : la branche de blocage de la Bande A de l'Alarme du lecteur naïf et la comparaison avec les ancres du Candidat Bande A (l'accessibilité des règles est confirmée, mais nécessite un texte atteignant le statut de Candidat Bande A pour être déclenchée — aucun texte évalué n'ayant atteint cette branche à ce jour) ; le Siège 10 (Examen de l'intention éditoriale, nécessitant `--brief`) ; l'auto-contrôle de stabilité `--stability` ; le mode comparaison `/lit-compare` (y compris `--fast-compare`) ; l'agrégation de plusieurs lecteurs avec `--readers` > 1 ; l'ordonnancement parallèle natif **après installation en tant que plugin Claude Code** (la chaîne d'installation marketplace a été testée et affiche la liste correcte des composants, mais le lancement effectif d'une évaluation parallèle après installation reste non vérifié) ; **la remesure des améliorations de temps d'exécution v0.3.0** (les chiffres de la v0.3.0 dans la section Performances attendues étant des estimations) ; **la restructuration de la couche de rapport v0.4.0 et l'ensemble de la couche d'export des scores** (les formules du §5.8 ayant été vérifiées par recalcul manuel sur des données historiques de machines réelles — test final zhang-ch01 v0.2.1 — confirmant que les formules sont calculables et reproductibles, `tests/runs/zhang-ch01-v040-format-sample.md` étant l'échantillon rendu ; mais les formules n'ayant pas encore été appelées par l'orchestrateur lors d'une véritable évaluation de bout en bout — un recalcul manuel n'équivalant pas à une vérification d'exécution sur machine réelle) ; **le système de bonus d'originalité v0.4.1** (le passage du Siège 09 du niveau veto/bande au bonus pur) n'a pas non plus été retesté sur machine réelle — les données historiques existantes dans `tests/runs/` provenant de clichés de règles antérieurs à la v0.4.1 ; cet échantillon de version étant un recalcul manuel d'anciennes données avec la nouvelle formule et non une évaluation réelle activant les nouvelles règles, une vérification sur machine réelle devra être réalisée rapidement après la mise en ligne officielle.

Cette liste sera mise à jour au fil des futurs tests sur machine réelle — d'ici là, veuillez considérer ces mécanismes comme « cohérents sur le plan de la conception mais non encore éprouvés dans la pratique » et non comme « vérifiés et fiables ».

## Confidentialité

- Les échantillons de référence dans `skills/lit-panel/references/anchors/` (échantillons de référence pour les bandes A/B/C) sont **des textes entièrement synthétiques**, ne contenant aucune information biographique réelle.
- Les textes et matériels soumis pour évaluation (`--source` / `--brief`) circulent uniquement entre votre session locale Claude Code / Codex et les API des modèles ; lit-panel lui-même n'introduit aucun chemin de transmission, de collecte ou d'envoi externe de données en dehors des appels de modèles nécessaires à l'exécution de l'évaluation.
- **Recommandation pour séparer les sessions de génération et d'évaluation** : Ne demandez pas au modèle de rédiger un texte puis d'évaluer son propre texte dans la même conversation — l'auto-évaluation du modèle n'étant pas une vérité d'évaluation, comme l'indique fidèlement le champ « Divulgation du modèle et de la session » en en-tête du rapport. Si possible, il est recommandé d'effectuer une évaluation croisée multi-familles (par exemple génération par Claude → évaluation par Codex, ou inversement), afin de réduire les angles morts dus aux biais identiques entre rédaction et jugement.

## Origines méthodologiques et remerciements

Les critères ne sont pas rédigés de toutes pièces. Chaque critère porte une étiquette de traçabilité ([Vérifié] / [Traduit] / [Seconde main à vérifier] / [Auto-développé]), la liste complète figure dans `docs/criteria-pool.md` ; nous rappelons ici les principales sources dont s'inspire ce système :

- **TTCW** (*Torrance Test of Creative Writing*) — source de traduction directe pour toute la série de critères TW couvrant le rythme narratif, l'équilibre scène/résumé, le naturel de la fin, la logique des transitions, la complexité des personnages, la flexibilité émotionnelle, la complexité rhétorique, principalement répartis sur les Sièges 04/05/06/07/09, avec TW5 (« tous les éléments de l'histoire s'assemblent pour former un tout unifié, intelligible et satisfaisant ») intégré au Siège 02 (Examen de cohérence interne) comme critère de clôture de la cohérence globale.
- **ConStory** — source de classification des conflits factuels/de cohérence centraux pour l'Examen de fidélité et l'Examen de cohérence interne (confusion de noms, conflits quantitatifs, conflits temporels, conflits de simultanéité, conflits de mémoire, conflits géographiques, violations des normes sociales), représentant la source majeure pour ces deux sièges.
- **Measuring AI Slop** (associé à la méthode du lexique Antislop) — source du cadre de classification à 3 thèmes et 11 dimensions du Siège 03 (Détecteur de traces d'IA) (densité, modélisation, répétition, langage non naturel, verbosité, choix de mots inapproprié, ton/registre), ainsi que de la règle méthodologique selon laquelle « une correspondance dans le lexique ne signifie pas une erreur, le verdict devant passer l'examen du contexte ».
- **EssayBench** — source d'un grand nombre de critères de techniques d'écriture narrative pour la structure, les personnages, la langue et l'émotion (sélection du matériel, niveaux, caractérisation, description de l'environnement, configuration des paragraphes).
- **HANNA** — source des critères d'ancrage élevé pour la participation et la surprise du lecteur naïf.
- **HealthBench** — source des trois règles de conception des critères (un critère vérifie un seul comportement observable ; les énumérations après « par exemple » ne sont pas exhaustives ; les critères de risque évaluent si un phénomène indésirable apparaît).
- **RaR** — source des quatre éléments de conception des critères (base de conseils d'experts ; couverture des modes d'échec courants ; hiérarchisation veto/core/extended excluant les poids numériques ; chaque critère autonome et directement évaluable).

De plus, AlignBench, EQ-bench, factool, lechmazur et les critères d'évaluation de la rédaction du Gaokao sont répartis dans des critères individuels de divers sièges ; pour la liste complète, se référer à `docs/criteria-pool.md`.

**Remerciements particuliers** : Dans le dictionnaire de preuves du Siège 03 `slop-patterns-zh.md`, l'organisation des motifs de style IA en chinois s'inspire des idées de classification publiques de **shuorenhua** (Licence MIT, projet open-source de détection de style IA en chinois) et de **speak-human-tw** — les exemples ayant été entièrement réécrits pour le registre des mémoires / histoires orales, sans copier mot à mot ni correspondre de manière univoque aux entrées individuelles.

## Licence

MIT © 2026 Anamnese Project — voir [`LICENSE`](./LICENSE).
