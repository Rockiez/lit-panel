[简体中文](README.md) | [English](README.en.md) | [Français](README.fr.md) | [Español](README.es.md)

# lit-panel

La versión 0.5.0 es un plugin de crítica literaria con once escaños para memorias y narrativa en chino. Cada escaño se ejecuta en un contexto de subagente real y aislado. Los escaños entregan dictámenes estructurados con citas literales; los scripts cierran la ejecución, validan los esquemas, invalidan citas sin respaldo y derivan una banda cualitativa A/B/C/N/A. Agent Plugins es la ruta de instalación y descubrimiento de primer nivel en Codex CLI 0.147.0 o posterior.

## Matriz de compatibilidad

| Host | Versión mínima verificada | Ruta nativa | Notas |
|---|---:|---|---|
| Codex CLI / App | 0.147.0 | Agent Plugin + `spawn_agent` nativo | Agent Plugins v1 transporta el skill; los archivos opcionales `.codex/agents/*.toml` amplían la instalación |
| Claude Code | 2.1.63 | plugin `agents/*.md` + herramienta `Agent` | Usa la terminología y la ruta de ejecución `Agent` actuales |
| Google Antigravity | CLI 1.1.12 | agentes personalizados del plugin + llamadas repetidas a `invoke_subagent` | Las llamadas pueden ejecutarse en paralelo; el proyecto no presupone una API batch única con array garantizada |

