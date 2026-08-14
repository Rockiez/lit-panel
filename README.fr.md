[简体中文](README.md) | [English](README.en.md) | [Français](README.fr.md) | [Español](README.es.md)

# lit-panel

La version 0.5.0 est un plugin de critique littéraire à onze sièges pour les mémoires et les récits en chinois. Chaque siège s’exécute dans un contexte de subagent réel et isolé. Les sièges rendent des jugements structurés accompagnés de citations littérales ; des scripts ferment la chaîne d’exécution, valident les schémas, invalident les citations non vérifiables et dérivent une bande qualitative A/B/C/N/A. Agent Plugins est la voie d’installation et de découverte de premier rang avec Codex CLI 0.147.0 ou version ultérieure.

## Matrice de compatibilité

| Hôte | Version minimale vérifiée | Chemin natif | Remarques |
|---|---:|---|---|
| Codex CLI / App | 0.147.0 | Agent Plugin + `spawn_agent` natif | Agent Plugins v1 transporte le skill ; des fichiers `.codex/agents/*.toml` facultatifs enrichissent l’installation |
| Claude Code | 2.1.63 | plugin `agents/*.md` + outil `Agent` | Emploie la terminologie et le chemin d’exécution `Agent` actuels |
| Google Antigravity | CLI 1.1.12 | agents personnalisés du plugin + appels répétés à `invoke_subagent` | Les appels peuvent être concurrents ; le projet ne suppose pas l’existence garantie d’une API batch unique à tableau |

