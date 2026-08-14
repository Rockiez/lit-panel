[简体中文](README.md) | [English](README.en.md) | [Français](README.fr.md) | [Español](README.es.md)

# lit-panel : Système d'évaluation littéraire par comités en double aveugle pour le récit et les mémoires en chinois fondé sur la déconstruction narratologique

*An eleven-seat, mutual-blind literary review panel for Chinese memoir / narrative text — a Claude Code / Codex / Google Antigravity skill.*

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg) ![Version: 0.4.1](https://img.shields.io/badge/version-0.4.1-lightgrey.svg)

> **[Résumé]** Face aux écueils épistémologiques de la notation scalaire continue pseudo-précise, de l'homogénéisation esthétique et des citations hallucinées courantes chez les grands modèles de langage (LLM) dans la critique littéraire et l'évaluation de récits, cette étude présente `lit-panel`, un système multi-agents d'évaluation par les pairs en double aveugle spécifiquement conçu pour les mémoires et les récits non fictionnels en langue chinoise. Fondé sur la narratologie classique et le cadre de critères binaires du test de créativité textuelle de Torrance (TTCW), le système déploie un espace d'évaluation indépendant à onze sièges couvrant la fidélité aux sources, la cohérence interne, la détection des traces de génération artificielle (AI slop), l'architecture narrative, la psychologie des personnages, le rythme de la prose, la résonance affective, la perception phénoménologique du lecteur naïf, l'originalité, la conformité au mandat éditorial et l'éthique narrative. Opérant au sein d'environnements d'exécution physiquement isolés et strictement étanches, les sièges mènent des lectures parallèles, éliminent les fausses affirmations grâce à une vérification textuelle mot à mot rigoureuse et synthétisent des attributions de bandes qualitatives (A/B/C) ainsi que des scores multidimensionnels reproductibles issus de règles formelles déterministes. Les analyses théoriques et empiriques démontrent que cette architecture élimine efficacement la dérive stochastique des scores tout en préservant les tensions intrinsèques et l'incommensurabilité de l'esthétique littéraire.
>
> **[Mots-clés]** Narratologie ; Critique littéraire ; Évaluation par les pairs ; Double aveugle ; TTCW ; Humanités numériques ; Critique de la fausse précision

## 1. Introduction : Dilemme épistémologique et critique des échelles quantitatives continues

Dans la critique littéraire computationnelle et l'évaluation de la qualité textuelle, attribuer une note scalaire continue telle que « 7,5/10 » à un chapitre de mémoires ou à un essai narratif préserve en surface une apparence d'objectivité quantitative. En réalité, cette démarche succombe à l'illusion épistémologique d'écraser des jugements esthétiques pluriels et incommensurables en un nombre scalaire arbitraire. De telles notes numériques manifestent non seulement une dérive statistique notable lors de variations minimes d'instructions ou de changements de modèle, mais masquent également les tensions internes entre l'architecture formelle, l'authenticité de la voix et la probité émotionnelle de l'œuvre.

Le refus des échelles numériques continues ne relève pas d'une convenance esthétique, mais d'un choix méthodologique fondé sur des preuves. Plusieurs critères fondamentaux de ce système (la série TW pour les Sièges 04, 05, 06, 07 et 09) sont issus du cadre théorique du **TTCW** (*Torrance Test of Creative Writing*). Lorsqu'il évalue la qualité de la création narrative, le TTCW emploie explicitement des critères discrets binaires évalués point par point par des écrivains professionnels plutôt que des métriques continues ; ses recherches fondatrices ont mis en lumière un désalignement structurel profond entre les scores scalaires générés par les LLM et les jugements qualitatifs d'auteurs confirmés. Les scores continus aplanissent insidieusement cette divergence ; `lit-panel` choisit de préserver formellement les tensions esthétiques et les désaccords critiques.

En écartant la fausse précision du calcul direct, le système établit trois livrables concrets et vérifiables :

- **Critères discrets** : Vérifier si des comportements textuels précis et observables ainsi que des qualités esthétiques sont satisfaits ;
- **Preuves textuelles mot à mot** : Ancrer chaque verdict dans des citations textuelles vérifiées mécaniquement ; toute citation introuvable ou inventée entraîne l'invalidation immédiate du constat associé, prévenant la corruption de la chaîne de preuves ;
- **Bandes qualitatives** : Fournir une catégorisation qualitative A/B/C au lieu d'échelles continues trompeuses.

Le rapport d'évaluation final synthétise **Bandes qualitatives (A/B/C) + Citations textuelles mot à mot + Zone de divergence préservée + Paquet de directives de révision + Tableau de scores multidimensionnel dérivé mécaniquement d'un vecteur de critères** (introduit en v0.4.0+). **Les sièges d'évaluation appliquent une stricte discipline de zéro notation** (contrat de sortie de la section 3.4) : ils émettent exclusivement des jugements discrets et des citations textuelles sans générer ni percevoir de chiffres ; les scores ne sont que des projections algébriques déterministes et ouvertes du vecteur de critères (voir `SKILL.md` §5.8), garantissant une transparence et une reproductibilité intégrales.

## 2. Cadre théorique et mécanismes d'évaluation par les pairs à onze sièges

Cette section détaille les mécanismes formels d'évaluation pour les chercheurs et praticiens. La référence normative à l'exécution est `skills/lit-panel/SKILL.md` (logique d'orchestration commune partagée entre les plateformes) ; les spécifications de conception se trouvent dans `docs/DESIGN.md`. En cas de divergence, `SKILL.md` prévaut.

### 2.1 Architecture du comité de lecture à onze sièges et déconstruction narratologique

| Identifiant du siège | Domaine de critique théorique & Objet d'examen | Condition d'activation | Rôle dans la bande & Attributs de pouvoir |
|---|---|---|---|
| **01** `lit-fidelity` | Fidélité aux sources : confrontation des affirmations aux documents historiques, étiquettes à cinq états (SUPPORTED/PERMISSIBLE_INFERENCE/UNSUPPORTED/CONTRADICTED/UNVERIFIABLE) | Si `--source` fourni | Déterminant unique de la bande de fidélité ; Droit de veto ligne rouge |
| **02** `lit-continuity` | Cohérence interne au texte : temporalité, identité des personnages, faits et conventions de l'univers | Toujours actif | Siège de preuves fondamentales ; Droit de veto ligne rouge en cas de contradiction avérée |
| **03** `lit-slop` | Détection des artefacts artificiels : balisage de segments selon des lexiques de motifs multidimensionnels (AI slop léger/lourd) | Toujours actif | Extraction de preuves et de caractéristiques ; Aucun droit de veto indépendant |
| **04** `lit-structure` | Structure narratologique : anachronies genettiennes, équilibre scène/sommaire, amorces et résolutions | Toujours actif | Siège délibératif central de la bande littéraire |
| **05** `lit-character` | Caractérisation et agentivité : continuité motivationnelle, registres de dialogue vivants, refus de l'aseptisation | Toujours actif | Siège délibératif central de la bande littéraire |
| **06** `lit-prose` | Stylistique et rythme de la prose : pureté de la voix narrative, transitions syntaxiques, précision sensorielle | Toujours actif | Siège délibératif central de la bande littéraire |
| **07** `lit-resonance` | Résonance et justesse émotionnelle : émotion intellectualisée (*processed*) vs éprouvée (*lived*), refus de l'emphase factice | Toujours actif | Siège délibératif central de la bande littéraire |
| **08** `lit-naive-reader` | Perception phénoménologique du lecteur naïf : test à l'aveugle sans critères préalables, réaction brute et suivi post-lecture | Toujours actif (protocole strict en 2 étapes) | Participe à l'arbitrage final ; Exclu du vecteur de critères de base |
| **09** `lit-originality` | Originalité et défamiliarisation : examen des clichés narratifs, singularité de la voix biographique | Toujours actif | Dimension de bonus strictement positive (sans pénalité ni plafonnement de bande) |
| **10** `lit-brief` | Conformité au mandat éditorial : transmission de l'intention dramatique, respect des contraintes de consigne | Préréglage incluant 10 & `--brief` fourni | Exclu de la bande de base ; Écarts convertis en directives de révision |
| **11** `lit-ethics` | Éthique narrative : protection contre la narration unilatérale abusive, nécessité de la vie privée, dignité des sujets vulnérables | Actif par défaut (avertissement si exclu) | Exclu de la bande de base ; Risques éthiques systématiquement transférés à l'arbitrage humain |

**Préréglages d'évaluation** : `quick`=01,02,03,08 ; `standard`=01–09+11 (configuration par défaut, excluant 10 ; intègre automatiquement 10 si `--brief` est transmis) ; `full`=01–11 (génère un avertissement si 01/10 sont ignorés faute de données) ; `custom(<liste>)`=sélection explicite de sièges, ex. `--preset custom(01,03,08)`. Tout identifiant non enregistré interrompt immédiatement l'exécution.

### 2.2 Protocole d'évaluation fondé sur les preuves en trois étapes (Pré-vérification, Aveugle mutuel, Vérification, Synthèse)

```
Flux d'entrée : Texte cible + Optionnel --source (Documents sources) / --brief (Mandat éditorial)
        │
        ▼
Étape 0 · Pré-vérification mécanique —— Verrou d'interruption : détection de troncature ou de texte inachevé (arrêt immédiat) ;
                                      Nettoyage des métadonnées, validation du genre, vérification des contraintes formelles du mandat
        │
        ▼
Étape 1 · Examen parallèle en double aveugle —— 11 sièges lisent de façon autonome dans des contextes isolés,
                                                appliquant leurs critères dédiés (Siège 08 : protocole strict en 2 temps)
        │
        ▼
Étape 2 · Vérification textuelle des citations —— Moteur de vérification hiérarchique Tier 1–5 (Exact / Normalisé / Ellipse / Flou / Invalide) ;
                                                  Audit mécanique sur tous les champs quote vis-à-vis du texte et des sources, invalidant les hallucinations
        │
        ▼
Étape 3 · Synthèse déterministe par règles —— Alertes ligne rouge / vecteurs de critères / bandes qualitatives /
                                             scores dérivés / zones de divergence / arbitrage humain / plan de révision
        │
        ▼
Sortie : Rapport d'évaluation académique structuré + Registre annexe des preuves
         (schéma references/report-template.md + `<nom_rapport>-details.md`)
```

### 2.3 Stratification qualitative par bandes et gouvernance par veto

Le système maintient deux trajectoires qualitatives indépendantes : la **Bande de fidélité (Siège 01)** et la **Bande littéraire (Sièges 04/05/06/07)**. Ces deux voies sont évaluées en parallèle et ne sont jamais fusionnées en une note globale.

Les critères de la bande littéraire sont structurés en trois niveaux formels :
- **Critères de veto (veto)** : Jusqu'à 2 critères critiques par siège central (par ex. le Siège 07 qualifie à la fois l'absence totale de dramatisation émotionnelle et l'exagération mélodramatique forcée de conditions symétriques de veto).
- **Critères centraux standards (core)** : Critères esthétiques réguliers.
- **Critères étendus (extended)** : Éléments diagnostiques d'appoint, enregistrés dans le vecteur de critères sans conditionner l'accès aux bandes.

Algorithme d'attribution de bande (priorité décroissante, s'arrête au premier critère déclenché) :
1. Présence d'un échec de critère veto avec une gravité `severity=高` (élevée) $\rightarrow$ Bande littéraire plafonnée à **C** (réécriture majeure requise) ;
2. Présence d'un échec de critère veto avec une gravité `severity=中/低` (moyenne/faible) $\rightarrow$ Bande littéraire plafonnée à **B**, avec transfert obligatoire à l'arbitrage humain ;
3. Aucun veto défaillant, mais échec sur $\ge 1$ critère central standard $\rightarrow$ Bande littéraire plafonnée à **B** ;
4. Tous les critères veto et centraux validés $\rightarrow$ Octroi du statut **Candidat Bande A** (sous réserve de confirmation de texture face à `anchors/band-a.md`).

**La sévérité opère comme quatre aiguillages déterministes** :
1. Seuil de bande de fidélité : Seul le statut UNSUPPORTED de haute gravité déclenche le plafonnement en bande C ;
2. Accès à la zone rouge : Les contradictions factuelles graves sont dirigées vers les alertes ligne rouge ;
3. Aiguillage veto : Distingue le blocage en C de la révision humaine en B ;
4. Ordre des révisions : Fixe la hiérarchie de traitement du paquet de révisions.

### 2.4 Système de bonus d'originalité (Incentive positive non punitive)

Depuis la version v0.4.1, le Siège 09 (`lit-originality`) s'est retiré du mécanisme punitif de veto et de plafonnement. La posture critique sous-jacente est nette : **dans le domaine des mémoires et du récit biographique, l'originalité créative constitue un accomplissement exceptionnel et non une obligation morale de base**. Un témoignage d'existence sobre et véridique ne doit pas subir de rétrogradation pour absence d'audace formelle. Les résultats du Siège 09 modulent le score global selon les règles suivantes (voir `SKILL.md` §5.8) :
- Tous les critères positifs d'originalité (O2/O3/O5/O6) **validés** sans aucun constat négatif $\rightarrow$ **+5 points** au score global ;
- Au moins 3 critères positifs validés sans aucun constat négatif $\rightarrow$ **+3 points** ;
- Toute autre situation $\rightarrow$ **+0 point** (mécanisme strictement non déductif). Les constats négatifs sont reversés dans le plan de révision comme suggestions d'amélioration stylistique.

### 2.5 Perception phénoménologique du lecteur naïf et mécanisme d'alarme

Pour éviter que l'évaluation par critères ne dérive en formalisme stérile, le système intègre le Siège 08 (`lit-naive-reader`) comme garde-fou phénoménologique. Dès lors que l'ensemble des critères littéraires est validé et que le texte accède au statut de Candidat Bande A, le système déclenche la question post-lecture du lecteur naïf : *« Seriez-vous sincèrement disposé(e) à raconter ou recommander cette histoire à un proche ? »* (choix binaire strict : Oui / Non).

- **Échantillon $N=1$** : En cas de réponse « Non », le système **n'attribue pas la Bande A sans pour autant rétrograder le texte en Bande B**. Le verdict est formulé sous la mention *« **Candidat Bande A (En attente d'arbitrage humain — Divergence entre critères formels et expérience du lecteur)** »*, suspendant toute validation automatique.
- **Échantillon $N>1$** : Règle de la majorité ; les cas d'égalité déclenchent prudemment l'arbitrage humain.

