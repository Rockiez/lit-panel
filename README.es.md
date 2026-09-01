[简体中文](README.md) | [English](README.en.md) | [Français](README.fr.md) | [Español](README.es.md)

# lit-panel

La versión 0.6.1 es un plugin de crítica literaria con once escaños para memorias y narrativa en chino. Cada escaño se ejecuta en un contexto de subagente real y aislado. Los escaños entregan dictámenes estructurados con citas literales; los scripts cierran la ejecución, validan los esquemas, invalidan citas sin respaldo y derivan bandas cualitativas A/B/C/N/A junto con una vista de puntuación determinista de 0-100 con estado de evidencia explícito. Agent Plugins es la ruta de instalación y descubrimiento de primer nivel en Codex CLI 0.147.0 o posterior.

## Matriz de compatibilidad

| Host | Versión mínima verificada | Ruta nativa | Notas |
|---|---:|---|---|
| Codex CLI / App | 0.147.0 | Agent Plugin + `spawn_agent` nativo | Agent Plugins v1 transporta el skill; los archivos opcionales `.codex/agents/*.toml` amplían la instalación |
| Claude Code | 2.1.63 | plugin `agents/*.md` + herramienta `Agent` | Usa la terminología y la ruta de ejecución `Agent` actuales |
| Google Antigravity | CLI 1.1.12 | agentes personalizados del plugin + llamadas repetidas a `invoke_subagent` | Las llamadas pueden ejecutarse en paralelo; el proyecto no presupone una API batch única con array garantizada |