El núcleo portable de la especificación abierta [Agent Plugins 1.0](https://agent-plugins.org/specification) abarca actualmente skills y servidores MCP; no registra una misma definición de agente personalizado en todos los hosts. Por eso el repositorio conserva la semántica de ejecución en `core/` y genera definiciones nativas mediante `adapters/`. El manifest Agent Plugin de Codex y la configuración de subagentes personalizados de Codex son dos capas distintas.

## Instalación

Primero construya las tres distribuciones:

```bash
python3 scripts/build_dist.py
```

Codex:

```bash
./scripts/install-codex.sh
# Opcional: instalar también los 11 archivos Agent TOML en el proyecto actual
./scripts/install-codex.sh --project-agents
```

Claude Code:

```bash
./scripts/install-claude.sh
```

Antigravity:

```bash
./scripts/install-antigravity.sh --cli
./scripts/install-antigravity.sh --ide
./scripts/install-antigravity.sh --workspace /path/to/project
```

Los adaptadores resultantes en `dist/codex`, `dist/claude` y `dist/antigravity` son autocontenidos. Cada uno incluye personas, criterios, esquemas, plantilla de informe y scripts de ejecución; ninguna distribución necesita leer recursos desde el checkout fuente.

## Modelo de ejecución

```text
prepare_run.py -> run.json + paquetes de escaño mutuamente ciegos
  -> un subagente independiente por escaño, en paralelo y a ciegas entre sí
  -> dos pasos estrictos del Escaño 08 por lector, con prueba de contexto y hash de la primera lectura
  -> execution-receipt.json prueba subagentes nativos, aislamiento, despachos y degradación
  -> validación mediante seat-output.schema.json
  -> verify_quotes.py comprueba citas literales e invalida los criterios fallidos
  -> derive_report.py correlaciona todos los recibos y produce un informe formal o un diagnóstico
```

La entrada de cierre `verify_quotes.py` y la auditoría autónoma `verify-quotes.py` comparten un motor Tier 1–5. Tier 1 exacto, Tier 2 normalizado y Tier 3 con elipsis sujeto a longitudes mínimas pueden validar; Tier 4 solo produce un candidato no aprobado para arbitraje humano y Tier 5 invalida de forma definitiva. El recibo estructurado conserva el tier real, y Tier 4/5 nunca entra en la derivación de bandas.

`prepare_run.py` acepta `--genre memoir|other` (`memoir` por defecto) y `--readers=N` (1 por defecto). El preset `standard` activa los Escaños 01 a 09 y 11. `--source` satisface la condición de entrada del Escaño 01. `--brief` hace que `standard` añada el Escaño 10 y lo activa cuando `full` o `custom(...)` ya lo selecciona; `quick` no se amplía solo por recibir un brief. La base `quick` es 01, 02, 03 y 08, pero una ejecución de memorias añade automáticamente el Escaño 11 de ética; sin el núcleo literario, su banda literaria formal es N/A. `full` cubre los Escaños 01 a 11 y cualquier source o brief ausente se declara como brecha de cobertura. Excluir explícitamente el Escaño 11 de un `custom(...)` de memorias también genera una advertencia.

El criterio A7 del Escaño 03 es exclusivamente intercapítulos. Solo entra en el paquete cuando `--source` apunta a un directorio que contiene al menos dos archivos de forma recursiva; ninguna source, un solo archivo o un directorio con un archivo no activa A7.

La evaluación a ciegas mutua es una barrera estricta: una revisión formal exige subagentes reales e independientes. Si el host no puede crear contextos aislados, la ejecución se cierra con fallo por defecto. Con autorización explícita del usuario solo puede producir un diagnóstico marcado `degraded=true`; no puede afirmar que hubo evaluación a ciegas.

Cada lector `lit-naive-reader` sigue un protocolo estricto de dos pasos. El paso 1 solo recibe el texto y congela la experiencia natural. El paso 2 puede ser un follow-up en el mismo contexto o un contexto nuevo que reciba el texto sellado del paso 1. Para cada lector, `execution-receipt.json` registra `step_2_mode`, ambos identificadores de contexto y el SHA-256 del paso 1; los lectores permanecen aislados entre sí. La derivación también reconstruye el plan canónico y verifica el SHA-256 de cada paquete despachado; una abstención no puede convertirse silenciosamente en banda A.

`derive_report.py` solo produce `formal=true` cuando se prueban subagentes nativos, `degraded=false`, están completos todos los despachos, salidas y pruebas del Escaño 08, coinciden los digests de entrada y los recibos, y `coverage_gaps=[]`. Toda degradación, despacho fallido o no aislado, artefacto ausente o cita invalidada produce un diagnóstico con `bands.fidelity=null`, `bands.literary=null` y recomendación `仅诊断`. Este `null` diagnóstico es distinto del N/A formal de una dimensión legítimamente fuera de alcance.

## Comandos de una ejecución cerrada

```bash
python3 core/lit-panel/scripts/prepare_run.py text.md \
  --preset standard --genre memoir --readers 1 --output runs/example

# Despachar subagentes nativos y escribir execution-receipt.json; después:
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

Si existe una source, pase el mismo `--source <archivo-o-directorio>` a `verify_quotes.py` y `derive_report.py`. Si existe un brief, pase también el mismo `--brief <archivo>` a `derive_report.py`. Sus cinco argumentos posicionales son salidas de escaños, recibo de verificación, manifest de ejecución, recibo de ejecución y directorio de criterios; la interfaz anterior ya no es válida. Un digest no nulo de source/brief en `run.json` falla de inmediato si falta el argumento correspondiente o cambió su contenido.

## Artefactos de evidencia

Una ejecución cerrada conserva al menos seis clases de artefactos:

- `run.json`, que congela digests de entrada, género, número de lectores, escaños y salidas esperadas;
- `execution-receipt.json`, que prueba aislamiento nativo, despachos, los dos pasos del Escaño 08 y brechas de cobertura;
- un JSON por escaño conforme a `seat-output.schema.json`;
- `verification-receipt.json`, que registra cada coincidencia o invalidación de cita;
- `derived-report.json`, con bandas, líneas rojas, revisiones y elementos de arbitraje derivados mecánicamente;
- `report.md`, la crítica formal destinada a personas o una proyección marcada explícitamente como diagnóstico.

Todo dictamen YES/NO exige una cita literal. La validación del esquema y la verificación mecánica preceden a la síntesis; una cita fallida invalida el criterio completo, impide el cierre formal de esa ejecución y no puede influir en una banda formal. El proyecto solo permite bandas cualitativas A/B/C/N/A: nunca una puntuación numérica agregada, porcentaje o total ponderado.

## Arquitectura

```text
core/lit-panel/                 # única fuente de semántica de ejecución
  SKILL.md
  agents/
  references/
  schema/                       # run / execution / seat / verification / report
  scripts/
adapters/
  codex/
  claude/
  antigravity/
scripts/build_dist.py           # genera tres dist y las superficies de compatibilidad de la raíz
dist/                           # distribuciones generadas
```

No edite directamente `dist/`, `skills/lit-panel/` de la raíz ni `agents/` de la raíz. Modifique `core/` o `adapters/`, reconstruya y ejecute:

```bash
python3 scripts/build_dist.py --check
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/release_check.py
claude plugin validate --strict dist/claude
agy plugin validate dist/antigravity
```

## Privacidad y publicación

`tests/fixtures/` y `tests/runs/` quedan excluidos permanentemente para impedir que material real de colaboradores sea versionado o empaquetado. Las barreras de publicación también rechazan estos directorios dentro de las distribuciones, rutas absolutas locales, versiones de manifest incoherentes y recursos de ejecución autocontenidos ausentes.

Consulte [compatibilidad y degradación](docs/COMPATIBILITY.md), [arquitectura](docs/ARCHITECTURE.md) y `core/lit-panel/SKILL.md` para ver el contrato completo.

## Referencias oficiales

- [Versión Codex 0.147.0](https://github.com/openai/codex/releases/tag/rust-v0.147.0)
- [Crear plugins para Codex](https://developers.openai.com/plugins/build/plugins)
- [Subagentes personalizados de Codex](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Subagentes de Claude Code](https://code.claude.com/docs/en/sub-agents)
- [Plugins de Antigravity CLI](https://antigravity.google/docs/cli/plugins)
- [Subagentes de Antigravity](https://antigravity.google/docs/subagents)

Licencia MIT