### 2.6 Isolation en double aveugle et conception expérimentale anti-biais de position

- **Double évaluation avec permutation d'ordre (exclusivité de `/lit-compare`)** : Lors d'évaluations comparatives, chaque siège examine la paire de textes à deux reprises : une fois dans l'ordre (A,B) et une fois dans l'ordre (B,A). Une préférence n'est validée que si le même texte est désigné dans les deux cas ; une inversion désigne un **TIE** (égalité), neutralisant ainsi le biais de position.
- **Isolation contextuelle physique (Google Antigravity / Claude Code)** : Sous Google Antigravity, les sièges sont instanciés en parallèle via `invoke_subagent` ; sous Claude Code, via des tâches Task indépendantes. L'absence de mémoire partagée garantit structurellement le double aveugle.
- **Simulation de réinitialisation d'état (Mode séquentiel Codex)** : En mode séquentiel sous Codex, l'orchestrateur injecte explicitement des consignes d'amnésie entre les sièges afin de simuler la discipline de non-communication.
- **Évaluation croisée multi-modèles** : Les modèles générateurs et les agents évaluateurs doivent appartenir à des familles d'architectures distinctes (ex. génération Claude $\rightarrow$ évaluation Codex / Gemini) pour éviter les biais de complaisance endogènes.
- **Champ d'opinion critique libre** : Chaque siège formule 1 à 3 paragraphes de réflexion critique non contrainte qui, couplés au pré-test du lecteur naïf, forment un rempart contre le détournement des critères (Loi de Goodhart).

