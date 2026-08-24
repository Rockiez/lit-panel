[简体中文](README.md) | [English](README.en.md) | [Français](README.fr.md) | [Español](README.es.md)

# lit-panel

La version 0.5.5 est un plugin de critique littéraire à onze sièges pour les mémoires et les récits en chinois. Chaque siège s’exécute dans un contexte de subagent réel et isolé. Les sièges rendent des jugements structurés accompagnés de citations littérales ; des scripts ferment la chaîne d’exécution, valident les schémas, invalident les citations non vérifiables et dérivent des bandes qualitatives A/B/C/N/A ainsi qu’une vue de score déterministe de 0-100 avec un état de preuve explicite. Agent Plugins est la voie d’installation et de découverte de premier rang avec Codex CLI 0.147.0 ou version ultérieure.

## Matrice de compatibilité

| Hôte | Version minimale vérifiée | Chemin natif | Remarques |
|---|---:|---|---|
| Codex CLI / App | 0.147.0 | Agent Plugin + `spawn_agent` natif | Agent Plugins v1 transporte le skill ; des fichiers `.codex/agents/*.toml` facultatifs enrichissent l’installation |
| Claude Code | 2.1.63 | plugin `agents/*.md` + outil `Agent` | Emploie la terminologie et le chemin d’exécution `Agent` actuels |
| Google Antigravity | CLI 1.1.12 | agents personnalisés du plugin + appels répétés à `invoke_subagent` | Les appels peuvent être concurrents ; le projet ne suppose pas l’existence garantie d’une API batch unique à tableau |

