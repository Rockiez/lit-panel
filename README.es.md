[简体中文](README.md) | [English](README.en.md) | [Français](README.fr.md) | [Español](README.es.md)

# lit-panel: Sistema de evaluación literaria por comité a ciegas mutua para narrativa y memorias en chino basado en la deconstrucción narratológica

*An eleven-seat, mutual-blind literary review panel for Chinese memoir / narrative text — a Claude Code / Codex / Google Antigravity skill.*

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg) ![Version: 0.4.1](https://img.shields.io/badge/version-0.4.1-lightgrey.svg)

> **[Resumen]** Frente a los dilemas epistemológicos de la puntuación escalar continua pseudoprecisa, la homogeneización estética y las citas alucinadas prevalentes en los grandes modelos de lenguaje (LLM) durante la crítica literaria y la evaluación narrativa, este estudio presenta `lit-panel`, un sistema multiagente de evaluación por pares a ciegas mutua diseñado específicamente para memorias y narrativa de no ficción en lengua china. Fundamentado en la narratología clásica y el marco de criterios binarios del Test de Escritura Creativa de Torrance (TTCW), el sistema articula un espacio de evaluación independiente de once escaños que abarca la fidelidad a las fuentes, la coherencia interna, los rastros de generación artificial (AI slop), la arquitectura narrativa, la psicología de personajes, el ritmo prosódico, la resonancia afectiva, la percepción fenomenológica del lector ingenuo, la originalidad, el cumplimiento del mandato editorial y la ética narrativa. Operando en entornos de ejecución físicamente aislados y estrictamente estancos, los escaños realizan lecturas paralelas, depuran afirmaciones falsas mediante verificación textual literal mecánica y sintetizan asignaciones de bandas cualitativas (A/B/C) junto con puntuaciones multidimensionales reproducibles derivadas de reglas formales deterministas. Los análisis teóricos y empíricos demuestran que esta arquitectura elimina de forma efectiva la deriva estocástica de las puntuaciones, preservando al mismo tiempo las tensiones intrínsecas y la inconmensurabilidad de la estética literaria.
>
> **[Palabras clave]** Narratología; Crítica literaria; Evaluación por pares; Doble ciego; TTCW; Humanidades digitales; Crítica de la falsa precisión

## 1. Introducción: Dilema epistemológico y crítica de las escalas cuantitativas continuas

En la crítica literaria computacional y la evaluación de la calidad textual, asignar una puntuación escalar continua como "7.5/10" a un capítulo de memorias o a un ensayo narrativo mantiene en apariencia una fachada de objetividad cuantitativa. En rigor, sucumbe a la ilusión epistemológica de colapsar juicios estéticos plurales e inconmensurables en una cifra escalar arbitraria. Dichas calificaciones numéricas no solo manifiestan una notable deriva estadística ante leves variaciones en las instrucciones o actualizaciones de los modelos, sino que ocultan las tensiones internas entre la estructura formal, la autenticidad vocal y la honestidad emocional del texto.

Renunciar a las escalas numéricas continuas no constituye una preferencia estética subjetiva, sino una elección metodológica sustentada en evidencia. Múltiples criterios fundamentales de este sistema (la serie TW en los Escaños 04, 05, 06, 07 y 09) provienen del marco teórico del **TTCW** (*Torrance Test of Creative Writing*). Al evaluar la creatividad narrativa, el TTCW emplea explícitamente criterios discretos binarios respondidos punto por punto por escritores profesionales en lugar de métricas continuas; sus investigaciones fundacionales evidenciaron un desacoplamiento estructural profundo entre las puntuaciones continuas generadas por LLM y los juicios cualitativos de escritores expertos. Las puntuaciones continuas aplanan silenciosamente esta divergencia; `lit-panel` opta por preservar formalmente las tensiones estéticas y el disenso crítico.

Al desestimar la falsa precisión del cálculo directo, el sistema establece tres entregables concretos y verificables:

- **Criterios discretos**: Verificar si comportamientos textuales específicos y observables así como cualidades estéticas se cumplen de manera efectiva;
- **Evidencia textual literal**: Respaldar cada dictamen mediante citas textuales verificadas mecánicamente; cualquier cita no localizada o inventada invalida de inmediato la afirmación correspondiente, impidiendo la contaminación de la cadena probatoria;
- **Bandas cualitativas**: Proveer una categorización cualitativa A/B/C en lugar de escalas continuas engañosas.

El informe final de evaluación integra **Bandas cualitativas (A/B/C) + Citas textuales literales + Zona de divergencia preservada + Paquete de directivas de revisión + Tabla de puntuación multidimensional derivada mecánicamente de un vector de criterios** (incorporada en v0.4.0+). **Los escaños de evaluación aplican una estricta disciplina de cero puntuación** (contrato de salida de la sección 3.4): emiten exclusivamente dictámenes discretos y citas textuales sin generar ni percibir cifras; las puntuaciones son únicamente proyecciones algebraicas deterministas y públicas del vector de criterios (véase `SKILL.md` §5.8), asegurando una transparencia y reproducibilidad totales.

## 2. Marco teórico y mecanismos de evaluación por pares de once escaños

Esta sección detalla los mecanismos formales de evaluación para investigadores y profesionales. La autoridad normativa en tiempo de ejecución es `skills/lit-panel/SKILL.md` (lógica de orquestación unificada compartida entre plataformas); las especificaciones de diseño residen en `docs/DESIGN.md`. En caso de discrepancia, prevalecerá `SKILL.md`.

### 2.1 Arquitectura del panel de evaluación de once escaños y deconstrucción narratológica

| Identificador del escaño | Dominio de crítica teórica & Objeto de examen | Condición de activación | Rol en la banda & Atributos de autoridad |
|---|---|---|---|
| **01** `lit-fidelity` | Fidelidad a fuentes: cotejo de afirmaciones frente a fuentes históricas, etiquetas de cinco estados (SUPPORTED/PERMISSIBLE_INFERENCE/UNSUPPORTED/CONTRADICTED/UNVERIFIABLE) | Si se aporta `--source` | Determinante único de la banda de fidelidad; Derecho de veto de línea roja |
| **02** `lit-continuity` | Coherencia interna del texto: temporalidad, identidad de personajes, hechos y normas del universo textual | Siempre activo | Escaño de evidencia fundamental; Derecho de veto de línea roja ante contradicciones confirmadas |
| **03** `lit-slop` | Detección de huellas artificiales: etiquetado de fragmentos según léxicos de patrones multidimensionales (AI slop leve/grave) | Siempre activo | Extracción de evidencia y rasgos; Sin derecho de veto independiente |
| **04** `lit-structure` | Estructura narratológica: anacronías genettianas, equilibrio entre escena y resumen, anticipaciones y resoluciones | Siempre activo | Escaño deliberativo central de la banda literaria |
| **05** `lit-character` | Caracterización y agencia: continuidad motivacional, registros dialógicos vivos, rechazo al blanqueamiento moral | Siempre activo | Escaño deliberativo central de la banda literaria |
| **06** `lit-prose` | Estilística y ritmo de la prosa: pureza de la voz narrativa, transiciones sintácticas, precisión sensorial | Siempre activo | Escaño deliberativo central de la banda literaria |
| **07** `lit-resonance` | Resonancia y autenticidad afectiva: emoción intelectualizada (*processed*) vs. experiencia vivida (*lived*), rechazo al sentimentalismo forzado | Siempre activo | Escaño deliberativo central de la banda literaria |
| **08** `lit-naive-reader` | Percepción fenomenológica del lector ingenuo: prueba a ciegas sin criterios previos, reacción pura y seguimiento posterior | Siempre activo (protocolo estricto en 2 pasos) | Participa en el arbitraje final; Excluido del vector de criterios base |
| **09** `lit-originality` | Originalidad y desfamiliarización: examen de clichés narrativos, singularidad de la voz biográfica | Siempre activo | Dimensión de bonificación estrictamente positiva (sin deducción ni tope de banda) |
| **10** `lit-brief` | Conformidad con el mandato editorial: transmisión de la intención dramática, cumplimiento de pautas del encargo | Preajuste incluye 10 & `--brief` aportado | Excluido de la banda base; Desviaciones convertidas en directivas de revisión |
| **11** `lit-ethics` | Ética narrativa: protección ante narración unilateral lesiva, necesidad de privacidad, dignidad de sujetos vulnerables | Activo por defecto (aviso si se excluye) | Excluido de la banda base; Riesgos éticos remitidos sistemáticamente al arbitraje humano |

**Preajustes de evaluación**: `quick`=01,02,03,08; `standard`=01–09+11 (configuración predeterminada, excluyendo 10; activa automáticamente 10 si se proporciona `--brief`); `full`=01–11 (registra una advertencia si 01/10 se omiten por falta de datos); `custom(<lista>)`=selección explícita de escaños, ej. `--preset custom(01,03,08)`. Cualquier identificador no registrado detiene la ejecución de inmediato.

### 2.2 Protocolo de evaluación basado en evidencia en tres etapas (Preverificación, A ciegas mutua, Verificación, Síntesis)

```
Flujo de entrada: Texto objeto + Opcional --source (Materiales fuente) / --brief (Mandato editorial)
        │
        ▼
Etapa 0 · Preverificación mecánica —— Barrera de interrupción: detección de truncamiento o texto inacabado (detención inmediata);
                                      Depuración de metadatos, validación de género, verificación de restricciones del mandato
        │
        ▼
Etapa 1 · Evaluación paralela a ciegas mutua —— 11 escaños leen de forma autónoma en contextos aislados,
                                                aplicando sus criterios específicos (Escaño 08: protocolo estricto en 2 fases)
        │
        ▼
Etapa 2 · Verificación textual de citas —— Cotejo mecánico de fragmentos textuales citados;
                                          Citas no halladas invalidadas de inmediato (cortafuegos antialucinación)
        │
        ▼
Etapa 3 · Síntesis determinista por reglas —— Alarmas de línea roja / vectores de criterios / bandas cualitativas /
                                             puntuaciones derivadas / zonas de discrepancia / arbitraje humano / plan de revisión
        │
        ▼
Salida: Informe de evaluación académica estructurado + Registro anexo de evidencias
        (esquema references/report-template.md + `<nombre_informe>-details.md`)
```

### 2.3 Estratificación cualitativa por bandas y gobernanza por veto

El sistema mantiene dos trayectorias cualitativas independientes: la **Banda de fidelidad (Escaño 01)** y la **Banda literaria (Escaños 04/05/06/07)**. Ambas vías se evalúan en paralelo y nunca se fusionan en una métrica única.

Los criterios de la banda literaria se estructuran en tres niveles formales:
- **Criterios de veto (veto)**: Hasta 2 criterios críticos por escaño central (por ej. el Escaño 07 califica tanto la ausencia total de dramatización emocional como la exageración melodramática forzada como condiciones simétricas de veto).
- **Criterios centrales estándar (core)**: Criterios estéticos regulares.
- **Criterios extendidos (extended)**: Elementos diagnósticos de apoyo, registrados en el vector de criterios sin condicionar el acceso a las bandas.

Algoritmo de asignación de bandas (prioridad descendente, concluye en el primer criterio activado):
1. Presencia de fallo en criterio veto con gravedad `severity=高` (alta) $\rightarrow$ Banda literaria topada en **C** (requiere reescritura sustancial);
2. Presencia de fallo en criterio veto con gravedad `severity=中/低` (media/baja) $\rightarrow$ Banda literaria topada en **B**, con remisión obligatoria a arbitraje humano;
3. Sin fallos de veto, pero con $\ge 1$ fallo en criterio central estándar $\rightarrow$ Banda literaria topada en **B**;
4. Todos los criterios veto y centrales superados $\rightarrow$ Concesión del estatus de **Candidato a Banda A** (sujeto a ratificación de textura frente a `anchors/band-a.md`).

**La gravedad actúa como cuatro interruptores deterministas**:
1. Umbral de banda de fidelidad: Solo el estado UNSUPPORTED de alta gravedad activa el tope en banda C;
2. Acceso a zona roja: Las contradicciones factuales graves se canalizan a las alarmas de línea roja;
3. Desvío de veto: Distingue el bloqueo en C de la revisión humana en B;
4. Orden de revisiones: Define la jerarquía del paquete de revisiones.

### 2.4 Sistema de bonificación por originalidad (Incentivo positivo no punitivo)

Desde la versión v0.4.1, el Escaño 09 (`lit-originality`) se desvinculó del régimen punitivo de veto y topes. La postura crítica fundamental es nítida: **en las memorias y la narrativa testimonial, la originalidad creativa constituye un mérito extraordinario y no una obligación moral primaria**. Un testimonio biográfico sobrio y verídico no debe sufrir degradación por ausencia de audacia formal. Los resultados del Escaño 09 modulan la puntuación global según las siguientes reglas (véase `SKILL.md` §5.8):
- Todos los criterios positivos de originalidad (O2/O3/O5/O6) **aprobados** sin observaciones negativas $\rightarrow$ **+5 puntos** a la puntuación total;
- Al menos 3 criterios positivos aprobados sin observaciones negativas $\rightarrow$ **+3 puntos**;
- Cualquier otra configuración $\rightarrow$ **+0 puntos** (mecanismo estrictamente no deductivo). Las observaciones negativas se integran en el plan de revisión como sugerencias de pulido estilístico.

### 2.5 Percepción fenomenológica del lector ingenuo y mecanismo de alarma

Para evitar que la evaluación por criterios degenere en formalismo burocrático, el sistema incorpora el Escaño 08 (`lit-naive-reader`) como salvaguarda fenomenológica. Cuando todos los criterios literarios son superados y el texto califica como Candidato a Banda A, el sistema activa la pregunta posterior del lector ingenuo: *«¿Estaría sinceramente dispuesto/a a contar o recomendar esta historia a otra persona?»* (opción binaria estricta: Sí / No).

- **Muestra $N=1$**: Si responde "No", el sistema **no otorga la Banda A ni degrada automáticamente el texto a Banda B**. El dictamen se formula como *«**Candidato a Banda A (Pendiente de arbitraje humano — Discrepancia entre criterios formales y experiencia del lector)**»*, suspendiendo la validación automática.
- **Muestra $N>1$**: Se rige por mayoría simple; los empates activan de forma conservadora el arbitraje humano.

### 2.6 Aislamiento a ciegas mutua y diseño experimental antisesgo de posición

- **Doble evaluación con inversión de orden (exclusivo de `/lit-compare`)**: En evaluaciones comparativas de textos emparejados, cada escaño revisa el par dos veces: una en orden (A,B) y otra en orden (B,A). Solo se consolida una preferencia si se elige el mismo texto en ambas presentaciones; una inversión registra un **TIE** (empate), neutralizando el sesgo de posición.
- **Aislamiento contextual físico (Google Antigravity / Claude Code)**: En Google Antigravity, los escaños se instancian en paralelo mediante `invoke_subagent`; en Claude Code, a través de herramientas Task independientes. La ausencia de memoria compartida garantiza estructuralmente la evaluación a ciegas mutua.
- **Simulación de reinicio de estado (Modo secuencial en Codex)**: En la ejecución secuencial de Codex, el orquestador inyecta explícitamente instrucciones de borrado de contexto entre escaños para simular la disciplina de incomunicación.
- **Evaluación cruzada entre familias de modelos**: Los modelos generadores y los agentes evaluadores deben pertenecer a familias arquitectónicas distintas (ej. generación Claude $\rightarrow$ evaluación Codex / Gemini) para erradicar sesgos de complacencia endógenos.
- **Campo de opinión crítica libre**: Cada escaño redacta de 1 a 3 párrafos de reflexión crítica no restringida que, junto a la prueba previa del lector ingenuo, conforma una defensa sólida contra la optimización artificial de métricas (Ley de Goodhart).

## 3. Entorno experimental e instalación del sistema

### 3.1 Despliegue en Google Antigravity y concurrencia nativa

```bash
# Recomendado: Utilizar script de instalación global (~/.gemini/config/skills/lit-panel)
./scripts/install-antigravity.sh

# O instalar en el espacio de trabajo local (.agents/skills/lit-panel)
./scripts/install-antigravity.sh --workspace
```

Antigravity detecta automáticamente la habilidad. Inicie la evaluación en cualquier sesión con `/lit-review <ruta_texto>`. El sistema instancia simultáneamente 11 subagentes de razonamiento intermedio (`Model: "flash"`) en entornos de solo lectura, ejecutando revisiones aisladas y gestionando la consulta en dos fases del Escaño 08 mediante `send_message`.

### 3.2 Despliegue de extensión en Claude Code y orquestación paralela de tareas

Modalidades de instalación admitidas:

```bash
# Método 1: Enlace simbólico en el directorio local de skills (recomendado para desarrollo)
ln -s /path/to/lit-panel ~/.claude/skills/lit-panel
# O copia íntegra: cp -r /path/to/lit-panel ~/.claude/skills/lit-panel
```

```bash
# Método 2: Registro en marketplace local (la raíz del repo contiene .claude-plugin/marketplace.json)
claude plugin marketplace add /path/to/lit-panel
claude plugin install lit-panel
```

Salida de verificación en terminal:
```
✔ Successfully added marketplace: lit-panel (declared in user settings)
✔ Successfully installed plugin: lit-panel@lit-panel (scope: user)
```

```bash
# Método 3: Depuración temporal en sesión única
claude --plugin-dir /path/to/lit-panel
```

### 3.3 Evaluación secuencial en Codex y simulación de reinicio de estado

```bash
# Recomendado: Ejecutar script de instalación idempotente
./scripts/install-codex.sh

# O copiar manualmente al registro global de Codex
cp -r skills/lit-panel ~/.agents/skills/lit-panel
```

En una sesión limpia de Codex, cargue mediante ruta absoluta o detección automática. Los 11 escaños se ejecutarán en secuencia con simulación de reinicio de estado.

## 4. Guía de inicio rápido y paradigmas de invocación

```bash
# Evaluación de texto individual: Preajuste estándar (01–09+11) con fuentes primarias para el Escaño 01
/lit-review capitulo.md --source entrevista.md --preset standard
```

```bash
# Evaluación comparativa A/B a ciegas: Dos versiones con doble evaluación permutada
/lit-compare a.md b.md
```

**Esquema estandarizado del informe académico**: Un informe `/lit-review` mantiene una secuencia invariable de ocho secciones (encabezados sin numerar): **Síntesis del jurado (2–3 párrafos) $\rightarrow$ Alarmas de línea roja (preceden al panel de puntuación si se activan) $\rightarrow$ Panel de puntuación derivada (Total/Grado/Veredicto) $\rightarrow$ Tabla de puntuación multidimensional (4D literaria + Bonificación originalidad + Limpieza IA + Experiencia lector + Fidelidad) $\rightarrow$ Comentarios críticos razonados (prosa crítica con citas textuales insertadas) $\rightarrow$ Directivas de revisión y problemas $\rightarrow$ Zona de arbitraje humano (discrepancias en prosa pura, sin tablas) $\rightarrow$ Archivo de metadatos**. Todos los vectores de criterios y registros de verificación se conservan en el archivo anexo `<nombre_informe>-details.md`.

## 5. Definiciones formales de parámetros

| Parámetro CLI | Dominio / Formato | Función académica & Especificación semántica |
|---|---|---|
| `--preset` | `quick\|standard\|full\|custom(<lista>)` | Define la selección de escaños; por defecto `standard`. `custom(<lista>)` exige identificadores válidos registrados en `registry.md`. |
| `--source <ruta>` | Archivo o directorio | Vincula materiales fuente primarios (ej. transcripciones de testimonios). Activa la auditoría de fidelidad del Escaño 01; si se omite, se registra N/A con aviso explícito. |
| `--brief <ruta>` | Archivo | Vincula el encargo de escritura o escaleta dramática. Activa el Escaño 10 y valida restricciones formales en la Etapa 0. |
| `--stability` | Bandera booleana (sin valor) | Ejecuta una prueba de estabilidad y reproducibilidad: realiza dos pasadas silenciosas independientes y calcula la tasa de inversión de criterios. |
| `--readers=N` | Entero positivo, defecto `1` | Tamaño muestral de lectores independientes para el Escaño 08. Cada lector ejecuta el protocolo en dos fases para medir la dispersión de respuestas. |
| `--fast-compare` | Bandera booleana, defecto desactivado | Específico de `/lit-compare`. Omite la doble evaluación permutada para respuesta rápida; muestra advertencia de sesgo de posición no mitigado. |

## 6. Evaluación de rendimiento y complejidad computacional

Perfiles de ejecución observados según el entorno de cómputo:

- **Modo secuencial en Codex (razonamiento medio/alto)**: El preajuste `quick` requiere $\approx 10$ minutos; `standard` (10–11 escaños consecutivos) requiere $\approx 15\text{--}30$ minutos, escalando linealmente $O(N)$ con el número de escaños activos.
- **Modo concurrente en Antigravity / Claude Code**: La duración de `standard` está acotada por el **escaño individual más lento** ($\approx 5\text{--}8$ minutos), convergiendo a complejidad temporal constante $O(1)$.

**Directrices de uso**: Emplear `quick` en fases de redacción preliminar; exigir `standard` o `full` para evaluaciones editoriales formales; en modo secuencial de Codex, configurar el razonamiento en `medium` para equilibrar rigor de verificación y tiempo de ejecución.

## 7. Estructura del informe de evaluación y mecanismos de derivación multidimensional de puntuaciones

**Axiomas de derivación de puntuaciones**: Los escaños mantienen un **estricto régimen de cero puntuación**, emitiendo únicamente dictámenes discretos y citas textuales. En la Etapa 3, el motor de síntesis aplica las ecuaciones algebraicas definidas en `SKILL.md` §5.8:
$$\text{Base Score} = \frac{1}{4} \sum_{i \in \{04,05,06,07\}} S_i$$
donde cada dimensión literaria parte de 90 puntos, los fallos veto imponen topes (alto $\le 45$, medio/bajo $\le 65$), los fallos centrales estándar restan 12 puntos y los extendidos 5 puntos. Se superponen la penalización por huellas de IA del Escaño 03 ($-3/\text{ítem}$, máx $-10$), la bonificación de originalidad del Escaño 09 ($+3 \sim +5$, no deductiva) y los topes de fidelidad del Escaño 01 (Banda C de fidelidad topa el total en 45 con recomendación forzosa de reescritura).

**Normas de la zona de arbitraje humano**: Esta sección **prohíbe tajantemente el uso de tablas**, exponiendo todas las discrepancias críticas mediante prosa narrativa. Seis categorías de sucesos exigen arbitraje humano:
1. Cualquier dictamen ABSTAIN;
2. Todos los hallazgos del Escaño 11 (ética narrativa);
3. Criterios invalidados por fallo de verificación textual en la Etapa 2;
4. Fallos en criterios veto con gravedad `severity=中/低` (media/baja);
5. Criterios veto marcados como NA (no aplicable);
6. Activación de la alarma fenomenológica del Escaño 08.

## 8. Banco de criterios personalizados y directrices de extensión de escaños

- **Invarianza semántica**: La redacción de criterios en `references/criteria/*.md` puede perfeccionarse, pero su polaridad (`[通过]`/`[风险]`) debe permanecer inalterada. Cualquier modificación debe registrarse en `references/criteria/CHANGELOG.md`.
- **Integración de criterios privados (`criteria/99-private.md`)**: Permite incorporar criterios locales no públicos para evitar el sobreajuste deliberado de los modelos generadores.
- **Cuatro axiomas para incorporar escaños**: La creación de un nuevo escaño exige:
  1. **Perspectiva crítica diferenciada** (no subsumible en escaños existentes);
  2. **Solapamiento semántico $<20\%$**;
  3. **Tipología de evidencia exclusiva** (ej. triangulación de fuentes, sondeo en dos fases);
  4. **Cobertura insustituible de fallos potenciales**.

## 9. Análisis de limitaciones y fronteras de validez empírica (Sección de honestidad)

El sistema expone transparentemente sus fronteras metodológicas:

- **La verificación textual garantiza existencia, no certeza hermenéutica**: La verificación mecánica en la Etapa 2 certifica únicamente la presencia literal del fragmento en el texto; no valida la infalibilidad de la interpretación crítica contenida en la nota.
- **Vulnerabilidad a la Ley de Goodhart en criterios públicos**: Si las métricas de evaluación se convierten en objetivos de optimización para los modelos generadores, pierden su capacidad diagnóstica. El sistema lo combate mediante pruebas ciegas de lectores ingenuos y comentarios críticos libres.
- **La ética textual no sustituye el consentimiento legal de personas reales**: El Escaño 11 analiza únicamente la representación dentro del texto, no la obtención jurídica del consentimiento de los involucrados.
- **Reducción de varianza en lugar de sustitución del criterio editorial**: La evaluación colegiada a ciegas mutua elimina el ruido subjetivo individual para brindar un expediente probatorio sólido; no reemplaza el discernimiento estético final de los editores humanos.

### 9.1 Fronteras de validez empírica

En el estado de la versión v0.4.1, la validación empírica de los módulos se clasifica de la siguiente manera:
- **Validados empíricamente en ejecución real**: Canal de distribución a ciegas mutua, detección de citas e invalidación de alucinaciones, configuraciones `quick`/`standard`, evaluación cruzada entre modelos, auditoría completa de fidelidad, asignación de bandas por veto, protocolo en 2 fases del lector ingenuo.
- **Pendientes de validaciones empíricas complementarias**: Rama de comparación de textura para textos excepcionales que alcancen la Banda A frente a la alarma del lector ingenuo, análisis profundo de encargos complejos para el Escaño 10, agregación estadística multilector ($N > 1$) y pruebas de estrés con textos extremadamente largos en entornos de alta producción.

## 10. Declaración de privacidad de datos y ética académica

- Los textos de referencia en `references/anchors/` son **estrictamente sintéticos** y no contienen datos de personas reales.
- Los textos analizados y sus fuentes circulan exclusivamente entre el entorno local del usuario y las API de los modelos configurados; no se efectúa telemetría externa.
- Se aconseja enfáticamente **separar las sesiones de redacción de las de evaluación**, priorizando modelos de diferentes familias para neutralizar sesgos de complacencia endógenos.

## 11. Genealogía metodológica y agradecimientos teóricos

El diseño y el repositorio de criterios se inspiran en los siguientes trabajos académicos y proyectos abiertos (véase `docs/criteria-pool.md`):
- **TTCW (Torrance Test of Creative Writing)**: Base teórica para la adaptación de criterios de ritmo, equilibrio escénico y complejidad de personajes;
- **ConStory**: Taxonomía de conflictos de coherencia y anomalías fácticas;
- **Measuring AI Slop & Antislop**: Taxonomías de anomalías de generación artificial y principios de auditoría contextual;
- **EssayBench & HANNA**: Metodologías de evaluación estilística y protocolo de lectura fenomenológica;
- **HealthBench & RaR**: Principios de diseño de criterios binarios observables y rúbricas de cuatro elementos;
- **Aportaciones de la comunidad**: La categorización de giros artificiales toma referencias metodológicas de **shuorenhua** y **speak-human-tw**.

## 12. Licencia

Este proyecto está disponible bajo la Licencia MIT. Consulte [`LICENSE`](./LICENSE) para más detalles.