## 3. Environnement expérimental et déploiement du système

### 3.1 Déploiement Google Antigravity et ordonnancement concurrent natif

```bash
# Recommandé : Utiliser le script d'installation globale (~/.gemini/config/skills/lit-panel)
./scripts/install-antigravity.sh

# Ou déployer dans le bac à sable de l'espace de travail (.agents/skills/lit-panel)
./scripts/install-antigravity.sh --workspace
```

Antigravity détecte automatiquement la compétence. Lancez l'examen avec `/lit-review <chemin_texte>`. Le système mobilise simultanément 11 sous-agents de raisonnement intermédiaire (`Model: "flash"`) dans des bacs à sable en lecture seule, garantissant un examen isolé et traitant le suivi en 2 étapes du Siège 08 via `send_message`.

### 3.2 Déploiement de l'extension Claude Code et orchestration parallèle de tâches

Modes d'installation pris en charge :

```bash
# Méthode 1 : Lien symbolique dans le dossier local skills (recommandé pour le développement)
ln -s /path/to/lit-panel ~/.claude/skills/lit-panel
# Ou copie intégrale : cp -r /path/to/lit-panel ~/.claude/skills/lit-panel
```

```bash
# Méthode 2 : Enregistrement sur le marketplace local (la racine contient .claude-plugin/marketplace.json)
claude plugin marketplace add /path/to/lit-panel
claude plugin install lit-panel
```