Le noyau portable de la spécification ouverte [Agent Plugins 1.0](https://agent-plugins.org/specification) couvre actuellement les skills et les serveurs MCP ; il n’enregistre pas une même définition d’agent personnalisé sur tous les hôtes. Le dépôt conserve donc la sémantique d’exécution dans `core/` et génère des définitions d’agent natives via `adapters/`. Le manifeste Agent Plugin de Codex et la configuration des subagents personnalisés Codex constituent deux couches distinctes.

## Installation

L’installation normale ne nécessite ni de cloner le dépôt ni d’exécuter d’abord le constructeur Python. Le gestionnaire de plugins natif de chaque hôte lit directement sa distribution autonome et versionnée dans le dépôt.

Codex :

```bash
codex plugin marketplace add Rockiez/lit-panel
codex plugin add lit-panel@lit-panel
```

Claude Code :

```bash
claude plugin marketplace add Rockiez/lit-panel
claude plugin install lit-panel@lit-panel
```

Antigravity :

```bash
agy plugin install https://github.com/Rockiez/lit-panel/tree/main/dist/antigravity
```

Après l’installation, démarrez une nouvelle tâche Codex, une nouvelle session Claude Code ou une nouvelle session Antigravity afin que l’hôte actualise la découverte des plugins.

L’installation elle-même n’exécute jamais `scripts/build_dist.py`. La vérification littérale et la dérivation du rapport exigent toujours Python 3.10+ à l’exécution ; il s’agit d’une dépendance d’exécution, pas d’une étape de construction préalable. Les paquets `dist/codex`, `dist/claude` et `dist/antigravity` incluent chacun les personas, les critères, les schémas, le modèle de rapport et les scripts.

Clonez le dépôt uniquement pour une installation locale/hors ligne ou pour le développement. Dans ce cas, `./scripts/install-codex.sh`, `./scripts/install-claude.sh` et `./scripts/install-antigravity.sh` consomment les `dist` versionnés par défaut ; les mainteneurs peuvent ajouter `--rebuild` après une modification de `core/` ou `adapters/`. Les fichiers Agent TOML facultatifs de Codex restent disponibles avec `./scripts/install-codex.sh --project-agents`.

## Modèle d’exécution

```text
prepare_run.py -> run.json + paquets de sièges à l’aveugle mutuel
  -> un subagent indépendant par siège, exécuté en concurrence et à l’aveugle mutuel
  -> deux étapes strictes du Siège 08 par lecteur, avec preuve de contexte et hash de la première lecture
  -> execution-receipt.json prouve les subagents natifs, l’isolation, les dispatchs et la dégradation
  -> validation par seat-output.schema.json
  -> verify_quotes.py contrôle les citations ; un critère en échec peut revenir une seule fois à son siège d’origine, uniquement pour ses quotes
  -> repair_quotes.py fige tous les champs de jugement et revérifie tout, seulement si une réparation est demandée
  -> derive_report.py corrèle tous les reçus et produit un rapport formel ou un diagnostic
```

L’entrée de clôture `verify_quotes.py` et l’audit autonome `verify-quotes.py` partagent le même moteur Tier 1–5 et exécutent tous les cinq tiers par défaut. Tier 1 exact, Tier 2 normalisé et Tier 3 avec ellipses soumises à une longueur minimale peuvent valider ; Tier 4 ne produit qu’un repère non validé et Tier 5 invalide définitivement. Le reçu structuré conserve le tier réel, et Tier 4/5 n’entre jamais directement dans la dérivation des bandes. La version 0.5.3 ajoute une seule reprise auditable limitée aux citations : le siège d’origine ne peut renvoyer que les ids de critères et leurs `quotes` de remplacement ; `repair_quotes.py` fige tous les champs de jugement et revérifie l’ensemble. Une deuxième reprise ou un override manuel est interdit.

`prepare_run.py` accepte `--genre memoir|other` (`memoir` par défaut) et `--readers=N` (1 par défaut). Le preset `standard` active par défaut les Sièges 01 à 09 et 11. `--source` satisfait la condition d’entrée du Siège 01. `--brief` fait ajouter le Siège 10 à `standard` et l’active lorsque `full` ou `custom(...)` l’a déjà sélectionné ; `quick` ne s’étend pas du seul fait de recevoir un brief. La base `quick` est 01, 02, 03 et 08, mais une exécution de mémoires ajoute automatiquement le Siège 11 d’éthique ; sans noyau littéraire, sa bande littéraire formelle est N/A. `full` couvre les Sièges 01 à 11, et toute source ou tout brief manquant devient un manque de couverture. Exclure explicitement le Siège 11 d’un `custom(...)` de mémoires crée également un avertissement.

Le critère A7 du Siège 03 est exclusivement interchapitres. Il n’entre dans le paquet que si `--source` désigne un répertoire contenant récursivement au moins deux fichiers ; aucune source, un fichier unique ou un répertoire à un seul fichier ne l’active.

L’aveugle mutuel est un verrou strict : une évaluation formelle exige de vrais subagents indépendants. Si l’hôte ne peut pas créer de contextes isolés, l’exécution s’arrête par défaut. Avec l’autorisation explicite de l’utilisateur, seul un diagnostic marqué `degraded=true` est permis ; il ne peut pas revendiquer l’aveugle mutuel.

Chaque lecteur `lit-naive-reader` suit un protocole strict en deux étapes. L’étape 1 ne reçoit que le texte et fige l’expérience naturelle. L’étape 2 est soit un follow-up dans le même contexte, soit un nouveau contexte recevant le texte scellé de l’étape 1. Pour chaque lecteur, `execution-receipt.json` enregistre `step_2_mode`, les deux identifiants de contexte et le SHA-256 de l’étape 1 ; les lecteurs restent mutuellement isolés. La dérivation reconstruit aussi le plan canonique et vérifie le SHA-256 de chaque paquet dispatché ; une abstention ne peut pas devenir silencieusement une bande A.

`derive_report.py` ne produit `formal=true` que si les subagents natifs sont prouvés, `degraded=false`, tous les dispatchs, sorties et preuves du Siège 08 sont complets, les empreintes d’entrée et reçus concordent, et `coverage_gaps=[]`. Toute dégradation, dispatch en échec ou non isolé, ressource manquante ou citation invalidée donne un diagnostic avec `bands.fidelity=null`, `bands.literary=null` et la recommandation `仅诊断`. Ce `null` de diagnostic diffère du N/A formel d’une dimension légitimement hors périmètre.

## Vue de score toujours disponible avec état de preuve (0.5.5)

La version 0.5.2 a restauré la formule déterministe v0.4.1 ; la version 0.5.4 a séparé la disponibilité du score de la vérification des citations ; la version 0.5.5 garantit un total de 0 à 100 dès que l’étape 3 produit un rapport. Les sièges n’attribuent toujours aucun nombre : seul `derive_report.py` calcule `derived-report.json.scores`. Les entrées complètes utilisent `status=verified` ; un NA core/extended assorti d’un motif d’inapplicabilité explicite est également un jugement neutre achevé. ABSTAIN, un veto NA, les citations invalides, une exécution dégradée ou des sièges non couverts donnent un score mécanique `status=provisional`, avec chaque limite dans `status_reasons`. Les dimensions absentes restent non évaluées et, sans aucune dimension exploitable, le rapport utilise une base diagnostique fixe de 50.

Sans `--source`, seule la fidélité n’est pas évaluée (`dimensions.fidelity=null`) ; les autres dimensions et le total restent disponibles. Si une source existe, une citation de fidélité incorrecte produit tout de même un score de fidélité provisoire à partir du jugement gelé. Les citations invalidées restent exclues des bandes formelles, des alertes rouges et des révisions.

Les quatre dimensions littéraires partent de 90, avec retraits mécaniques pour les problèmes core/extended et plafonds veto. La propreté IA part de 100, l’expérience lecteur de 85, et l’originalité ajoute +5, +3 ou +0 sans jamais retrancher. Le total combine ces résultats, avec un plafond final de fidélité à 75 pour B et 45 pour C lorsque la source est fournie. Les classes de la vue 0-100 vont de A à D. **Les scores sont mécaniquement dérivés des vecteurs de critères ; les sièges ne produisent aucun nombre.**

## Commandes d’une exécution fermée

```bash
python3 core/lit-panel/scripts/prepare_run.py text.md \
  --preset standard --genre memoir --readers 1 --output runs/example

# Dispatcher les subagents natifs et écrire execution-receipt.json, puis :
python3 core/lit-panel/scripts/validate_execution_receipt.py runs/example/execution-receipt.json
python3 core/lit-panel/scripts/verify_quotes.py runs/example/seat-outputs runs/example/text.txt \
  --output runs/example/verification-receipt.initial.json \
  --repair-request runs/example/quote-repair-request.json
# Si requests n’est pas vide, recueillir quote-repair-patches/*.json auprès des sièges d’origine, puis :
python3 core/lit-panel/scripts/repair_quotes.py \
  runs/example/seat-outputs runs/example/quote-repair-patches \
  runs/example/verification-receipt.initial.json runs/example/text.txt \
  --output-dir runs/example/repaired-seat-outputs \
  --verification-output runs/example/verification-receipt.json \
  --repair-receipt runs/example/quote-repair-receipt.json
python3 core/lit-panel/scripts/derive_report.py \
  <seat-output-dir> <verification-receipt.json> \
  runs/example/run.json runs/example/execution-receipt.json \
  core/lit-panel/references/criteria --text runs/example/text.txt \
  --output-json runs/example/derived-report.json \
  --output-markdown runs/example/report.md
```

Sans critère invalidé, dérivez depuis `seat-outputs` et `verification-receipt.initial.json`. Après une tentative de réparation, utilisez `repaired-seat-outputs` et le `verification-receipt.json` final ; le code de sortie 1 reste diagnostique et ne doit jamais lancer une deuxième reprise.

Avec une source, passez le même `--source <fichier-ou-répertoire>` à `verify_quotes.py` et à `derive_report.py`. Avec un brief, passez aussi le même `--brief <fichier>` à `derive_report.py`. Ses cinq arguments positionnels sont les sorties de sièges, le reçu de vérification, le manifeste d’exécution, le reçu d’exécution et le répertoire de critères ; l’ancienne interface n’est plus valable. Une empreinte source/brief non nulle dans `run.json` provoque un échec immédiat si l’argument correspondant manque ou si son contenu a changé.

## Artefacts de preuve

Une exécution fermée conserve au moins six catégories d’artefacts :

- `run.json`, qui fige empreintes d’entrée, genre, nombre de lecteurs, sièges et sorties attendues ;
- `execution-receipt.json`, qui prouve isolation native, dispatchs, deux étapes du Siège 08 et manques de couverture ;
- un JSON par siège conforme à `seat-output.schema.json` ;
- `verification-receipt.json`, qui consigne chaque correspondance ou invalidation de citation ;
- `derived-report.json`, avec bandes, `scores` et leurs `status/status_reasons`, lignes rouges, révisions et éléments d’arbitrage dérivés mécaniquement ;
- `report.md`, soit la critique formelle destinée au lecteur, soit une projection explicitement diagnostique.

Chaque jugement YES/NO exige une citation littérale. La validation du schéma et la vérification mécanique précèdent la synthèse ; l’échec d’une citation invalide le critère comme preuve formelle, empêche la fermeture formelle de cette exécution et ne peut influencer une bande formelle. Il n’efface pas la vue numérique : le jugement gelé contribue à un score provisoire clairement signalé. Les sièges ne peuvent attribuer ni score, ni pourcentage, ni pondération libre ; seul le script fermé peut dériver des `scores` 0-100 reproductibles avec la formule v0.4.1. A/B/C/N/A reste une vue qualitative indépendante.

## Architecture

```text
core/lit-panel/                 # source unique de la sémantique d’exécution
  SKILL.md
  agents/
  references/
  schema/                       # run / execution / seat / verification / report
  scripts/
adapters/
  codex/
  claude/
  antigravity/
scripts/build_dist.py           # génère les trois dist et les surfaces de compatibilité racine
dist/                           # distributions générées
```

Ne modifiez pas directement `dist/`, `skills/lit-panel/` à la racine ni `agents/` à la racine. Modifiez `core/` ou `adapters/`, reconstruisez, puis exécutez :

```bash
python3 scripts/build_dist.py --check
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/release_check.py
claude plugin validate --strict dist/claude
agy plugin validate dist/antigravity
```

## Confidentialité et publication

`tests/fixtures/` et `tests/runs/` sont définitivement exclus afin qu’aucun contenu réel de contributeur ne soit suivi ou distribué. Les barrières de publication rejettent également ces répertoires dans les distributions, les chemins absolus propres à une machine, les versions de manifeste incohérentes et l’absence de ressources d’exécution autonomes.

Voir [compatibilité et dégradation](docs/COMPATIBILITY.md), [architecture](docs/ARCHITECTURE.md) et `core/lit-panel/SKILL.md` pour le contrat complet.

## Références officielles

- [Version Codex 0.147.0](https://github.com/openai/codex/releases/tag/rust-v0.147.0)
- [Construire des plugins pour Codex](https://developers.openai.com/plugins/build/plugins)
- [Subagents personnalisés Codex](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Subagents Claude Code](https://code.claude.com/docs/en/sub-agents)
- [Plugins CLI Antigravity](https://antigravity.google/docs/cli/plugins)
- [Subagents Antigravity](https://antigravity.google/docs/subagents)

Licence MIT