Le noyau portable de la spécification ouverte [Agent Plugins 1.0](https://agent-plugins.org/specification) couvre actuellement les skills et les serveurs MCP ; il n’enregistre pas une même définition d’agent personnalisé sur tous les hôtes. Le dépôt conserve donc la sémantique d’exécution dans `core/` et génère des définitions d’agent natives via `adapters/`. Le manifeste Agent Plugin de Codex et la configuration des subagents personnalisés Codex constituent deux couches distinctes.

## Installation

Construisez d’abord les trois distributions :

```bash
python3 scripts/build_dist.py
```

Codex :

```bash
./scripts/install-codex.sh
# Facultatif : installer aussi les 11 fichiers Agent TOML dans le projet courant
./scripts/install-codex.sh --project-agents
```

Claude Code :

```bash
./scripts/install-claude.sh
```

Antigravity :

```bash
./scripts/install-antigravity.sh --cli
./scripts/install-antigravity.sh --ide
./scripts/install-antigravity.sh --workspace /path/to/project
```

Les adaptateurs produits dans `dist/codex`, `dist/claude` et `dist/antigravity` sont autonomes. Chacun contient les personas, les critères, les schémas, le modèle de rapport et les scripts d’exécution ; aucune distribution ne doit relire les ressources du dépôt source.

## Modèle d’exécution

```text
prepare_run.py -> run.json + paquets de sièges à l’aveugle mutuel
  -> un subagent indépendant par siège, exécuté en concurrence et à l’aveugle mutuel
  -> deux étapes strictes du Siège 08 par lecteur, avec preuve de contexte et hash de la première lecture
  -> execution-receipt.json prouve les subagents natifs, l’isolation, les dispatchs et la dégradation
  -> validation par seat-output.schema.json
  -> verify_quotes.py contrôle les citations littérales et invalide les critères en échec
  -> derive_report.py corrèle tous les reçus et produit un rapport formel ou un diagnostic
```

`prepare_run.py` accepte `--genre memoir|other` (`memoir` par défaut) et `--readers=N` (1 par défaut). Le preset `standard` active par défaut les Sièges 01 à 09 et 11. `--source` active le Siège 01 de fidélité et `--brief` le Siège 10 d’intention éditoriale. La base `quick` est 01, 02, 03 et 08, mais une exécution de mémoires ajoute automatiquement le Siège 11 d’éthique ; sans noyau littéraire, sa bande littéraire formelle est N/A. `full` couvre les Sièges 01 à 11, et toute source ou tout brief manquant devient un manque de couverture. Exclure explicitement le Siège 11 d’un `custom(...)` de mémoires crée également un avertissement.

Le critère A7 du Siège 03 est exclusivement interchapitres. Il n’entre dans le paquet que si `--source` désigne un répertoire contenant récursivement au moins deux fichiers ; aucune source, un fichier unique ou un répertoire à un seul fichier ne l’active.

L’aveugle mutuel est un verrou strict : une évaluation formelle exige de vrais subagents indépendants. Si l’hôte ne peut pas créer de contextes isolés, l’exécution s’arrête par défaut. Avec l’autorisation explicite de l’utilisateur, seul un diagnostic marqué `degraded=true` est permis ; il ne peut pas revendiquer l’aveugle mutuel.

Chaque lecteur `lit-naive-reader` suit un protocole strict en deux étapes. L’étape 1 ne reçoit que le texte et fige l’expérience naturelle. L’étape 2 est soit un follow-up dans le même contexte, soit un nouveau contexte recevant le texte scellé de l’étape 1. Pour chaque lecteur, `execution-receipt.json` enregistre `step_2_mode`, les deux identifiants de contexte et le SHA-256 de l’étape 1 ; les lecteurs restent mutuellement isolés. La dérivation reconstruit aussi le plan canonique et vérifie le SHA-256 de chaque paquet dispatché ; une abstention ne peut pas devenir silencieusement une bande A.

`derive_report.py` ne produit `formal=true` que si les subagents natifs sont prouvés, `degraded=false`, tous les dispatchs, sorties et preuves du Siège 08 sont complets, les empreintes d’entrée et reçus concordent, et `coverage_gaps=[]`. Toute dégradation, dispatch en échec ou non isolé, ressource manquante ou citation invalidée donne un diagnostic avec `bands.fidelity=null`, `bands.literary=null` et la recommandation `仅诊断`. Ce `null` de diagnostic diffère du N/A formel d’une dimension légitimement hors périmètre.

## Commandes d’une exécution fermée

```bash
python3 core/lit-panel/scripts/prepare_run.py text.md \
  --preset standard --genre memoir --readers 1 --output runs/example

# Dispatcher les subagents natifs et écrire execution-receipt.json, puis :
python3 core/lit-panel/scripts/validate_execution_receipt.py runs/example/execution-receipt.json
python3 core/lit-panel/scripts/verify_quotes.py runs/example/seat-outputs runs/example/text.txt \
  --output runs/example/verification-receipt.json
python3 core/lit-panel/scripts/derive_report.py \
  runs/example/seat-outputs runs/example/verification-receipt.json \
  runs/example/run.json runs/example/execution-receipt.json \
  core/lit-panel/references/criteria --text runs/example/text.txt \
  --output-json runs/example/derived-report.json \
  --output-markdown runs/example/report.md
```

Avec une source, passez le même `--source <fichier-ou-répertoire>` à `verify_quotes.py` et à `derive_report.py`. Avec un brief, passez aussi le même `--brief <fichier>` à `derive_report.py`. Ses cinq arguments positionnels sont les sorties de sièges, le reçu de vérification, le manifeste d’exécution, le reçu d’exécution et le répertoire de critères ; l’ancienne interface n’est plus valable. Une empreinte source/brief non nulle dans `run.json` provoque un échec immédiat si l’argument correspondant manque ou si son contenu a changé.

## Artefacts de preuve

Une exécution fermée conserve au moins six catégories d’artefacts :

- `run.json`, qui fige empreintes d’entrée, genre, nombre de lecteurs, sièges et sorties attendues ;
- `execution-receipt.json`, qui prouve isolation native, dispatchs, deux étapes du Siège 08 et manques de couverture ;
- un JSON par siège conforme à `seat-output.schema.json` ;
- `verification-receipt.json`, qui consigne chaque correspondance ou invalidation de citation ;
- `derived-report.json`, avec bandes, lignes rouges, révisions et éléments d’arbitrage dérivés mécaniquement ;
- `report.md`, soit la critique formelle destinée au lecteur, soit une projection explicitement diagnostique.

Chaque jugement YES/NO exige une citation littérale. La validation du schéma et la vérification mécanique précèdent la synthèse ; l’échec d’une citation invalide le critère entier, empêche la fermeture formelle de cette exécution et ne peut influencer une bande formelle. Le projet n’autorise que les bandes qualitatives A/B/C/N/A : aucun score numérique agrégé, pourcentage ou total pondéré.

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