Affichage de validation du terminal :
```
✔ Successfully added marketplace: lit-panel (declared in user settings)
✔ Successfully installed plugin: lit-panel@lit-panel (scope: user)
```

```bash
# Méthode 3 : Débogage temporaire sur session unique
claude --plugin-dir /path/to/lit-panel
```

### 3.3 Évaluation séquentielle Codex et simulation de réinitialisation d'état

```bash
# Recommandé : Exécuter le script d'installation idempotent
./scripts/install-codex.sh

# Ou installer manuellement dans le répertoire Codex global
cp -r skills/lit-panel ~/.agents/skills/lit-panel
```

Dans une nouvelle session Codex, chargez via le chemin absolu ou par découverte automatique. Les 11 sièges s'exécuteront en séquence avec simulation de réinitialisation d'état.

## 4. Prise en main rapide et paradigmes d'invocation

```bash
# Évaluation d'un texte : Préréglage standard (01–09+11) avec retranscription de sources pour le Siège 01
/lit-review chapitre.md --source entretien.md --preset standard
```

```bash
# Évaluation comparée A/B en aveugle : Deux versions candidates avec double évaluation permutée
/lit-compare a.md b.md
```

**Schéma normalisé du rapport académique** : Un rapport `/lit-review` respecte une séquence stricte en huit sections (titres non numérotés) : **Synthèse du jury (2–3 paragraphes) $\rightarrow$ Alertes ligne rouge (en amont de la carte des scores si déclenchées) $\rightarrow$ Carte des scores dérivés (Total/Grade/Verdict) $\rightarrow$ Tableau des scores multidimensionnels (4D littéraire + Bonus originalité + Pureté IA + Expérience lecteur + Fidélité) $\rightarrow$ Commentaires critiques individualisés (remarques rédigées avec citations intégrées) $\rightarrow$ Directives de révision et problèmes $\rightarrow$ Zone d'arbitrage humain (divergences en prose pure, sans tableaux) $\rightarrow$ Archive des métadonnées**. L'intégralité des vecteurs de critères et des journaux de vérification figure dans le fichier annexe `<nom_rapport>-details.md`.

