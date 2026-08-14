[简体中文](README.md) | [English](README.en.md) | [Français](README.fr.md) | [Español](README.es.md)

# lit-panel (Panel de evaluación literaria)

*An eleven-seat, mutual-blind literary review panel for Chinese memoir / narrative text — a Claude Code / Codex skill.*

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg) ![Version: 0.4.1](https://img.shields.io/badge/version-0.4.1-lightgrey.svg)

Para un mismo texto de memorias o texto narrativo en chino, once escaños de evaluación leen de forma independiente, sin ver las conclusiones de los demás. Una lógica de orquestación basada en reglas explícitas realiza la síntesis: produciendo una asignación de banda, evidencia textual cita por cita y puntuaciones multidimensionales derivadas mecánicamente de un vector de criterios (los escaños de evaluación aplican cero puntuación por sí mismos; las puntuaciones constituyen una vista derivada y no un juicio directo de los escaños).

## Por qué existe

Asignar una puntuación numérica de "7.5 puntos" a un capítulo de memorias puede parecer objetivo, pero en realidad comprime una infinidad de juicios inmensurables en un número falsamente preciso; cambie la formulación de la instrucción o cambie de modelo, y ese número a menudo se desviará sin explicar qué funciona bien en el artículo, qué está mal o quién decidió qué.

Evitar la puntuación numérica no es una preferencia estética, sino una elección fundamentada. Múltiples criterios de este proyecto (la serie TW para los escaños 04/05/06/07/09) están adaptados del **TTCW** (*Torrance Test of Creative Writing*). Cuando el TTCW evalúa la calidad de la escritura creativa, utiliza un conjunto de criterios binarios respondidos punto por punto por escritores profesionales en lugar de una puntuación continua; sus investigaciones originales también probaron el uso de grandes modelos de lenguaje como evaluadores del TTCW, concluyendo que los juicios del modelo con frecuencia no coincidían con los de los escritores profesionales. Las puntuaciones numéricas aplastan silenciosamente este desacuerdo bajo un número aparentemente certero; lit-panel elige preservar las divergencias en lugar de aplanarlas.

La respuesta de lit-panel es abandonar la escala en sí y producir únicamente tres elementos concretos:

- **Criterios** — si un comportamiento textual específico y observable se cumple;
- **Evidencia** — citas textuales que respaldan la determinación, verificadas mecánicamente; cualquier determinación respaldada por una cita no encontrada en el texto queda invalidada de inmediato;
- **Asignación de banda** — clasificación cualitativa en tres niveles A/B/C en lugar de una escala continua.

El producto final del informe es **clasificación por banda (A/B/C) + citas textuales + zona de divergencia + paquete de revisión + tabla de puntuación multidimensional derivada mecánicamente del vector de criterios** (nueva incorporación desde v0.4.0). **Los escaños de evaluación aplican cero puntuación por sí mismos**: el contrato de salida de la sección 3.4 no ha cambiado ni una sola palabra; los escaños no generan ni necesitan ser conscientes de ninguna cifra. Las puntuaciones son una **vista** derivada mediante una fórmula pública a partir del vector de criterios, ejecutable y reproducible en todo el texto (véase `SKILL.md` §5.8). El sistema no se opone a que aparezcan números en el informe en sí, sino a que el modelo informe una cifra **falsamente precisa** basada en impresiones (incapaz de explicar de dónde proviene un "7.5" y que se desvía en cada consulta). Las bandas siguen siendo conclusiones cualitativas y las puntuaciones son otra presentación de la misma evidencia basada en criterios; ambas no se contradicen ni se sustituyen entre sí.

## Mecanismo central

Esta sección es una explicación simplificada del mecanismo orientada a los usuarios. La autoridad de ejecución en tiempo de ejecución completa es `skills/lit-panel/SKILL.md` (la única lógica de orquestación compartida por ambas plataformas de distribución); la especificación de diseño en fase de construcción se encuentra en `docs/DESIGN.md`. En caso de conflicto entre ambos, prevalecerá `SKILL.md`.

### Panel de evaluación de once escaños

| Escaño | Orientación | Condición de activación | Rol de asignación de banda / Permisos especiales |
|---|---|---|---|
| **01** `lit-fidelity` | Basado estrictamente en fuentes: muestreo de claims, etiquetas de cinco estados (SUPPORTED/PERMISSIBLE_INFERENCE/UNSUPPORTED/CONTRADICTED/UNVERIFIABLE) | Cuando se proporciona `--source` | Única fuente de la banda de fidelidad; derecho de veto de línea roja |
| **02** `lit-continuity` | Coherencia interna del texto: coherencia temporal, de personajes, factual y normativa | Siempre | Escaño de evidencia; derecho de veto de línea roja en caso de contradicción confirmada |
| **03** `lit-slop` | Huellas específicas de IA: marcado de tramos frente a biblioteca de patrones, clasificado en leve/grave | Siempre | Escaño de evidencia + características; sin derecho de veto |
| **04** `lit-structure` | Estructura narrativa: escena/resumen, presagio/resolución, disposición de capítulos | Siempre | Escaño principal de la banda literaria |
| **05** `lit-character` | Personajes y psicología: continuidad de motivaciones, tono de diálogo, rechazo al adorno | Siempre | Escaño principal de la banda literaria |
| **06** `lit-prose` | Prosa y ritmo: coherencia de la voz, transiciones, precisión léxica | Siempre | Escaño principal de la banda literaria |
| **07** `lit-resonance` | Resonancia emocional e impacto: procesado vs vivido, rechazo de emociones forzadas | Siempre | Escaño principal de la banda literaria |
| **08** `lit-naive-reader` | Lector ingenuo: sin criterios antes de leer, informe de experiencia pura, comprobación posterior | Siempre (ejecutado estrictamente en dos pasos) | Participa en el juicio sintético, excluido del vector de criterios; evaluación posterior a criterios |
| **09** `lit-originality` | Originalidad y clichés: fórmulas de escritura humana, voz y color individual | Siempre | Dimensión de bonificación (desde v0.4.1 no entra en asignación de banda, problemas degradados a sugerencias de pulido) |
| **10** `lit-brief` | Consigna editorial: cumplimiento de elementos del brief y alcance de metas dramáticas | Cuando el preset incluye el 10 Y se proporciona `--brief` | Excluido de asignación de banda; elementos no alcanzados se convierten en revisiones |
| **11** `lit-ethics` | Ética y alteridad: caracterización unilateral, necesidad de privacidad, dignidad de personas vulnerables | Activado por defecto en memorias (exclusión explícita vía `custom` emitirá una advertencia) | Excluido de asignación de banda; descubrimientos se derivan siempre a arbitraje humano |

**Niveles de presets**: `quick`=01,02,03,08; `standard`=01–09+11 (no incluye el 10; al proporcionar `--brief`, el 10 se incluye automáticamente sin necesidad de usar `custom` explícitamente); `full`=01–11 (si 01/10 no se activan por falta de entrada, se marcarán con un nivel de **advertencia** en la sección "Escaños omitidos y motivos", ya que la intención explícita de full es activar los once escaños); `custom(<lista>)`=selección de números de escaño de la tabla anterior, con sintaxis como `--preset custom(01,03,08)`. Los números deben estar registrados previamente en `registry.md`; de lo contrario, se considerará un error de parámetro y la ejecución se detendrá de inmediato. Los escaños condicionales se omiten automáticamente cuando no se cumplen sus condiciones, indicando la razón en el encabezado del informe.

### Proceso de tres fases

```
Entrada: Texto evaluado + opcional --source (material fuente) / --brief (consigna editorial)
        │
        ▼
Fase Cero · Precomprobación mecánica —— Pasarela de fallo fatal: texto truncado/no concluido → interrupción inmediata, sin abrir escaños;
                      además se realiza extracción de metadatos, determinación de género y verificación mecánica de restricciones del brief
        │
        ▼
Fase Uno · Evaluación paralela a ciegas mutua —— 11 escaños evalúan de forma independiente con sus propios archivos de criterios,
                          sin ver las conclusiones de los demás (el Escaño 08 se ejecuta en 2 pasos: experiencia previa → preguntas posteriores)
        │
        ▼
Fase Dos · Verificación mecánica de citas —— Verificación textual cita por cita de si cada quote proviene exactamente del original;
                          las determinaciones con citas no encontradas quedan invalidadas como nulas (mecanismo de invalidación) ——
                          esta es la línea de defensa contra citas fabricadas que "envenenan" la cadena de evidencia
        │
        ▼
Fase Tres · Síntesis explícita basada en reglas —— Zona de línea roja/vector de criterios/banda/derivación de puntuación/zona de divergencia/
                          zona de arbitraje humano/sugerencias de decisión/paquete de revisión; consolidación mecánica sin rejuicio estético
        │
        ▼
Salida: Informe de evaluación estructurado + archivo complementario de criterios
     (estructura de references/report-template.md + `<report_name>-details.md`)
```

`--stability` añade una ronda de reejecución independiente después de la Fase Tres para comparar la tasa de alternancia a nivel de criterios; `/lit-compare` ejecuta un modo de comparación independiente (véase "Referencia de parámetros"), sin reutilizar la matriz de banda/decisión de la Fase Tres.

### Asignación de banda por criterios en tres niveles

La banda de fidelidad (Escaño 01) y la banda literaria (Escaños 04/05/06/07) determinan su nivel de forma independiente basándose en sus propios conjuntos de criterios, sin fusionarse en una banda global única.

Los criterios de la banda literaria se dividen en tres niveles:

- **veto** — los ≤2 criterios principales más fatales de cada escaño; su incumplimiento representa el colapso estructural de esa dimensión. Por ejemplo, el Escaño 07 (Emoción) selecciona hasta 2 criterios: que las emociones no estén dramatizadas en absoluto y solo sean anunciadas por el narrador / que las emociones estén forzadas dramáticamente hasta la distorsión. El cumplimiento de cualquiera de estos dos extremos simétricos significa que el tratamiento emocional del capítulo ha fallado fundamentalmente. La lista detallada por escaño y los motivos de selección se encuentran en `criteria/CHANGELOG.md` sección v0.2.0.
- **core (principal)** — el resto de criterios de la tabla core de dicho escaño excluyendo los veto.
- **extended (extendido)** — criterios complementarios que no participan en la determinación de banda, pero que se evalúan normalmente y entran en el vector de criterios.

La determinación de banda se realiza por orden de prioridad de arriba a abajo, deteniéndose en la primera coincidencia:

1. Existe una determinación de problema en criterios veto y severity=**HIGH** (alto) → Banda literaria tope **C**;
2. Existe una determinación de problema en criterios veto pero severity=MEDIUM/LOW (medio/bajo) → Máximo hasta **B** (no activa C), y se incluye adicionalmente en la zona de arbitraje humano;
3. No cumple 1 ni 2, pero existe cualquier determinación de problema en criterios core principales → Máximo hasta **B**;
4. Todos los veto+core aprobados → **Candidato Banda A** — candidato no significa confirmación definitiva; aún se requiere leer detenidamente `anchors/band-a.md` para verificar que la textura del texto candidato sea equivalente a las muestras de anclaje; si es claramente inferior, se degrada a B.

**severity no es una decoración descriptiva, sino cuatro interruptores que alteran directamente los resultados mecánicos**:

1. Umbral de banda de fidelidad — solo UNSUPPORTED con severity=HIGH (alto) activa el tope C en la banda de fidelidad; los problemas con severity=LOW (bajo) solo limitan a B;
2. Admisión a la zona de línea roja — solo entran en la zona de línea roja los UNSUPPORTED de Escaño 01 con severity=HIGH (alto) y los NO de "contradicción confirmada" de Escaño 02;
3. Clasificación veto — ante una determinación de problema en el mismo criterio veto, severity=HIGH (alto) limita a C, mientras que severity=MEDIUM/LOW (medio/bajo) solo limita a B y se transfiere a arbitraje humano;
4. Ordenación del paquete de revisión — severity (alto/medio/bajo) es la base para el orden de procesamiento prioritario en las sesiones de revisión, pero no se convierte en puntuaciones numéricas.

### Bonificación por originalidad (Escaño 09, excluida de la asignación de banda)

A partir de v0.4.1, el Escaño 09 (Revisión de originalidad y clichés) sale del sistema de bandas de tres niveles veto/core mencionado anteriormente: no deduce puntos ni limita la banda. El Escaño 09 se evalúa de manera habitual (determinación + citas + opiniones libres sin cambios), pero los resultados de determinación solo impulsan la **bonificación** de la puntuación total. Las reglas mecánicas se detallan en `SKILL.md` §5.8:

- Todos los criterios de aprobación de la serie O (O2/O3/O5/O6) son **completamente** YES y hay cero determinaciones de problemas de la serie O → Puntuación total **+5**;
- Criterios de aprobación ≥3 YES y cero determinaciones de problemas → Puntuación total **+3**;
- Demás casos (incluida cualquier determinación de problema de la serie O) → **+0**, **en ningún caso se deducen puntos**.

Las determinaciones de problemas (como O1 al detectar metáforas trilladas) se degradan a sugerencias de pulido opcionales y entran en las secciones del informe "Problemas y sugerencias de revisión" y "Comentarios individuales de los jurados", sin silenciarse ni afectar la banda. La postura de producto tras este cambio: la originalidad es la guinda del pastel para el género de memorias, no una obligación central — una vivencia personal sencilla pero real sigue siendo una memoria calificada y no debe verse arrastrada en su banda por carecer de novedad literaria (los motivos detallados se encuentran en `criteria/CHANGELOG.md` sección v0.4.1).

### Alarma del lector ingenuo

Cuando todos los criterios veto+core de los cuatro escaños principales de la banda literaria son **completamente aprobados** y deberían producir un Candidato Banda A, se realiza una comprobación adicional: la cuarta pregunta posterior a la lectura del lector ingenuo (Escaño 08) — "¿Estarías dispuesto a relatar este texto a otras personas?" (solo acepta respuestas de "Sí" / "No", sin aceptar respuestas ambiguas como "Depende").

- **N=1**: Responde "Sí" → Candidato Banda A se mantiene normalmente y procede a la verificación con anclajes. Responde "No" → Activa la alarma: **no otorga A automáticamente ni degrada por ello**, y la sugerencia de decisión se reescribe como "**Candidato Banda A (Pendiente de confirmación manual — divergencia entre criterios y percepción del lector)**", transfiriéndose obligatoriamente a la zona de arbitraje humano.
- **N>1**: Prevalece la respuesta de la mayoría de los lectores ("Sí" / "No"); los empates se tratan como respuesta "No" — prefiriendo activar una verificación manual adicional antes que permitir un paso silencioso.
- La alarma solo tiene sentido bajo la premisa de "cero determinaciones de problemas core": si el plano de criterios ya ha limitado la banda a B o C debido a problemas veto/core, la respuesta "No" del lector ingenuo no activará un arbitraje adicional, ya que el problema ha sido capturado por el plano de criterios.

Sustituye al diseño obsoleto de la versión v0.1.1 "Condición de participación positiva del lector ingenuo en Candidato A". El diseño antiguo permitía al lector ingenuo participar directamente en la determinación de A/B/C; en el nuevo diseño, el lector ingenuo no participa en la determinación de banda, sino que actúa como una última verificación de la experiencia del lector cuando los criterios "parecen totalmente aprobados". Si los criterios y la experiencia del lector divergen, se entrega al criterio humano, no a la resolución automática del mecanismo.

### Diseño a ciegas mutua y antisesgo

- **Doble evaluación por inversión de orden (exclusivo de `/lit-compare`)**: En el modo de comparación, cada escaño realiza dos juicios de preferencia sobre A/B: una vez presentado en orden (A,B) y otra en orden invertido (B,A). Si ambas prefieren el mismo texto → se registra la preferencia de dicho escaño; si la preferencia se invierte con el orden de presentación → se registra **TIE** (empate). Este diseño está dedicado a detectar el sesgo de posición donde "la evaluación solo prefiere el orden de presentación". La salida solo proporciona el recuento de distribución, sin convertirse en una puntuación total o ranking ponderado.
- **Aislamiento estructural de rutas paralelas**: Bajo Claude Code, los once escaños son subagentes Task paralelos cuyo contexto está aislado de forma natural; la evaluación a ciegas mutua es una garantía estructural.
- **Declaración explícita de olvido en rutas secuenciales**: Codex no dispone de capacidad paralela. Cuando la sesión principal interpreta sucesivamente cada escaño, debe declarar explícitamente antes de cambiar al siguiente: "La revisión de este escaño termina aquí; descártense todas sus conclusiones". Se utiliza una instrucción clara para que el modelo simule activamente el olvido, ya que en la ejecución secuencial el contexto de conversación es continuo. Esta declaración no es una cortesía, sino la única forma de aplicar la disciplina a ciegas mutua en entornos sin paralelismo (sigue siendo una simulación; véanse los detalles en "Límites conocidos y riesgos").
- **Recomendación de evaluación cruzada interfamiliar**: Si el generador y el evaluador utilizan el mismo modelo o la misma sesión, el campo "Divulgación de modelo y sesión" en el encabezado del informe debe indicarse con veracidad, y se recomienda una evaluación cruzada interfamiliar (por ejemplo, generación por Claude → evaluación por Codex, o viceversa) para reducir el punto ciego homólogo de que "el mismo conjunto de sesgos potenciales escriba y juzgue".
- **Campo de opinión libre**: Cada escaño incluye en su contrato de salida, además de la tabla de criterios, una sección de "opinión libre" (1-3 párrafos de intuición profesional libre de las restricciones de los criterios). Junto con el mecanismo de "sin criterios antes de leer" del lector ingenuo, estas son las únicas dos áreas fuera de la tabla de criterios que no pueden eludirse memorizando preguntas (véase la discusión sobre el riesgo de Goodhart más adelante).

## Instalación

### Claude Code (modo complemento / plugin)

Tres métodos, elija según sus necesidades:

```bash
# Método 1: Copiar manualmente al directorio local de skills (se cargará automáticamente como lit-panel@skills-dir en el próximo inicio de claude)
cp -r /path/to/lit-panel ~/.claude/skills/lit-panel
# También se puede usar un enlace simbólico para facilitar el seguimiento de actualizaciones del repositorio:
ln -s /path/to/lit-panel ~/.claude/skills/lit-panel
```

```bash
# Método 2: Registrar como marketplace local e instalar (permanente, otra ruta oficialmente soportada)
# La raíz de este repositorio ya incluye .claude-plugin/marketplace.json, no requiere creación manual.
claude plugin marketplace add /path/to/lit-panel
claude plugin install lit-panel
```

Probado con éxito en un entorno `HOME` aislado (`HOME=$(mktemp -d) claude plugin marketplace add ...`), donde los dos comandos emiten sucesivamente:

```
✔ Successfully added marketplace: lit-panel (declared in user settings)
✔ Successfully installed plugin: lit-panel@lit-panel (scope: user)
```

`claude plugin details lit-panel` permite confirmar la lista de componentes: 3 skills (`lit-panel`/`lit-review`/`lit-compare`) + 11 agentes, consistente con la estructura del directorio fuente. Si el nombre registrado en su marketplace local difiere del nombre del plugin (por ejemplo, si cambió el campo `name` en `marketplace.json` tras hacer un fork), use `claude plugin marketplace list` para confirmar el nombre registrado e instale con `claude plugin install lit-panel@<nombre_registrado>`.

**Un detalle descubierto en pruebas reales**: Tras la instalación como plugin, el nombre del componente agente listado por `claude plugin details` es el **nombre del archivo** (como `ethics-reviewer`), no el campo `name` del frontmatter del archivo de definición del agente (como `lit-ethics`). La "regla de degradación de despacho" de `SKILL.md` §3.3 está diseñada precisamente para esta situación: si el despacho del subagente Task mediante el nombre del agente de `registry.md` falla, se reintenta utilizando el identificador listado por la plataforma.

```bash
# Método 3: Carga temporal para una sola sesión (sin instalación permanente, adecuado para probar)
claude --plugin-dir /path/to/lit-panel
```

Una vez completada la instalación, los comandos `/lit-review` y `/lit-compare` estarán disponibles de inmediato, y los once escaños de evaluación se programarán en paralelo de forma nativa por Claude Code como subagentes.

### Codex (modo habilidad / skill)

```bash
# Recomendado: Usar script de instalación (detecta instalaciones existentes y pregunta si sobrescribir; por defecto no sobrescribe)
./scripts/install-codex.sh

# O copiar manualmente
cp -r skills/lit-panel ~/.agents/skills/lit-panel
```

**Las nuevas habilidades instaladas no se detectan automáticamente en la sesión actual**: Codex solo escanea el directorio de habilidades al iniciar la sesión; las sesiones abiertas no se vuelven a escanear. Si desea usarlo de inmediato tras la instalación, elija una de las dos rutas: abra una nueva sesión de Codex; o prescinda de la detección automática y ordene a Codex leer `~/.agents/skills/lit-panel/SKILL.md` mediante su ruta absoluta y ejecutar según su contenido.

Codex no tiene el mecanismo nativo de subagentes paralelos de Claude Code, por lo que en Codex la evaluación de los once escaños es orquestada por `SKILL.md` para su **ejecución secuencial escaño por escaño** — la semántica de evaluación a ciegas mutua busca ser equivalente (cada escaño sigue siendo un contexto independiente e invisible a las conclusiones de los demás), pero como se describe más adelante en "Límites conocidos y riesgos", esto es una simulación esforzada, no un aislamiento de contexto real.

## Inicio rápido

```bash
# Evaluación de un solo texto: preset estándar (01–09+11), proporcionando material de entrevista para activar el Escaño 01 (Revisión de fidelidad)
/lit-review capítulo.md --source entrevista.md --preset standard
```

```bash
# Comparación A/B: dos textos de la misma fuente y tarea; los 11 escaños evalúan por defecto en modo comparación, con doble evaluación invertida en cada escaño
/lit-compare a.md b.md
```

Cómo se ve un informe: Un informe de `/lit-review` (reestructurado desde v0.4.0) contiene de forma fija ocho bloques; **los títulos de los bloques no llevan numeración y el orden físico es el orden de lectura**: Resumen general (visión global del jurado sobre el estilo del texto, 2-3 párrafos), Alerta de Línea Roja (aparece solo cuando existe source y se activa, inmediatamente después del resumen general y antes de la tarjeta de puntuación general), Tarjeta de puntuación general (puntuación total/nivel/veredicto de una frase, derivado mecánicamente), Tabla de puntuación multidimensional (cuatro dimensiones literarias + bonificación por originalidad + limpieza de IA + experiencia del lector; se añade fidelidad cuando hay source), Comentarios individuales de los jurados (un párrafo breve por escaño con el tono real del jurado, citas de problemas integradas en la prosa, sin tablas), Problemas y sugerencias de revisión (paquete de revisión original en formato de prosa), Arbitraje humano requerido (aparece solo cuando hay contenido; cada categoría es un elemento narrativo: quién con quién, sus posiciones respectivas y por qué requiere mediación humana; sin tablas de criterios), Archivo de evaluación (versión simplificada de la tabla de encabezado original). La estructura es fija y no se añade ni elimina según la longitud del texto o la cantidad de problemas. Las tablas completas de criterios por escaño, los registros cita por cita de la Fase Dos y la tabla de criterios originales de la zona de arbitraje humano **no se incluyen en el informe principal**, sino que se trasladan al archivo complementario `<report_name>-details.md`, proporcionando un puntero en el archivo de evaluación. La estructura completa se encuentra en `skills/lit-panel/references/report-template.md`. `/lit-compare` sigue una estructura de salida de comparación independiente (preferencia de cada escaño + motivos + distribución total del panel), sin reutilizar este sistema de banda/puntuación/decisión.

## Referencia de parámetros

| Parámetro | Valores | Descripción |
|---|---|---|
| `--preset` | `quick\|standard\|full\|custom(<lista>)` | Determina el alcance de escaños candidatos para esta ronda; por defecto `standard`. Las definiciones de los cuatro niveles se encuentran arriba en "Panel de evaluación de once escaños"; los números de la lista en `custom(<lista>)` deben estar registrados en `registry.md`; los números no registrados provocarán un error y la interrupción inmediata en la precomprobación mecánica. |
| `--source <ruta_fuente>` | Ruta de archivo o directorio | Proporciona materiales fuente como transcripciones de entrevistas. Activa el Escaño 01 (Revisión de fidelidad, única fuente de la banda de fidelidad, con derecho de veto de línea roja). Cuando no se proporciona, la banda de fidelidad registra N/A y se añade una línea de advertencia obligatoria bajo el título del informe. |
| `--brief <ruta_brief>` | Ruta de archivo | Proporciona la consigna editorial/task book. Es una de las condiciones necesarias para activar el Escaño 10 (requiere además que el preset incluya el 10); al mismo tiempo activa el preprocesamiento del brief en la precomprobación mecánica (extracción del propósito dramático central + resumen de tareas dramáticas clave) y la verificación mecánica de restricciones rígidas (rango de palabras/inicio y fin específicos/componentes estructurales/palabras clave prohibidas). |
| `--stability` | Interruptor (sin valor) | Activa la autocomprobación de estabilidad: ejecuta dos rondas completas y silenciosas sobre el mismo texto y configuración (manteniendo la ciegas mutua entre rondas), informando la tasa de alternancia a nivel de criterios agrupada por escaños (sin proporcionar una tasa total única). Este es un resultado adicional independiente del informe oficial y no afecta las sugerencias de decisión. |
| `--readers=N` | Entero positivo, por defecto `1` | Número de instancias de lectores independientes para el Escaño 08 (Lector ingenuo). N lectores son independientes entre sí a ciegas mutua, ejecutando por completo el proceso de dos pasos "sin criterios antes de leer → preguntas posteriores"; el informe enumera por secciones según el número de lector. No tiene relación con la selección de escaños y no acepta números de escaños ni nombres de agentes; para filtrar escaños participantes use siempre `--preset custom(<lista>)`. |
| `--fast-compare` | Interruptor (sin valor), por defecto desactivado | Solo válido para `/lit-compare`. Mantiene la doble evaluación por inversión de orden por defecto; al pasarse, cada escaño evalúa una sola vez (sin invertir orden) + declaración de autocomprobación interna a cambio de velocidad; el encabezado del informe divulga obligatoriamente "Sin doble evaluación invertida, sesgo de posición no protegido". Adecuado para rondas de iteración, no recomendado para rondas de control final (gatekeeping). |

## Rendimiento esperado

A continuación se muestran las referencias de tiempo obtenidas en pruebas reales (no constituyen un compromiso; los tiempos reales dependen de la longitud del texto, el modelo, la red y la limitación de concurrencia):

- **Codex (nivel de inferencia xhigh)**: preset `quick` (4 escaños en ejecución secuencial) aprox. 10 minutos; preset `standard` (10–11 escaños en ejecución secuencial) aprox. 30–45 minutos — en la ruta secuencial cada escaño representa una llamada completa al modelo, y el tiempo crece de forma aproximadamente lineal con el número de escaños activados.
- **Claude Code (subagente paralelo)**: preset `standard` equivale aproximadamente al tiempo del **escaño individual más lento** (5–8 minutos), ya que los once escaños son llamadas Task paralelas simultáneas y el tiempo total está determinado por el escaño más lento, sin acumularse secuencialmente.

**Recomendaciones**:

- Use `quick` en rondas de iteración (modificar un borrador, revisar problemas rápidamente); use `standard` o `full` en rondas de control final (evaluación final antes de la publicación, juicios de entrega formal) — no baje de nivel en rondas de control final para ahorrar tiempo; `quick` ni siquiera contiene ningún escaño principal de la banda literaria y la base del juicio de banda producido es incompleta.
- En la ruta secuencial de Codex, la intensidad de inferencia de los escaños de evaluación se puede ajustar a `medium` en lugar de `xhigh` — la respuesta a las tablas de criterios es una tarea de verificación estructurada punto por punto, no una creación abierta que requiera inferencia de alta intensidad; el nivel medium suele ser suficiente y reduce significativamente el tiempo acumulado de la ejecución secuencial.
- En `--source`, transfiera únicamente transcripciones/materiales directamente relacionados con este capítulo; no introduzca lotes enteros de capítulos no relacionados — la verificación de citas del lado de la fuente (secciones 3.4/4) necesita buscar citas en estos materiales; a mayor volumen de material, más lenta será la verificación y los materiales no relacionados no mejorarán la precisión de la banda de fidelidad.

**Efecto esperado de la optimización de rendimiento en v0.3.0 (estimación, pendiente de verificación real)**: La clasificación por niveles de la obligación de citación añadida en esta versión (la mayoría de determinaciones de aprobación ya no requieren citas obligatorias) y la optimización de pegado único del texto en la ruta secuencial (en Codex el texto se pega solo una vez al inicio de la sesión, sin volver a pegarse escaño por escaño) prevén reducir el tiempo de la ruta secuencial `standard` de Codex de aprox. 30–45 minutos a **15–20 minutos**. Esta es una estimación basada en el ahorro de tokens/llamadas de ambas optimizaciones y aún no ha sido verificada con cronometraje real de extremo a extremo; los números deben actualizarse tras confirmar los datos reales.

## Interpretación del informe

Un informe se ensambla estrictamente según la estructura de `skills/lit-panel/references/report-template.md` (ocho bloques, véase "Inicio rápido" anterior; los títulos de los bloques no llevan numeración y el orden físico es el orden de lectura). A continuación se explica cómo leer cada bloque y de dónde provienen las puntuaciones.

**De dónde provienen las puntuaciones** — Los escaños de evaluación aplican **cero puntuación** de principio a fin: el contrato de salida de la sección 3.4 solo contiene verdict/quote/location/severity/note, sin ningún campo numérico. Cada número en la tarjeta de puntuación general y en la tabla de puntuación multidimensional es **derivado mecánicamente a posteriori** por el orchestrator en la Fase Tres aplicando la fórmula determinista de `SKILL.md` §5.8 sobre el vector de criterios: las cuatro dimensiones literarias (estructura/personajes/lenguaje/emoción) tienen una base de 90 puntos cada una; las determinaciones de problemas en criterios veto se limitan según la gravedad (alto → ≤45, medio/bajo → ≤65); cada determinación de problema en criterios core principales resta −12; cada criterio extended resta −5; las tres dimensiones de limpieza de IA (derivada del Escaño 03), experiencia del lector (derivada de la serie R del lector ingenuo) y fidelidad (tomada de la letra de la banda de fidelidad cuando hay source) tienen fórmulas independientes; Puntuación total = promedio simple de las cuatro dimensiones literarias, superponiendo la corrección del Escaño 03 (−3/criterio, límite −10), **bonificación por originalidad** (nueva en v0.4.1 — si todos los criterios de aprobación de la serie O del Escaño 09 son YES y hay cero problemas → +5; si ≥3 YES y cero problemas → +3; demás con problemas → +0, solo suma sin restar) y el tope de la puntuación total por banda de fidelidad (banda de fidelidad C → puntuación total limitada a 45 y decisión obligatoria de "Sugerencia de reescritura"; banda de fidelidad B → limitada a 75, ambas surtiendo efecto incluso después de las bonificaciones). El texto completo de la fórmula es público y cualquiera puede recalcularlo con el vector de criterios para verificarlo — esta es precisamente la diferencia entre estar "impulsado por evidencia" y "puntuar por impresión": lo que se rechaza no son los números, sino los números cuyo origen es inexplicable. La tarjeta de puntuación general se presenta con un título H2 + negrita (por ejemplo, "## Puntuación total: 45/100 · C"), y todo el informe contiene solo un título H1.

**Significado de las bandas** — Las bandas son dos rutas cualitativas independientes paralelas a las puntuaciones; no se fusionan en una puntuación total ni se deducen a la inversa a partir de puntuaciones:

Banda de fidelidad (basada completamente en la distribución de cinco estados del Escaño 01; cuando no se proporciona `--source` registra N/A y la tabla de puntuación multidimensional no muestra la fila de fidelidad): A = distribución de cinco estados completamente limpia; B = no existen CONTRADICTED ni UNSUPPORTED con severity=HIGH (alto), pero existen problemas con severity=MEDIUM/LOW (medio/bajo), o solo existen PERMISSIBLE_INFERENCE/UNVERIFIABLE sin UNSUPPORTED/CONTRADICTED; C = existe CONTRADICTED o existe UNSUPPORTED con severity=HIGH (alto).

Banda literaria (basada en los criterios veto/core de los Escaños 04/05/06/07; cuando el preset `quick` no incluye ningún escaño principal de la banda literaria, no produce esta banda. La originalidad del Escaño 09 no participa en esta banda a partir de v0.4.1 y pasa a la "Bonificación por originalidad" independiente, véase arriba "Bonificación por originalidad (Escaño 09, excluida de la asignación de banda)"): las reglas de clasificación se encuentran arriba en "Asignación de banda por criterios en tres niveles"; además existe un estado especial — "**Candidato Banda A (Pendiente de confirmación manual — divergencia entre criterios y percepción del lector)**", que es la salida cuando se activa la alarma del lector ingenuo. Si ambas bandas son N/A (por ejemplo, en preset `quick` y sin `--source`), la sugerencia de decisión cambia a "**Solo diagnóstico**", enumerando únicamente las determinaciones de problemas de esta ronda como referencia, sin emitir valores por defecto que simulen una decisión real, y la tarjeta de puntuación general tampoco produce puntuaciones convencionales.

**Alerta de Línea Roja** — Las fuentes son únicamente dos: el Escaño 01 determina CONTRADICTED o UNSUPPORTED con severity=HIGH (alto); el Escaño 02 determina NO de "contradicción confirmada" con severity=HIGH (alto). Cuando existe source y se activa, esta sección aparece después del resumen general y antes de la tarjeta de puntuación general, mostrando citas emparejadas (cita de determinación + cita de fuente/cotejo). Que la zona de línea roja no esté vacía no significa que el informe termine ahí — todos los demás bloques se producen por completo de manera normal y la tarjeta de puntuación general sigue apareciendo normalmente (limitada a 45 cuando la banda de fidelidad es C).

**Cómo se escriben los comentarios individuales de los jurados** — Un párrafo por escaño; los materiales solo pueden provenir de extractos y microediciones de la opinión libre/informe de experiencia de dicho escaño, tejiendo las citas de determinaciones de problemas como citas en la prosa; no se permite que la capa de síntesis agregue ninguna evaluación cuya procedencia no se encuentre en estos materiales — los comentarios son "edición", no "evaluación"; esta regla rígida se encuentra en `SKILL.md` §5.9.

**Arbitraje humano requerido (presentación combinada de zona de divergencia + arbitraje humano, solo aparece cuando hay contenido)** — Esta sección **prohíbe estrictamente las tablas**; cada categoría se redacta como una entrada narrativa: quién con quién, posición de cada uno en una frase, citas en texto con «», y por qué requiere mediación humana (la tabla de criterios originales se traslada a la sección "Tabla detallada de arbitraje humano" en el archivo complementario, proporcionando un puntero al final de esta sección). Divergencia: la coexistencia de "determinación de problema" y "determinación de aprobación" sobre la misma área del texto, o cuando la opinión libre de un escaño se opone explícitamente a las conclusiones de otro, se considera divergencia; **no se promedia, no se pondera, no se juzga quién tiene razón**, y las posiciones de ambas partes se narran juntas de forma paralela para dejar la decisión al juicio humano/editorial. Arbitraje humano: las siguientes categorías de determinaciones nunca se aprobarán ni bloquearán automáticamente:

1. Todas las determinaciones ABSTAIN (incluidas las degradadas a ABSTAIN por "NA sin motivo de aplicabilidad");
2. **Todas** las determinaciones del Escaño 11 (Ética y alteridad), independientemente de su verdict — los descubrimientos éticos no se aprueban ni bloquean automáticamente;
3. Determinaciones invalidadas tras fallar la verificación mecánica de la Fase Dos (con motivo de invalidación, para revisar si fue un falso positivo del verificador);
4. Determinaciones de problemas en criterios veto con severity=MEDIUM/LOW (medio/bajo) (el juicio de gravedad afecta directamente la banda y requiere verificación humana);
5. NA en criterios veto (el NA requiere motivo de aplicabilidad; sin motivo se trata como ABSTAIN y entra en la categoría 1 anterior; los criterios veto tienen consecuencias directas de tope/arbitraje en la banda, y NA significa que falta este nivel de juicio); los NA (con motivo) en criterios core/extended no entran aquí y se presentan normalmente en el archivo complementario sin elevarse a esta sección;
6. Registros de activación de la alarma del lector ingenuo.

Cuando cualquiera de las categorías anteriores esté vacía, la sección completa no aparecerá, sin dejar títulos vacíos de reserva.

**Cómo alimentar los problemas y sugerencias de revisión de vuelta a la sesión de generación** — Consolidación de elementos de la zona de línea roja + todas las "determinaciones de problemas" del vector de criterios; cada elemento = ubicación + cita en prosa + por qué + cómo modificar, ordenados por severity, reutilizando los id de criterios; se pueden pegar directamente como lista de tareas en la siguiente ronda de modificación. Cuando una misma ubicación del texto es alcanzada por múltiples criterios, solo se genera una tarea combinada (severity toma el valor más alto y las sugerencias de modificación se combinan), evitando que la misma ubicación aparezca repetidamente en la lista. **Aviso de revisión humana**: la verificación mecánica solo garantiza que la cita existe realmente en el original, no que respalde la afirmación de dicha determinación — se adjunta una nota al final de esta sección recomendando revisar manualmente cada elemento antes de ejecutarlo.

**Archivo de evaluación y archivo complementario sidecar** — Versión simplificada de la tabla de encabezado original, que incluye el nombre del texto/preset y escaños activados (los escaños omitidos se combinan en una frase)/divulgación de modelo y degradación/estadísticas de verificación/versión de reglas, así como el puntero a la ruta del archivo complementario sidecar. La tabla completa de criterios por escaño + registros de verificación cita por cita de la Fase Dos + tabla de criterios originales de la zona de arbitraje humano ya no se incluyen en el informe principal, sino en el archivo complementario `<report_name>-details.md`, manteniendo el formato de "Resumen de tablas de criterios por escaño" de la versión anterior y añadiendo la sección "Tabla detallada de arbitraje humano". Cuando no se proporciona `--source`, se añade una línea en esta sección: "En esta ronda no se proporcionó --source, no se realizó verificación factual, la puntuación solo refleja la calidad intrínseca del texto" — este es el único lugar donde aparece el descargo de responsabilidad de fidelidad desde v0.4.0, dejando de ser un banner de advertencia obligatorio bajo el título (la propia tarjeta de puntuación general responde a lo mismo con texto pequeño en ausencia de source, siendo ambas suficientes).

## Personalización y extensión

**Los archivos de criterios son editables**: La redacción de cada criterio en `skills/lit-panel/references/criteria/*.md` puede pulirse, pero no se debe cambiar su semántica ni su polaridad (`[Aprobado]`/`[Riesgo]`) — cambiar la semántica equivale a cambiar los estándares de evaluación en sí, lo que requiere seguir el proceso de ampliación de escaños/CHANGELOG descrito a continuación, en lugar de modificar la redacción a voluntad.

**Registro de bajas en CHANGELOG**: Las elecciones, sustituciones y descartes de criterios deben registrarse en `skills/lit-panel/references/criteria/CHANGELOG.md`, una línea por elemento, indicando los motivos. v0.2.0 es un ejemplo de referencia: registra los motivos de selección de los ≤2 criterios veto delimitados por cada uno de los cinco escaños principales de la banda literaria, así como los resultados de auditoría tras leer exhaustivamente los 11 archivos de criterios y revisar par a par si el solapamiento semántico superaba la línea de admisión.

**Criterios privados (patrón `criteria/99-private.md`)**: Todos los archivos de criterios se distribuyen públicamente con el paquete. Si necesita recuperar el efecto de "preguntas de examen ocultas" (criterios adicionales que la parte generadora no pueda conocer de antemano), puede crear su propio `skills/lit-panel/references/criteria/99-private.md` (o nombre similar), añadirlo a su `.gitignore` personal (sin distribuirlo con el repositorio ni incluirlo en el conjunto público de criterios), y montarlo como un nuevo escaño o integrarlo en los archivos de criterios existentes siguiendo los pasos de "Ampliación de escaños" a continuación. Esta es una fortificación opcional para entornos locales; lit-panel no establece previamente ningún contenido de criterios privados.

**Ampliación de escaños (abrir un escaño de evaluación completamente nuevo)**: Conjunto de tres acciones simultáneas e indispensables —

1. Añadir una línea a la "Tabla de escaños" en `registry.md` (archivo de agente / nombre de agente / ruta de archivo de criterios / orientación en una frase / condición de activación / rol en la banda / permisos especiales, 8 columnas sin dejar espacios en blanco);
2. Añadir un nuevo archivo de definición de escaño `agents/*.md`;
3. Añadir el archivo de criterios correspondiente `criteria/*.md`, y registrar las elecciones en CHANGELOG.

Antes de abrir un nuevo escaño se debe superar primero la "Cuádruple regla de admisión" (responde a "si se debe abrir un escaño completo nuevo", no a la calidad del criterio individual):

1. **Modo de lectura independiente** — el enfoque de lectura difiere de los once escaños existentes, no es un subconjunto desgajado de la tabla de criterios de ningún escaño existente;
2. **Solapamiento de criterios <20%** — el objeto de juicio sustancial se solapa menos del 20% con cualquiera de los escaños existentes; si lo supera, debe integrarse en el escaño existente;
3. **Forma de evidencia exclusiva** — capaz de producir formas de evidencia o roles de proceso que otros escaños no pueden proporcionar (como las citas del lado de la fuente del Escaño 01, el proceso de dos pasos del Escaño 08 o el arbitraje humano obligatorio del Escaño 11);
4. **Su eliminación omite un tipo de error** — si se elimina dicho escaño del preset `full`, ¿existe un defecto real que ningún escaño restante pueda capturar? Si la respuesta es "No, otros escaños pueden respaldarlo", no cumple con la admisión.

Solo cuando se cumplen las cuatro reglas se añade un nuevo escaño. Existe una segunda capa de verificación independiente: el **nuevo criterio en sí mismo** (ya sea añadido a un escaño existente o a uno nuevo) debe pasar por la meta-especificación de diseño de criterios (`docs/criteria-pool.md` al final): los cuatro elementos de RaR, las tres reglas de HealthBench, la advertencia de contexto de Antislop y la advertencia de ablación. Las dos capas de verificación regulan dos cuestiones distintas (si se debe abrir un nuevo escaño / si un criterio individual está bien redactado), sin sustituirse entre sí. Los pasos completos se encuentran en `registry.md` "Instrucciones de ampliación de escaños".

## Límites conocidos y riesgos (Zona de transparencia)

Una herramienta con filosofía anti-IA no puede llamarse rigurosa si su propio README evita discutir sus propios riesgos y límites.

**La verificación de citas previene la invención, no que se "usen citas reales para decir falsedades"**: La verificación cita por cita de la Fase Dos solo resuelve un problema: si esta frase aparece realmente en el texto original. Evita la "fabricación de una cita que no existe en absoluto en el original", pero no puede evitar que "la cita exista realmente pero la afirmación/interpretación en la note no sea válida". Esto último no es un problema al alcance de la verificación mecánica, y es asumido por la verificación cruzada de múltiples escaños a ciegas mutua y el arbitraje humano. Quienes utilicen el informe deben saber que esta línea de defensa se detiene aquí: no interprete que "la cita pasó la verificación" significa que "la afirmación de esta determinación sea necesariamente sostenible".

**La evaluación a ciegas mutua en rutas secuenciales es una simulación esforzada, no un aislamiento de contexto**: Bajo Claude Code, los once escaños son subagentes Task paralelos cuyo contexto está aislado naturalmente; la evaluación a ciegas mutua es una garantía estructural. Codex carece de mecanismo de subagentes paralelos y la sesión principal interpreta sucesivamente cada escaño, confiando en "declarar explícitamente descartar las conclusiones del escaño anterior" para simular el efecto de evaluadores humanos que no se comunican — esto es un juego de roles dentro del mismo contexto de conversación, no procesos o sesiones verdaderamente independientes. La semántica busca ser equivalente, pero el mecanismo subyacente difiere; para escenarios con exigencias de rigor extremo en la ciegas mutua, se debe tener en cuenta la existencia de esta diferencia.

**La publicidad de criterios es una espada de doble filo (Ley de Goodhart)**: Todos los archivos de criterios se distribuyen públicamente con el paquete, lo que constituye la base para que la herramienta sea "auditable, revisable y refutable", pero también significa que si los modelos generadores son entrenados o instruidos específicamente para "responder" a estos criterios específicos, en teoría podrían hacer que la tabla de criterios luzca mejor sin mejorar realmente la calidad del texto — una vez que un indicador se convierte en un objetivo de optimización, pierde su valor indicativo. El lector ingenuo (Escaño 08) y los campos de "opinión libre" de cada escaño son superficies naturales de resistencia al entrenamiento específico: el lector ingenuo no ve los criterios en absoluto antes de leer, y la opinión libre no está ligada a los criterios; ninguno de los dos se puede eludir "memorizando preguntas". Para escenarios que requieran mayor resistencia, véase "Criterios privados" más arriba.

**El Escaño 11 no sustituye la autorización previa fuera de campo antes de la publicación**: El Escaño 11 evalúa si la **forma de presentación** interna del texto presenta riesgos éticos (caracterizaciones unilaterales, necesidad de privacidad, atribución errónea, dignidad de los vulnerables), pero no sustituye la verificación de consentimiento/autorización fuera de campo de personas reales. Que la presentación interna sea adecuada no significa que se haya obtenido el consentimiento de publicación de las personas involucradas — este paso aún debe ser completado por humanos de forma independiente fuera del texto.

**Los juicios literarios de los LLM tienen un techo; el panel reduce la varianza, no sustituye la revisión final**: Lo que la evaluación a ciegas mutua de once escaños + verificación mecánica + síntesis explícita basada en reglas puede lograr es reducir la arbitrariedad subjetiva y los sesgos puntuales del "puntuar al azar", haciendo que las determinaciones sean revisables, cuestionables y refutables. Lo que no puede hacer es sustituir el juicio final de editores o críticos humanos — la zona de divergencia conserva intencionadamente el hecho de que "los escaños de evaluación también pueden estar en desacuerdo entre sí", sin intentar aplanar las divergencias mediante reglas de síntesis más complejas para simular una conclusión falsamente unánime.

### Límites de verificación (hasta v0.4.1)

Los siguientes mecanismos **cuentan con evidencia de ejecución en máquinas reales** (al menos se han ejecutado por completo una vez en evaluación y conservan registros): distribución a ciegas mutua (tanto la ruta de subagentes Task paralelos de Claude Code como la ruta de simulación secuencial de Codex se han ejecutado); verificación cita por cita + invalidación por manipulación (se volvió a ejecutar la verificación tras alterar una cita, confirmando que la canalización de verificación bloquea citas fabricadas y no es una mera autodeclaración); ensamblaje de informes de los dos presets `quick`/`standard`; evaluación cruzada interfamiliar/multi-familia (ejecutando la evaluación con diferentes familias de modelos, con cero desviaciones en todo el proceso); **cadena completa de fidelidad** (verificación final de reglas v0.2.1: verificación archivo por archivo del directorio `--source`, etiquetas de cinco estados, CONTRADICTED activando la zona de línea roja y la banda de fidelidad C, producción en la matriz de "Sugerencia de reescritura" — en esta ronda el escaño de fidelidad detectó falsedades estructurales en el texto evaluado, con un acierto de 7/7 en citas de la fuente); **banda de tres niveles veto** (rama de gravedad en criterios veto → "máximo B + revisión manual" probada con éxito, frente a la sobre-eliminación de la regla antigua donde un solo criterio core provocaba el tope C); **reglas NA** (cuando falta la premisa del criterio principal, NA incluye motivo, sin limitar mecánicamente la banda); **contrato de contenido de note con doble cita** (89/89 verificaciones con cero invalidaciones y cero violaciones de formato, desapareciendo por completo las citas yuxtapuestas con «/» de versiones antiguas); **protocolo de gestión de desconexiones** (los diez escaños retornaron todos, frente a rondas antiguas con un escaño desconectado permanentemente); proceso de dos pasos del lector ingenuo y recolección de preguntas adicionales.

Los siguientes mecanismos **aún no han sido verificados mediante ejecución de extremo a extremo en máquinas reales**: la rama "bloqueo de A" de la alarma del lector ingenuo y la verificación con anclajes del Candidato A (la accesibilidad de las reglas de ambos se ha confirmado, pero se requiere un texto que alcance el Candidato A para activarse realmente — hasta la fecha ningún texto evaluado ha alcanzado esa rama); Escaño 10 (Revisión de la consigna editorial, requiere `--brief`); autocomprobación de estabilidad `--stability`; modo de comparación `/lit-compare` (incluido `--fast-compare`); agregación multilector con valores de `--readers` mayores a 1; la programación paralela nativa **tras la instalación como plugin de Claude Code** (la cadena de instalación del marketplace se ha probado en máquinas reales emitiendo la lista de componentes correcta, pero no se ha verificado el inicio de una evaluación paralela real tras la instalación); las **mejoras de tiempo proyectadas** por la clasificación por niveles de la obligación de citación y el pegado único del texto en la ruta secuencial introducidos en v0.3.0 (las cifras de v0.3.0 en la sección de rendimiento esperado de este README son estimaciones); así como la **reestructuración del informe v0.4.0 y la capa de derivación de puntuaciones en su conjunto** (la fórmula de §5.8 se ha recalculado a mano utilizando datos históricos de máquinas reales — ronda de verificación final zhang-ch01 v0.2.1 —, confirmando que la fórmula es calculable y reproducible, y `tests/runs/zhang-ch01-v040-format-sample.md` es la muestra procesada de dicho recalculado; sin embargo, la fórmula aún no ha sido llamada por el orchestrator en una evaluación de extremo a extremo real — el recalculado manual no equivale a la ejecución en máquinas reales, existiendo diferencias en la fuerza de la evidencia); y el **sistema de bonificación por originalidad v0.4.1** (el cambio semántico por el que el Escaño 09 sale de veto/banda y pasa a ser puramente de bonificación) tampoco se ha vuelto a probar en máquinas reales — los datos históricos en `tests/runs/` provienen de capturas de reglas anteriores a v0.4.1, y las muestras de esta versión también han sido recalculadas a mano aplicando las nuevas fórmulas a datos antiguos en lugar de una evaluación de extremo a extremo ejecutada con las nuevas reglas; se debe ejecutar una prueba en máquina real lo antes posible tras el lanzamiento oficial.

Esta lista se actualizará con futuras pruebas en máquinas reales — antes de que estos mecanismos sean verificados, considérelos como "consistentes en diseño, aún no demostrados empíricamente", y no como "verificados y fiables".

## Privacidad

- Todos los archivos dentro de `skills/lit-panel/references/anchors/` (muestras de referencia para los niveles A/B/C) son **textos puramente sintéticos**, sin contener información sobre personas reales.
- El texto y los materiales que envíe para su evaluación (`--source`/`--brief`) solo circulan entre su sesión local de Claude Code / Codex y sus respectivas API de modelos; lit-panel no introduce ninguna ruta de transmisión de red, recolección o envío externo aparte de las "llamadas de modelo necesarias para ejecutar la evaluación".
- **Recomendación de sesiones separadas para generación y evaluación**: No pida al modelo que redacte un borrador y luego evalúe su propio escrito en la misma conversación — la autoevaluación del lado de la generación no es el valor real de la evaluación, y el campo "Divulgación de modelo y sesión" en el encabezado del informe lo registrará con veracidad. Si es posible, se recomienda una evaluación cruzada interfamiliar (por ejemplo, generación por Claude → evaluación por Codex, o viceversa) para reducir el punto ciego de origen homólogo donde el mismo conjunto de sesgos potenciales escribe y juzga.

## Orígenes metodológicos y agradecimientos

Los criterios no se escribieron de la nada. Cada criterio lleva una etiqueta de procedencia ([Verificado] / [Adaptado] / [Pendiente de confirmación de segunda mano] / [Propio]); la lista completa de procedencia punto por punto se encuentra en `docs/criteria-pool.md`; aquí solo se enumeran las fuentes principales de las que más se ha nutrido este sistema de criterios:

- **TTCW** (*Torrance Test of Creative Writing*) — Fuente de adaptación directa para toda una serie de criterios TW sobre ritmo narrativo, equilibrio entre escena/resumen, naturalidad del final, razonabilidad de los giros, complejidad de personajes, flexibilidad emocional, complejidad retórica, etc., distribuidos principalmente en los Escaños 04/05/06/07/09; además, TW5 ("los elementos de la historia se combinan para formar un todo unificado, comprensible y satisfactorio") se integra en el Escaño 02 (Revisión de coherencia interna) como criterio de cierre para la coherencia global.
- **ConStory** — Clasificación principal de conflictos fácticos/de coherencia para la revisión de fidelidad y coherencia interna (confusión de nombres, conflictos cuantitativos, conflictos temporales, conflictos de simultaneidad, conflictos de memoria, conflictos geográficos, violaciones de normas sociales, etc.), constituyendo la mayor fuente de criterios para ambos escaños.
- **Measuring AI Slop** (en combinación con el método de vocabulario Antislop) — Marco de clasificación de tres temas y once dimensiones para el Escaño 03 (Detector de huellas de IA en chino) (densidad/patrones/repetición/lenguaje no natural/redundancia/uso inadecuado de vocabulario/tono y registro), así como la fuente metodológica de la regla "la coincidencia en el vocabulario no significa error; el juicio debe pasar por el análisis de contexto".
- **EssayBench** — Fuente de un gran número de criterios sobre técnicas de escritura narrativa en los escaños de estructura, personajes, lenguaje y emoción (selección de material, niveles, caracterización de personajes, descripción de ambientes, configuración de párrafos, etc.).
- **HANNA** — Fuente de criterios de alto anclaje sobre el sentido de participación y la imprevisibilidad en el escaño del lector ingenuo.
- **HealthBench** — Fuente metodológica para las tres reglas de diseño de criterios (un criterio comprueba solo un comportamiento observable; las enumeraciones tras "por ejemplo" no son exhaustivas; los criterios de riesgo juzgan si aparece un mal fenómeno).
- **RaR** — Fuente metodológica para los cuatro elementos del diseño de criterios (base en guía de expertos, cobertura de modos de fallo comunes, estratificación veto/core/extended prohibiendo pesos numéricos, cada criterio es autosuficiente y respondible de forma independiente).

Además, AlignBench, EQ-bench, factool, lechmazur y los criterios de puntuación de redacción del examen de admisión a la universidad (Gaokao) están dispersos en criterios individuales de varios escaños; la lista completa se rige por `docs/criteria-pool.md`.

**Agradecimientos especiales**: En el diccionario de evidencia para los criterios del Escaño 03 `slop-patterns-zh.md`, la sistematización de patrones con huellas de IA en chino tomó como referencia las ideas de clasificación pública de **shuorenhua** (Licencia MIT, proyecto de código abierto para la detección de huellas de IA en chino) y **speak-human-tw** — las frases de ejemplo han sido redactadas nuevamente adaptándolas al registro de memorias e historia oral, sin copiar textualmente ningún vocabulario ni hacer correspondencias biunívocas con entradas específicas.

## Licencia

MIT © 2026 Anamnese Project — véase [`LICENSE`](./LICENSE).