El núcleo portable de la especificación abierta [Agent Plugins 1.0](https://agent-plugins.org/specification) abarca actualmente skills y servidores MCP; no registra una misma definición de agente personalizado en todos los hosts. Por eso el repositorio conserva la semántica de ejecución en `core/` y genera definiciones nativas mediante `adapters/`. El manifest Agent Plugin de Codex y la configuración de subagentes personalizados de Codex son dos capas distintas.

## Instalación

La instalación normal no requiere clonar el repositorio ni ejecutar primero el constructor de Python. El gestor de plugins nativo de cada host lee directamente su distribución autocontenida y versionada en el repositorio.

Codex:

```bash
codex plugin marketplace add Rockiez/lit-panel
codex plugin add lit-panel@lit-panel
```

Claude Code:

```bash
claude plugin marketplace add Rockiez/lit-panel
claude plugin install lit-panel@lit-panel
```

Antigravity:

```bash
agy plugin install https://github.com/Rockiez/lit-panel/tree/main/dist/antigravity
```

Después de instalar, abra una nueva tarea de Codex, sesión de Claude Code o sesión de Antigravity para que el host actualice el descubrimiento del plugin.

La instalación nunca ejecuta `scripts/build_dist.py`. La verificación literal y la derivación de informes todavía requieren Python 3.10+ en tiempo de ejecución; es una dependencia de ejecución, no un paso previo de construcción. Los paquetes `dist/codex`, `dist/claude` y `dist/antigravity` incluyen personas, criterios, esquemas, plantilla de informe y scripts.

Clone el repositorio solo para una instalación local/sin conexión o para desarrollo. En ese caso, `./scripts/install-codex.sh`, `./scripts/install-claude.sh` y `./scripts/install-antigravity.sh` consumen los `dist` versionados de forma predeterminada; los mantenedores pueden añadir `--rebuild` después de modificar `core/` o `adapters/`. Los archivos Agent TOML opcionales de Codex siguen disponibles mediante `./scripts/install-codex.sh --project-agents`.

## Modelo de ejecución

```text
prepare_run.py -> run.json + paquetes de escaño mutuamente ciegos
  -> un subagente independiente por escaño, en paralelo y a ciegas entre sí
  -> dos pasos estrictos del Escaño 08 por lector, con prueba de contexto y hash de la primera lectura
  -> execution-receipt.json prueba subagentes nativos, aislamiento, despachos y degradación
  -> validación mediante seat-output.schema.json
  -> verify_quotes.py comprueba citas; un criterio fallido puede volver una sola vez a su escaño original, solo para sus quotes
  -> repair_quotes.py congela todos los campos del dictamen y vuelve a verificar todo, solo si se pidió una reparación
  -> derive_report.py correlaciona todos los recibos y produce un informe formal o un diagnóstico
```

La entrada de cierre `verify_quotes.py` y la auditoría autónoma `verify-quotes.py` comparten un motor Tier 1–5 y ejecutan los cinco niveles de forma predeterminada. Tier 1 exacto, Tier 2 normalizado y Tier 3 con elipsis sujeto a longitudes mínimas pueden validar; Tier 4 solo produce un localizador no aprobado y Tier 5 invalida de forma definitiva. El recibo estructurado conserva el tier real, y Tier 4/5 nunca entra directamente en la derivación de bandas. La versión 0.5.3 añade un único reintento auditable limitado a citas: el escaño original solo puede devolver ids de criterios y `quotes` de reemplazo; `repair_quotes.py` congela todos los campos del dictamen y vuelve a verificar todo. Se prohíben un segundo reintento y cualquier override manual.

`prepare_run.py` acepta `--genre memoir|other` (`memoir` por defecto) y `--readers=N` (1 por defecto). El preset `standard` activa los Escaños 01 a 09 y 11. `--source` satisface la condición de entrada del Escaño 01. `--brief` hace que `standard` añada el Escaño 10 y lo activa cuando `full` o `custom(...)` ya lo selecciona; `quick` no se amplía solo por recibir un brief. La base `quick` es 01, 02, 03 y 08, pero una ejecución de memorias añade automáticamente el Escaño 11 de ética; sin el núcleo literario, su banda literaria formal es N/A. `full` cubre los Escaños 01 a 11 y cualquier source o brief ausente se declara como brecha de cobertura. Excluir explícitamente el Escaño 11 de un `custom(...)` de memorias también genera una advertencia.

El criterio A7 del Escaño 03 es exclusivamente intercapítulos. Solo entra en el paquete cuando `--source` apunta a un directorio que contiene al menos dos archivos de forma recursiva; ninguna source, un solo archivo o un directorio con un archivo no activa A7.

La evaluación a ciegas mutua es una barrera estricta: una revisión formal exige subagentes reales e independientes. Si el host no puede crear contextos aislados, la ejecución se cierra con fallo por defecto. Con autorización explícita del usuario solo puede producir un diagnóstico marcado `degraded=true`; no puede afirmar que hubo evaluación a ciegas.

Cada lector `lit-naive-reader` sigue un protocolo estricto de dos pasos. El paso 1 solo recibe el texto y congela la experiencia natural. El paso 2 puede ser un follow-up en el mismo contexto o un contexto nuevo que reciba el texto sellado del paso 1. Para cada lector, `execution-receipt.json` registra `step_2_mode`, ambos identificadores de contexto y el SHA-256 del paso 1; los lectores permanecen aislados entre sí. La derivación también reconstruye el plan canónico y verifica el SHA-256 de cada paquete despachado; una abstención no puede convertirse silenciosamente en banda A.

`derive_report.py` solo produce `formal=true` cuando se prueban subagentes nativos, `degraded=false`, están completos todos los despachos, salidas y pruebas del Escaño 08, coinciden los digests de entrada y los recibos, y `coverage_gaps=[]`. Toda degradación, despacho fallido o no aislado, artefacto ausente o cita invalidada produce un diagnóstico con `bands.fidelity=null`, `bands.literary=null` y recomendación `仅诊断`. Este `null` diagnóstico es distinto del N/A formal de una dimensión legítimamente fuera de alcance.

## Vista de puntuación siempre disponible con estado de evidencia (0.6.1)

La versión 0.5.2 restauró la fórmula determinista v0.4.1; la versión 0.5.4 separó la disponibilidad de la puntuación de la verificación de citas; la versión 0.5.5 garantiza un total de 0 a 100 cuando la fase 3 genera un informe; la versión 0.6.0 sustituyó la fórmula v0.4.1 por `formula 0.5.0-anchored` para corregir el defecto Base-90 de «sin defecto es excelente»; la versión 0.6.1 sustituye esa fórmula por `formula 0.7.0-full-partition` para corregir una doble penalización que aquella introdujo: los criterios de oficio recibían la bonificación y, si estaban ausentes, también se restaban por el mismo libro de deducciones de la dimensión, así que un texto competente pero llano podía reprobar legítimamente casi la mitad de sus criterios y saturar la puntuación en el suelo. La puntuación ya no se deriva de forma independiente: es una **proyección legible de la banda literaria**. La banda toma la más estricta de dos techos independientes — un techo de oficio (la banda A exige que cada escaño central verifique ≥60 % de su conjunto de oficio; si no, el promedio de los cuatro escaños la limita a B o a «de registro») y un techo de defectos (líneas rojas sin cambios: cualquier problema veto/core limita a B, cualquier veto de alta severidad limita a C) — y esa banda fija una ventana de puntuación; el vector de criterios solo posiciona el texto dentro de ella. Los escaños siguen sin asignar números: solo `derive_report.py` produce `derived-report.json.scores`. Las entradas completas usan `status=verified`; un NA core/extended con un motivo explícito de inaplicabilidad también es un dictamen neutral completo. ABSTAIN, un veto NA, citas inválidas, ejecución degradada o escaños no cubiertos conservan una puntuación mecánica `status=provisional`, con cada límite en `status_reasons`. Las dimensiones ausentes siguen como no evaluadas; cuando la banda literaria es N/A no se aplica la proyección de ventana y el total recae en experiencia lectora, limpieza de IA y luego fidelidad, y si no hay ninguna dimensión utilizable se aplica una base diagnóstica fija de 50.

Sin `--source`, solo la fidelidad queda sin evaluar (`dimensions.fidelity=null`); las demás dimensiones y el total siguen disponibles. Si existe source, una cita de fidelidad incorrecta todavía produce una puntuación de fidelidad provisional desde el dictamen congelado. Las citas invalidadas permanecen excluidas de las bandas formales, las alertas rojas y las revisiones.

La banda literaria fija la ventana de puntuación, y la escalera es una **partición completa de `[0,100]` sin huecos**: `S` `[95,100]`, A/candidata-A `[80,94]`, B (no de registro) `[68,79]`, B (de registro) `[60,67]`, C `[40,59]`, y `0-39` queda reservado para la zona de fallo de fidelidad (producida solo por la banda de fidelidad C). La posición dentro de una banda se normaliza contra el rango alcanzable de esa misma banda, así que cada ventana se usa por completo: la banda A pasó de 3 puntuaciones enteras alcanzables en 0.6 a 15. `S` (canónico) sigue sin producirse a partir del vector de criterios (no puede separar S de A; ambas rondan 87–100 % de oficio); se promueve mediante el canal de comparación anclada: ambos techos en A, **sin alerta de disposición a compartir del lector ingenuo**, y los cuatro escaños centrales situando el texto en «接近S» frente a `band-s.md`. Si falla cualquiera de esas condiciones, la ejecución se queda en A.
La fidelidad se aplica al final: la fidelidad B limita el total a 60 (el suelo de la banda B); la fidelidad C **proyecta** hacia la zona de fallo `[0,39]` en lugar de limitar —un tope produciría un único punto y dejaría sin dueño todo lo que está por debajo. La limpieza de IA, la experiencia lectora y la fidelidad **ya no emiten puntuaciones de 0 a 100**; informan lecturas nativas (hallazgos detectados / lectores y problemas / banda de fidelidad). No están en la escalera de bandas y no son comparables con las cuatro dimensiones literarias. Las calificaciones de la vista 0-100 reutilizan ahora los nombres de banda en lugar de un vocabulario A–D aparte.

## Comandos de una ejecución cerrada

```bash
python3 core/lit-panel/scripts/prepare_run.py text.md \
  --preset standard --genre memoir --readers 1 --output runs/example

# Despachar subagentes nativos y escribir execution-receipt.json; después:
python3 core/lit-panel/scripts/validate_execution_receipt.py runs/example/execution-receipt.json
python3 core/lit-panel/scripts/verify_quotes.py runs/example/seat-outputs runs/example/text.txt \
  --output runs/example/verification-receipt.initial.json \
  --repair-request runs/example/quote-repair-request.json
# Si requests no está vacío, recopilar quote-repair-patches/*.json de los escaños originales y después:
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

Si no hay criterios invalidados, derive desde `seat-outputs` y `verification-receipt.initial.json`. Tras un intento de reparación, use `repaired-seat-outputs` y el `verification-receipt.json` final; el código de salida 1 sigue siendo diagnóstico y nunca debe iniciar un segundo reintento.

Si existe una source, pase el mismo `--source <archivo-o-directorio>` a `verify_quotes.py` y `derive_report.py`. Si existe un brief, pase también el mismo `--brief <archivo>` a `derive_report.py`. Sus cinco argumentos posicionales son salidas de escaños, recibo de verificación, manifest de ejecución, recibo de ejecución y directorio de criterios; la interfaz anterior ya no es válida. Un digest no nulo de source/brief en `run.json` falla de inmediato si falta el argumento correspondiente o cambió su contenido.

## Artefactos de evidencia

Una ejecución cerrada conserva al menos seis clases de artefactos:

- `run.json`, que congela digests de entrada, género, número de lectores, escaños y salidas esperadas;
- `execution-receipt.json`, que prueba aislamiento nativo, despachos, los dos pasos del Escaño 08 y brechas de cobertura;
- un JSON por escaño conforme a `seat-output.schema.json`;
- `verification-receipt.json`, que registra cada coincidencia o invalidación de cita;
- `derived-report.json`, con bandas, `scores` y sus `status/status_reasons`, líneas rojas, revisiones y elementos de arbitraje derivados mecánicamente;
- `report.md`, la crítica formal destinada a personas o una proyección marcada explícitamente como diagnóstico.

Todo dictamen YES/NO exige una cita literal. La validación del esquema y la verificación mecánica preceden a la síntesis; una cita fallida invalida el criterio como evidencia formal, impide el cierre formal de esa ejecución y no puede influir en una banda formal. No borra la vista numérica: el dictamen congelado contribuye a una puntuación provisional claramente señalada. Los escaños no pueden asignar puntuaciones, porcentajes ni pesos libres; solo el script cerrado puede derivar `scores` reproducibles de 0-100 con la fórmula congelada `0.7.0-full-partition`. A/B/C/N/A sigue siendo una vista cualitativa independiente.

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