**Outil de vérification autonome des citations** : Pour auditer de façon indépendante l'authenticité des citations hors session, exécutez le script d'audit hiérarchique Tier 1–5 inclus : `python3 <skill-dir>/scripts/verify-quotes.py quotes.json chapitre.md --max-tier 5 [--source entretien.md] [--format text|markdown|json] [--fuzzy-threshold 0.85] [--include-tier]` (valeur par défaut `--max-tier 1` pour correspondance exacte seule ; l'Étape 2 recommande explicitement `--max-tier 5` ; le Tier 4 génère des candidats d'arbitrage non validés distincts du Tier 5 void ; le format JSON déclare `schema_version` `lit-panel.quote-verification/v1`).

## 5. Définitions formelles des paramètres

| Paramètre CLI | Domaine / Format | Fonction académique & Spécification sémantique |
|---|---|---|
| `--preset` | `quick\|standard\|full\|custom(<liste>)` | Définit la sélection des sièges ; valeur par défaut : `standard`. `custom(<liste>)` requiert des identifiants valides déclarés dans `registry.md`. |
| `--source <chemin>` | Fichier ou répertoire | Associe les sources primaires (ex. entretiens retranscrits). Active l'audit de fidélité du Siège 01 ; en son absence, la fidélité est notée N/A avec avertissement explicite. |
| `--brief <chemin>` | Fichier | Associe la consigne d'écriture ou le canevas dramatique. Active le Siège 10 et déclenche la validation des contraintes formelles à l'Étape 0. |
| `--stability` | Drapeau booléen (sans valeur) | Déclenche un test de stabilité et de reproductibilité : réalise deux passes silencieuses indépendantes et calcule la matrice de retournement des critères. |
| `--readers=N` | Entier positif, défaut `1` | Taille de l'échantillon de lecteurs indépendants pour le Siège 08. Chaque lecteur exécute le protocole en deux étapes pour mesurer la distribution des réactions. |
| `--fast-compare` | Drapeau booléen, défaut désactivé | Spécifique à `/lit-compare`. Désactive la double évaluation avec permutation pour une réponse rapide ; affiche un avertissement de biais de position. |

## 6. Évaluation des performances et de la complexité computationnelle

Profils d'exécution constatés selon les environnements :

- **Mode séquentiel Codex (raisonnement moyen/élevé)** : Le préréglage `quick` requiert environ 10 minutes ; `standard` (10–11 sièges consécutifs) nécessite environ 15 à 30 minutes, avec un temps de calcul linéaire $O(N)$ selon le nombre de sièges.
- **Mode concurrent Antigravity / Claude Code** : La durée du préréglage `standard` est bornée par le **siège le plus lent** (environ 5 à 8 minutes), convergeant vers une complexité à temps constant $O(1)$.

**Recommandations opérationnelles** : Utiliser `quick` pour les phases d'écriture exploratoire ; exiger `standard` ou `full` pour les évaluations éditoriales formelles ; sous Codex séquentiel, régler le raisonnement sur `medium` pour concilier rigueur de vérification et rapidité.

## 7. Structure du rapport d'évaluation et mécanismes de dérivation multidimensionnelle des scores

**Axiomes de dérivation des scores** : Les sièges maintiennent une **stricte absence de notation**, n'émettant que des jugements discrets et des citations textuelles. À l'Étape 3, le moteur applique l'équation algébrique définie dans `SKILL.md` §5.8 :
$$\text{Base Score} = \frac{1}{4} \sum_{i \in \{04,05,06,07\}} S_i$$
où chaque dimension littéraire part de 90 points, les manquements veto plafonnent les scores (élevé $\le 45$, moyen/faible $\le 65$), les défauts centraux standards retirent 12 points et les critères étendus 5 points. S'y ajoutent la déduction d'artefacts IA du Siège 03 ($-3/\text{élément}$, max $-10$), le bonus d'originalité du Siège 09 ($+3 \sim +5$, non déductif) et les plafonds de fidélité du Siège 01 (Bande C de fidélité plafonne le total à 45 avec consigne de réécriture obligatoire).

**Règles de la zone d'arbitrage humain** : Cette section **interdit formellement les tableaux**, exposant toutes les divergences critiques sous forme de prose narrative. Six catégories d'événements imposent un arbitrage humain :
1. Tout jugement ABSTAIN ;
2. Tout constat du Siège 11 (éthique narrative) ;
3. Les critères invalidés pour échec de vérification textuelle à l'Étape 2 ;
4. Les manquements veto de gravité `severity=中/低` (moyenne/faible) ;
5. Les critères veto marqués NA (non applicable) ;
6. Le déclenchement de l'alarme phénoménologique du Siège 08.

## 8. Bassin de critères personnalisés et critères d'extension des sièges

- **Invariance sémantique** : La formulation des critères dans `references/criteria/*.md` peut être affinée, mais leur polarité (`[通过]`/`[风险]`) doit demeurer inchangée. Toute modification doit figurer dans `references/criteria/CHANGELOG.md`.
- **Intégration de critères privés (`criteria/99-private.md`)** : Possibilité d'intégrer des critères locaux non publics pour éviter l'adaptation artificielle des modèles générateurs.
- **Quatre axiomes d'extension d'un siège** : La création d'un siège exige :
  1. **Une perspective critique distincte** (non incluse dans les sièges existants) ;
  2. **Un chevauchement sémantique $<20\%$** ;
  3. **Une typologie de preuve exclusive** (ex. recoupement de sources, sondage en deux temps) ;
  4. **Une couverture irremplaçable d'erreurs potentielles**.

## 9. Analyse des limites et frontières de validité empirique (Section d'honnêteté)

Le système expose en toute transparence ses limites méthodologiques :

- **La vérification textuelle garantit l'existence, non l'interprétation herméneutique** : La vérification mécanique de l'Étape 2 confirme uniquement la présence physique de l'extrait dans le texte ; elle ne certifie pas la justesse absolue de l'interprétation critique portée dans la note.
- **Sensibilité à la loi de Goodhart pour les critères publics** : Dès lors que les métriques d'évaluation deviennent des cibles d'optimisation pour les modèles générateurs, elles perdent leur pertinence diagnostique. Le système y remédie par des lectures naïves à l'aveugle et des commentaires critiques libres.
- **L'éthique textuelle ne remplace pas le consentement juridique des personnes réelles** : Le Siège 11 analyse uniquement la représentation textuelle et non l'obtention légale du consentement des personnes citées.
- **Réduction de la variance plutôt que substitution au jugement éditorial** : L'évaluation collégiale en double aveugle neutralise le bruit subjectif individuel pour fournir un dossier de preuves robuste ; elle ne saurait se substituer au discernement esthétique ultime des directeurs éditoriaux.

### 9.1 Frontières de validité empirique

Au stade de la version v0.4.1, la validation empirique des modules s'établit comme suit :
- **Validé empiriquement en exécution réelle** : Pipeline de distribution en double aveugle, vérification hiérarchique des citations Tier 1–5 et invalidation des hallucinations (Exact / Normalisé / Ellipse / Flou / Invalide), configurations `quick`/`standard`, évaluation croisée multi-modèles, audit intégral de fidélité, déclinaison des bandes par veto, protocole en 2 étapes du lecteur naïf.
- **En attente de validations empiriques complémentaires** : Branche de comparaison de texture pour les textes exceptionnels atteignant la Bande A face à l'alarme du lecteur naïf, analyse approfondie de mandats complexes pour le Siège 10, agrégation statistique multi-lecteurs ($N > 1$) et tests de charge sur textes très longs en environnement de production intense.

## 10. Déclaration sur la confidentialité des données et l'éthique académique

- Les textes étalons de référence dans `references/anchors/` sont **exclusivement synthétiques** et exempts de données biographiques réelles.
- Les textes soumis et leurs sources transitent uniquement entre l'environnement local de l'utilisateur et les API des modèles configurés ; aucune télémétrie externe n'est pratiquée.
- Nous recommandons vivement de **séparer les sessions de rédaction et d'évaluation**, en favorisant des modèles d'architectures différentes pour prévenir les complaisances endogènes.

## 11. Filiation méthodologique et remerciements théoriques

La conception et le corpus de critères s'inspirent des travaux académiques et projets ouverts suivants (voir `docs/criteria-pool.md`) :
- **TTCW (Torrance Test of Creative Writing)** : Fondement de la transposition des critères de rythme, d'équilibre des scènes et de complexité des personnages ;
- **ConStory** : Typologie des conflits de cohérence et d'anomalies factuelles ;
- **Measuring AI Slop & Antislop** : Taxonomies des tics de génération artificielle et principes d'analyse contextuelle ;
- **EssayBench & HANNA** : Méthodes d'évaluation stylistique et protocole de lecture phénoménologique ;
- **HealthBench & RaR** : Règles de conception de critères binaires observables et rubriques en quatre points ;
- **Contributions de la communauté** : Classification des tournures artificielles inspirée des projets ouverts **shuorenhua** et **speak-human-tw**.

## 12. Licence

Ce projet est distribué sous licence MIT. Consulter [`LICENSE`](./LICENSE) pour plus de précisions.
