---
name: company-brain
description: >
  Motor del canon de negocio y producto de un proyecto o empresa.
  Captura decisiones, procesos y observaciones, las mantiene correctas frente a
  la realidad, las recupera calibradas por fiabilidad, las conecta con una
  ontología y un grafo tipado, y mide el canon con gates. Úsala SIEMPRE que
  digan "company brain", "documentar esto", "registra esta decisión", "procesa
  este transcript", "qué sabemos de", "qué debo validar", "salud del canon",
  "cómo está el canon", "haz el enrich" o "abre una apuesta". También cubre el
  canon técnico (track `tech`). NO es la salud de un vault personal (second brain).
metadata:
  version: "0.7.1"
  supersedes: "docgate, docgate-extract, docgate-maintain, docgate-retrieve, canon-manifest"
compatibility: >
  Necesita lectura/escritura en el repo (skill/, tools/, y por proyecto
  {proyecto}/manifest.* y {proyecto}/Context/) y git. `extract` vía Fathom depende
  opcionalmente de `fathom-sync`. Hooks de `maintain` sobre `metric`
  requieren conectores MCP a Amplitude/Metabase (si no, `skipped`). `enrich`
  necesita `Context/_skill-config/ontology.json`. Los subcomandos de medida
  necesitan `python3` (solo stdlib, sin dependencias). El canon NO se sirve
  por MCP: se consulta con esta skill sobre el filesystem.
---

# company-brain — un motor, cualquier proyecto, ocho acciones

> Historial de versiones en `CHANGELOG.md`, en la raíz de este proyecto (no aquí, para no inflar la skill con historia). v0.5.0 (2026-08-08) añade la capa de retrieval descrita en la propuesta de diseño v0.5 (Retrieval layer), aprobada por el dueño del canon, con la Fase 1 (ontología seed) cerrada.

## Invocación

```
company-brain <proyecto> <acción>
```

- `<proyecto>` — cualquier carpeta `{proyecto}/` en la raíz del repo (el canon vive en `{proyecto}/Context/`; el motor, en `tools/cb.py`). `all` para acciones que tiene sentido correr sobre todos los proyectos a la vez (`validate`, `manifest`, `health`).
- `<acción>` — una de: `capture`, `extract`, `maintain`, `retrieve`, `validate`, `manifest`, `health`, `enrich`.

También dispara con lenguaje natural — en ese caso, infiere `<proyecto>` del contexto de la conversación (si no es obvio, pregunta) e infiere `<acción>` de la intención:

| Si dices algo como... | Acción |
|---|---|
| "quiero documentar X", "¿ya existe esto documentado?", "registra esta decisión" | `capture` |
| "procesa este transcript/thread/reunión para el proyecto" | `extract` |
| "trae/recupera el transcript de Fathom", "conecta con la API de Fathom" | `extract` (fuente API en vez de pegado manual) |
| "mantén el canon de X", "qué está caducado en el proyecto" | `maintain` |
| "qué sabemos de X en el proyecto", "busca en el canon de X" | `retrieve` |
| "qué tengo que validar", "revisión semanal del canon" | `validate` |
| "dame el índice del canon", "qué cubrimos y qué no" | `manifest` |
| "salud del canon de X", "hay pdfs sueltos", "revisa huérfanos/duplicados" | `health` |
| "cuántas veces se repite X", "qué clientes tuvieron X", "problemas principales de runtime" | `retrieve` (sobre `observation shareable`) |
| "qué significa X", "cómo le llamamos a X", "¿X y Y son lo mismo?" | `retrieve` (sobre `glossary`) |
| "mejora la búsqueda del canon", "normaliza los search terms", "haz el enrich", "qué notas se contradicen", "conecta notas relacionadas" | `enrich` |

---

## Modelo de notas — diez tipos en dos tracks, igual en cualquier proyecto

Hereda patrones de un vault personal de conocimiento (second brain) (`search_terms`, `layer`, `confidence`) y el contrato epistémico de `tech-context` (`validated`, `expires_on`, `source_of_truth`). Es el mismo modelo que se diseñó bajo `docgate`, generalizado: donde antes decía el nombre de una empresa concreta ahora dice `{proyecto}`.

| `type` | Qué captura | Layer por defecto | Expiry default |
|---|---|---|---|
| `context-map` | Qué existe y dónde — mapea un tema a sus fuentes (Notion, JIRA, Slack, conocimiento tribal) | knowledge | 90 días |
| `observation` | Diagnóstico: qué está roto, falta, se contradice o no está documentado — clasificado por `kind` (`gap-interno`/`anti-pattern`/`gotcha`/`pattern`, ver `references/contrato-de-notas.md`). **Privado por defecto** (`shareable: false`) — excepción en `references/contrato-de-notas.md` | diagnosis | 365 días |
| `decision-log` | Registro ligero de una decisión (contexto, opciones, decisión, dueño, fecha) | decision | 180 días |
| `process` | Cómo funciona algo de verdad vs. cómo está documentado | application | 90 días |
| `metric` | Definición de negocio de "qué cuenta" — qué mide, qué excluye, dónde está la vista canónica, qué trampas de datos tiene | knowledge | 180 días (sin hook wireado todavía) |
| `glossary` | Vocabulario compartido: qué significa un término y con qué se contrasta — el bounded context que evita que la IA y el equipo lo entiendan cada uno a su manera | knowledge | 180 días |

**Track `tech`** — mismo frontmatter común, `company_brain_track: tech` (D1 del decision-log de integración del track `tech`):

| `type` | Qué captura | Layer por defecto | Expiry default |
|---|---|---|---|
| `system` `Sys-` | Cómo funciona un módulo, servicio o flujo de código — de primera mano o verificado contra el repo | knowledge | 90 días |
| `runbook` `Run-` | Cómo hacer algo operativo paso a paso (deploy, rotar credenciales, debug de un incidente) | application | 90 días |
| `gotcha` `Got-` | Convención no obvia, excepción al patrón, bug recurrente de **código** — no confundir con `kind: gotcha` de `observation` (esa es de producto/runtime, ésta de implementación) | diagnosis | 365 días — boost ×1.3 en retrieve si `severity: high` |
| `inventory-repo` `Inv-` | Qué existe en un repo (versiones, deps, owners) — **siempre auto-generado** (`auto_generated: true`), nunca a mano | knowledge | no expira — se regenera cada noche |
| `reference` `Ref-` | Mirror de una fuente externa (Notion, PDF, deep-dive de repo) — igual rol que `Context/Sources/` pero nativo del esquema `tech-knowledge` original | knowledge | 90 días (5 años si `source_of_truth: external` con sync activo) |
| `plan` `Plan-` | Plan activo multi-semana/multi-fase, con versión y fecha de corte en el propio archivo | application | 90 días |

Las decisiones técnicas no son un tipo nuevo — usan `decision-log` (`DL-`) con `company_brain_track: tech`. `metric` no cambia. ### Frontmatter común de las notas del canon (los 6 tipos)

```yaml
---
type: context-map | observation | decision-log | process | metric | glossary | system | runbook | gotcha | inventory-repo
title: "Frase descriptiva — corta, sin ambigüedad"
project: "{proyecto}"              # p.ej. el nombre de la empresa, o de cualquier otro proyecto activo
company_brain_track: canon | tech  # canon (default) o tech — ver § company_brain_track
search_terms:
  - "[[Term 1]]"
  - "[[Term 2]]"
  - "[[Term 3]]"
  - "[[Term 4]]"
layer: knowledge | diagnosis | decision | application
confidence: high | medium | low
source_of_truth: vault | external
external_urls: []
jira_refs: []
notion_refs: []
captured_via: direct | extraction
source_id: null | "fathom:<recording_id>" | "hash:<sha256_16>"  # solo si captured_via: extraction — ver § Acción `extract`
owner: <nombre real de quien crea la nota>   # nunca un default fijo
occurred_on: YYYY-MM-DD            # v0.7.0 — fecha del EVENTO que la nota describe (la llamada, la reunión, la decisión)
captured_on: YYYY-MM-DD            # fecha en que se escribió la nota. No son lo mismo — ver § Los dos relojes
last_validated: YYYY-MM-DD
expires_on: YYYY-MM-DD
validated: true | false
status: active | stale | archived | superseded
source_project: "{proyecto}"       # duplicado de project, por compatibilidad con escáneres que leen ese campo
client_name: "<nombre real>"       # v0.7.0 en el contrato — obligatorio en context-map/decision-log/process/observation
client_id: cid-NNNN                # clave estable de client-directory.json; null si el cliente no está registrado
supersedes: []                     # opcional — wikilinks a notas que esta reemplaza explícitamente
connections: []                    # opcional, desde v0.5.0 — grafo tipado, ver § Ontología y grafo tipado
---
```

### Los dos relojes (v0.7.0)

`occurred_on` es cuándo pasó lo que la nota cuenta. `captured_on` es cuándo se escribió.
Confundirlos deja el canon sin cronología: antes de la v0.7.0, en un despliegue real, el canon tenía 40
decision-logs con el mismo `captured_on` porque salieron de la misma extracción masiva,
y 395 notas fechadas hasta seis meses después del evento que describen. Consecuencias
concretas de esa confusión, las dos medidas:

1. **`supersedes` es incomputable.** Sin fechas distintas no hay "la antigua" y "la nueva",
   así que el mecanismo entero (el campo, su derivación en `maintain`, el ×0.1 de
   `retrieve`, el check 11 de `health`) no puede dispararse nunca. Llevaba 0/171.
2. **La caducidad miente.** `expires_on` se contaba desde `captured_on`, así que una
   nota de una llamada de febrero se presentaba fresca hasta noviembre.

`occurred_on` se rellena solo cuando se conoce: en `extract` viene de la fuente (el
`source_date` de `extraction-log.jsonl`), en `capture` la pone la persona. Si no se sabe,
se deja vacío — **nunca se copia `captured_on` dentro**, porque eso es exactamente el
error que este campo existe para hacer visible.

**El reloj de `expires_on` cuenta desde `captured_on`** (decisión del dueño del canon, 2026-09-09).
La caducidad de este canon protege de *"nadie ha mirado esto en mucho tiempo"*, no de *"el
mundo cambió desde que esto era cierto"*: cuando alguien captura una nota está afirmando que
la revisó, y la ventana empieza ahí. La alternativa —anclar en el evento— pasaba 137 notas a
caducadas de golpe, 27 semanas de cola a 5 notas/semana de `validate`.

`occurred_on` no se usa para caducar, entonces. Sirve para tres cosas distintas: ordenar en
el tiempo (que es lo que hace computable `supersedes`), fechar lo que se cuenta cuando se
cita una nota, y **hacer visible el hueco**: una nota con seis meses entre el evento y su
captura se presenta fresca durante nueve meses después de que pasara. Eso es exposición real
de la política elegida, y por eso se mide sin bloquear (tira `temporal.desfase_medio` y
`python3 tools/cb.py expiry`, que compara los dos relojes y **no aplica nada**).

### Los campos de cliente (v0.7.0 en el contrato)

`client_name`/`client_id` se usaban en C17, C18 y en `retrieve` desde la v0.3.x, pero
**no estaban declarados en este bloque** — y por eso `capture`/`extract`, que siguen el
bloque, los rellenaban poco: en un despliegue real, 384 de 1.103 notas, con decision-logs a 4/171. No era
descuido de nadie: el contrato no los pedía.

Quién los lleva y quién no:

| tipo | `client_name` | por qué |
|---|---|---|
| `context-map` · `decision-log` · `process` · `observation` | **obligatorio** si la nota es de un cliente | son la ficha de cliente |
| `metric` · `glossary` | **nunca** | definen vocabulario de la casa, no de un cliente |
| `system` · `runbook` · `gotcha` · `reference` · `inventory-repo` | **nunca** | describen código; mencionar un cliente no los hace suyos |
| `plan` | opcional | hay planes de cliente y planes de producto |

Mencionar a un cliente en el cuerpo **no** lo atribuye: eso es una arista `menciona` del
grafo. La atribución la da el título o la persona que captura.

### Ontología y grafo tipado (v0.5.0)

Desde v0.5.0, `search_terms` ya no es texto libre sin control: se resuelve contra `Context/_skill-config/ontology.json`, un registro versionado de entidades con clases cerradas (`product-feature`, `channel`, `integration`; `client`/`metric`/`problem` se delegan a `client-directory.json`/`Metrics/`/`problem_tag`, que ya son vocabularios controlados — no se duplican en la ontología). Cada entidad tiene `id`, `canonical`, `class`, `aliases`, `gl_ref` (wikilink a una `Glossary/` si el término también tiene bounded context de vocabulario).

**C26 — resolución antes de escritura.** `capture`/`extract` resuelven cada `search_term` candidato contra la ontología antes de escribir la nota: si hay match (canónico o alias), se escribe la forma canónica; si no hay match, el término entra como candidato en el reporte final y solo se añade a la ontología con confirmación explícita de la persona — nunca se inventa una entidad nueva sobre la marcha. Mínimo actual de 4 `search_terms` se mantiene (C3); se recomienda que ≥2 sean de la ontología cuando exista una entidad real.

**G12 — la ontología no es taxonomía de carpetas.** Clasifica términos, no notas. Una nota no "pertenece" a una entidad — la menciona. No crear subcarpetas ni convenciones de naming a partir de las clases de la ontología.

**El campo `connections:`** declara el grafo tipado — aristas con significado entre notas del canon, no solo términos compartidos:

```yaml
connections:
  - rel: refuerza | contradice | extiende | depende-de
    target: "[[ID-de-la-nota-destino]]"
    note: "por qué, en una frase"
```

**C27 — 4 verbos cerrados, ninguno más.** `refuerza` (B aporta evidencia independiente de lo que A afirma), `contradice` (A y B no pueden ser ciertas a la vez), `extiende` (B añade alcance/detalle a A sin corregirla), `depende-de` (A pierde sentido si B cae). No se inventan verbos nuevos fuera de estos cuatro — mismo principio que los 4 callouts canónicos del vault personal del que hereda. Las relaciones que ya existen como campos propios (`supersedes`, `source_ref`, `problem_tag` compartido) no se duplican como typed links.

**C28 — `contradice` nunca marca `contradicted` por su cuenta.** Ese campo sigue reservado a hooks contra la realidad externa (`maintain`). Declarar una conexión `contradice` entre dos notas encola *ambas* en `validation-queue.json` con prioridad máxima — un humano decide en `validate` cuál sobrevive. La contradicción nota-vs-nota es una pregunta para humanos, no un veredicto de la IA.

Compilado derivado (regenerable, nunca a mano): `Context/_skill-config/graph.jsonl` — lo consumen `retrieve` (graph walk) y `health` (contradicciones sin resolver).

### `company_brain_track` — por qué existe

"Company Brain" puede nombrar dos cosas en el mismo vault: una tesis de contenido personal (Literature Notes/Permanent Notes/Manuscritos, jurisdicción del vault personal) y este canon de producto. Toda nota escrita por esta skill nace `company_brain_track: canon` — no hace falta decidirlo, ya se sabe por venir de aquí. El campo existe para que una nota de **fuera** de esta skill (una Idea, una Literature Note, un documento de estado) declare explícitamente a qué pista pertenece cuando el dominio es Company Brain — evita que la ambigüedad tesis-vs-canon se repita en notas nuevas. Desde v0.4.0, el valor `tech` cumple el mismo rol para el otro eje: una nota nace `tech` cuando describe implementación/código verificable contra un repo, y `canon` cuando describe negocio/producto — la mayoría de acciones (`maintain`, `retrieve`, `validate`, `manifest`, `health`) filtran o agrupan por este valor sin que haga falta declarar nada más.

### El detalle por tipo vive en `references/contrato-de-notas.md`

Los campos extra de cada tipo (`metric`, `glossary`, `observation`, el track `tech`,
`reference`, `plan`), los campos que escribe `maintain` y las convenciones de naming y
carpetas están en `references/contrato-de-notas.md`.

**Léelo cuando vayas a crear o editar una nota.** No está aquí porque la mayoría de las
invocaciones consultan el canon en vez de escribir en él, y no deben pagar ese detalle en
contexto. El frontmatter común, § Los dos relojes y § Los campos de cliente sí se quedan
arriba: los toca cualquier acción.

## Acción: `capture`

Ladder de "Recover Before Create" antes de crear nada nuevo — igual disciplina que tenía `docgate`.

1. **¿Ya existe?** → buscar en `{proyecto}/Context/`, luego Notion, luego JIRA. Si existe y está vigente, parar y enlazar.
2. **¿Existe pero desactualizado?** → sugerir actualizar en vez de crear; ofrecer una `observation` que marque el gap.
3. **¿Es de otro equipo/persona?** → sugerir hablar con esa persona primero; ofrecer un `context-map` de quién sabe qué.
4. **¿Basta con algo ligero?** → un `decision-log` de 5 líneas o una `observation` breve.
5. **¿Basta con indexar dónde vive?** → un `context-map`, sin escribir contenido nuevo. Esta es la resolución más común — no es un fallo.
6. **Crear.** Solo si 1-5 están genuinamente agotados.

**Track `tech` en `capture` directo (desde v0.4.0).** Cuando la persona explica algo de primera mano sobre código/infraestructura (no una fuente externa — eso es `extract`), la misma ladder aplica y el resultado nace `system`/`runbook`/`gotcha` con `company_brain_track: tech` en vez de uno de los seis tipos `canon`. Pedir siempre `repo` y `modules`; ofrecer declarar `verify_hooks` si aplica (nunca obligar — son opt-in, ver C24). Esto es la vía de captura manual que sustituye a `tech-context-capture` (que nunca llegó a instalarse).

**Observe** (antes un modo aparte de `docgate`, ahora plegado aquí): cuando la persona comparte una frustración o diagnóstico sobre documentación/proceso, ofrecer capturarlo como `observation` — una sola nota que sintetice el patrón, no una por queja.

**Vocabulario antes que hechos.** Antes de escribir cualquier `CM-`/`OB-`/`DL-`/`PR-` que use un término potencialmente ambiguo, comprobar `Context/Glossary/`: si ya existe una `GL-` para ese término, enlazarla por wikilink en `search_terms` en vez de redefinirlo dentro del cuerpo. Si el término no existe y hay evidencia real de que se confunde entre personas (no especulación), ofrecer capturarlo primero como `glossary` — antes que la nota que lo usa. Ver `references/contrato-de-notas.md`.

**Resolución contra la ontología (C26, desde v0.5.0).** Antes de fijar los `search_terms` finales, resolver cada uno contra `Context/_skill-config/ontology.json`: si hay match (canónico o alias), usar la forma canónica. Si no hay match, no inventar una entidad — el término se queda libre (es válido, ver §4.2 de la Propuesta v0.5) salvo que haya evidencia real de que se repite ≥3 veces en el canon, en cuyo caso se señala como candidato en el reporte, igual que un candidato a `glossary`.

**Shareable, siempre pregunta, nunca infiere.** Si lo que describe la persona es un problema de producto/runtime (algo que falló en producción, en un bot real, con un cliente real) en vez de un gap de documentación/proceso interno: preguntar explícitamente "¿esto es para compartir con el equipo (`shareable: true`, con `client_id` y `problem_tag`) o es diagnóstico privado?" — nunca asumir un lado. Si es shareable y el cliente es nuevo, pedir el nombre real, asignar un `client_id` nuevo para agregación estructurada, y escribir el nombre real tanto en `client-directory.json` como en el cuerpo/frontmatter de la nota — el nombre del cliente y de la empresa deben verse, no ocultarse (C17).

Al escribir: mínimo 4 `search_terms` (objetivo 6), frontmatter completo, `expires_on` auto-calculado por tipo, `validated: true` solo si la persona aporta conocimiento de primera mano, y `owner` con su nombre real.

**Nunca crear sin aprobación explícita de la persona que está usando la skill.** Pre-flight presenta y espera. Capture pregunta antes de escribir. Observe ofrece, no asume.

**Ningún documento de trabajo cierra sin nota-índice.** Si esta sesión (o cualquier acción de esta skill) genera un documento de trabajo exportable (PDF de análisis, síntesis, propuesta) con conclusiones citables, la sesión no termina sin una de dos cosas: (a) la nota-índice correspondiente escrita en el mismo momento — nunca como una frase de "pendiente" al pie del documento, o (b) si de verdad no hay tiempo, una entrada abierta en el tablero de tareas del equipo con la ruta exacta del documento y una fecha límite. Una frase en un pie de página que nadie vuelve a leer no cuenta como captura — es exactamente el patrón que produjo ocho PDFs huérfanos encontrados el 2026-08-06 en la carpeta de documentos de trabajo, precisamente por esto.

## Acción: `extract`

Ingestión masiva desde una fuente cruda (transcript, thread de Slack, doc, email, conversación) — el equivalente de `docgate-extract`.

### De dónde puede venir el transcript

- **Pegado manual** (como hasta ahora): la persona pega el texto crudo en la conversación.
- **API pública de Fathom, vía la skill `fathom-sync`**: la persona pide traer el transcript de una reunión de Fathom (por `recording_id` o por URL de share) y `extract` invoca `fathom-sync` en vez de hablar con la API directamente — esa skill lista/filtra reuniones y trae el transcript completo. La API key sigue aportándose en el momento, nunca se persiste — esa disciplina vive ahora en `fathom-sync` (ver su propio constraint F1) y sigue aplicando aquí igual (C20). Fuera de este primer paso de obtención del texto, el resto del pipeline (pasos 2-8 de abajo) es idéntico venga la fuente de donde venga.

1. **Fingerprint de la fuente — nunca reprocesar sin preguntar.** Antes de clasificar nada: calcular un `source_id` (si la fuente tiene un identificador estable — `fathom:<recording_id>`, ID de thread de Slack, etc. — usar ese; si no, `hash:<sha256_16>` — sha256 de los campos `text` de cada línea del transcript, concatenados en orden, en minúsculas y con espacios colapsados, truncado a los primeros 16 caracteres hex) y buscarlo en `{proyecto}/Context/_skill-config/extraction-log.jsonl`. Este mismo `source_id` se escribe también en el frontmatter de cada nota que produce esta fuente (campo `source_id` del modelo común) — así se puede ir de una nota individual a `extraction-log.jsonl` (qué otras notas nacieron de la misma llamada) y de una entrada del log a sus notas, en cualquier dirección.
   - **Coincidencia encontrada** → NO crear notas nuevas por defecto. Decir a la persona qué notas generó esa fuente la vez anterior (con la fecha de `processed_on`) y preguntar explícitamente: ¿reprocesar de cero, añadir una `occurrence` nueva si esta pasada trae evidencia que la anterior no capturó, o no hacer nada? Nunca elegir en su lugar.
   - **Sin coincidencia** → seguir con el resto del pipeline, y al cerrar (paso 8) escribir la entrada nueva en `extraction-log.jsonl`.
2. Clasificar la fuente (transcript / Slack / doc / email / JIRA / conversación).
3. Escanear en una sola pasada los 4 tipos capturables (decision-log, process, context-map, observation) — nunca `metric` ni `glossary` directamente: una definición negociada en una reunión rara vez pasa el lint de 3 piezas de `metric`, y un término nuevo rara vez trae ya la pareja de contraste clara que pide `glossary`. Si algo suena a definición de métrica, capturarlo como `observation` y dejar que la persona decida si la promueve a `MET-` vía `capture`. Si la fuente distingue explícitamente dos términos que se confunden (patrón "no es X, es Y", "cuando decimos X nos referimos a Y", un glosario de "qué no vamos a decir"), señalarlo como candidato a `glossary` en el reporte final — nunca crearlo directo dentro de `extract`. Si la fuente es técnica (post-mortem, incident review, PR, thread de código), escanear también candidatos a `runbook`/`system`/`gotcha` (track `tech`) con la misma regla que `metric`: si no pasa el contrato completo del tipo, nace como `observation` track `tech` y se promueve después vía `capture`.
4. **Clasificar cada `observation` candidata en shareable o privada** antes de escribirla: ¿es un problema de producto/runtime que afectó a un cliente real (shareable) o un gap de documentación/proceso interno (privada, default)? Presentar la clasificación para confirmar — el flag `shareable` en sí no se infiere sin más, se propone y se confirma.
5. **Duplicate check** contra lo que ya existe en `{proyecto}/Context/` antes de escribir cada nota — actualizar en vez de duplicar cuando aplique. Para `observation shareable`, el duplicate check es por `problem_tag` (mismo problema, distinta sesión), no solo por título: si ya existe una `OB-` shareable con `problem_tag` equivalente, **no crear nota nueva — añadir una entrada a `occurrences`** con `date`/`client_id`/`transcript_ref`/`quote` de esta fuente. (Esto cubre dos transcripts *distintos* con el mismo problema — el fingerprint del paso 1 cubre la *misma* fuente pasada dos veces.) Antes de escribir el cuerpo de cualquier nota, resolver también los términos que use contra `Context/Glossary/` existente — enlazar por wikilink, nunca redefinir un término que ya tiene `GL-`.
5.5. **Resolución contra la ontología (C26, desde v0.5.0).** Igual que el paso anterior con `Glossary/`, resolver cada `search_term` candidato contra `Context/_skill-config/ontology.json` antes de escribir la nota — match usa la forma canónica, sin match se deja libre o se señala como candidato si hay evidencia real de repetición (misma regla que ya aplica aquí a clientes vía `client-directory.json`, generalizada al resto de clases).
6. **`client_id` de la fuente**: si el transcript es de un cliente ya conocido, usar su `client_id` existente (buscarlo en `client-directory.json` por nombre real — nunca crear un segundo id para el mismo cliente). Si es un cliente nuevo, pedir confirmación y crear la entrada nueva en `client-directory.json`. Nunca derivar `client_id` de una etiqueta de sector+tamaño — eso es un bucket, no una clave de cliente, y colisiona en cuanto haya dos clientes del mismo sector y tamaño. El nombre real del cliente se escribe también en el cuerpo/frontmatter (`client_name`) de cada nota que produce esta fuente — no solo en `client-directory.json`.
7. Todas las notas extraídas nacen `validated: false`, `captured_via: extraction`, y con
   **`occurred_on` = la fecha del evento de la fuente** (el `source_date` que se escribe en
   `extraction-log.jsonl`), que no es `captured_on`. Si la fuente no trae fecha, `occurred_on`
   se deja vacío (C29). Un transcript de 1 hora debería rendir 3-8 notas, no 20 — si salen más de 10, probablemente se está capturando ruido.
8. **Reporte final — incluye el nombre real.** Notas creadas, notas actualizadas (con qué `problem_tag` y nuevo conteo de `occurrences`), cola de validación resultante, y qué se flaggeó para la skill de extracción del vault personal, si existe (conocimiento personal, no organizacional — no le pertenece a este canon). El reporte cita el nombre real del cliente y de la empresa, junto con `client_id` — es importante que se vea quién era el cliente, incluido en el título de una entrada de log. Cierra escribiendo/actualizando la línea correspondiente en `extraction-log.jsonl` (`source_id`, **`source_date`**, `processed_on`, `notes_created`, `notes_updated`).

> [!important] `source_date` no es opcional
> Es **la fecha del evento** de la fuente (el día de la llamada), y es el único sitio desde
> el que `occurred_on` se puede recuperar después. Sin ella, una nota extraída queda sin eje
> temporal para siempre: `supersedes` no se puede computar y la nota se fecha el día en que
> se procesó. Medido el 2026-09-09: las 31 entradas escritas ese día no la llevaban, y las
> 35 notas que salieron de ellas se quedaron sin `occurred_on` — el gate
> `temporal.occurred_on` se puso en rojo por eso. `processed_on` **no** la sustituye: son los
> dos relojes otra vez. Si la fuente no trae fecha, `source_date: null` explícito.

## Acción: `maintain`

El Puente Verificar — vuelve el canon activamente correcto en vez de pasivamente correcto.

1. **Hooks activos**: para notas `metric` con `verify_hooks` declarados, ejecutarlos contra Amplitude/Metabase si el wiring MCP existe; si no, marcar `skipped` siempre — nunca inventar un `pass`. *(El wiring en sí es trabajo pendiente, no parte de esta acción — ver § Qué falta.)* Mismo criterio para notas track `tech` con `verify_hooks` (`file_exists`, `grep_repo`, `package_version`, `reference_hash`): se ejecutan solo si esta sesión tiene el repo declarado en `_skill-config/repos` accesible en el filesystem; si no, `skipped`, nunca inventado (C12, C24). Si un `reference_hash` cambia, resetear `validated: false` en las notas listadas en su `derives`.
2. **Staleness pasiva**: recalcular `expires_on` vs. hoy → `stale` si venció. `review_due: true` si faltan ≤14 días y sigue `active`.
3. **`superseded_by`**: escanear todas las notas del proyecto por `supersedes:` que apunten a esta. Si se encuentra, escribir `superseded_by` — nunca archivar solo.
4. **Enlaces rotos**: wikilinks en `search_terms`/`supersedes` sin nota destino.
5. **Cola de validación**: escribir `{proyecto}/Context/_skill-config/validation-queue.json`, priorizada: `contradicted` → `superseded` → `expired` → `review_due` → `unvalidated`; dentro de cada grupo, `decision-log`/`metric`/`runbook`/`inventory-repo` primero (orden idéntico al de `tech-context-validate`: runbook antes que inventory, ambos antes que system), luego `process`/`system`, luego `context-map`, luego `observation`/`gotcha`.
6. **Reporte**: `{proyecto}/Context/_reports/Run-maintain-<fecha>.md` con hooks ejecutados/skipped, staleness, superseded, enlaces rotos, y tamaño de cola.

Nunca pone `validated: true`, nunca edita el cuerpo, nunca archiva sola, nunca inventa el resultado de un hook. Un pase, reporte, cola, stop.

## Acción: `retrieve`

Pipeline híbrido de 6 etapas, calibrado por validez:

1. Descomponer la query si es compuesta.
2. Candidatos híbridos: filtro estructural (`type`, `project`) + señal léxica (título, search_terms, cuerpo). `--track canon|tech` filtra además por `company_brain_track` cuando se declara.
3. Graph walk (desde v0.5.0, track `canon`): primero sobre las aristas tipadas de `Context/_skill-config/graph.jsonl` (`connections:` — `refuerza`/`contradice`/`extiende`/`depende-de`, mucha más señal que términos compartidos porque las confirmó una persona), luego, como fallback, sobre `search_terms`/`supersedes` wikilinkeados normales. Track `tech`: `see_also`/`derives` (mismas edges que usa `tech-context-retrieve`) — no tiene grafo tipado todavía. Al servir una nota, mostrar sus `contradice`/`superseded` visibles en el propio resultado.
4. Rerank del candidate set.
5. **Calibración por defecto conocido** (v0.7.0 — antes "por validez"):

   | Estado | Multiplicador | Qué afirma |
   |---|---|---|
   | `superseded_by` con valor | ×0.1 | hay una nota posterior que la reemplaza |
   | `contradicted: true` | ×0.15 | un hook la contradijo contra la realidad externa |
   | `expired` | ×0.4 | su ventana de vigencia pasó sin revalidar |
   | `review_due: true` | ×0.7 | está en cola de revisión |

   Los cuatro afirman un **defecto conocido de esa nota**, así que degradarla es correcto
   sin necesidad de datos de uso.

   `validated: false` **ya no multiplica** — es un desempate entre resultados por lo demás
   iguales, y sigue apareciendo como etiqueta. Por qué cambió: se aplicaba al 93 % del
   canon (en un despliegue real, el 2026-09-09, 29 de 659 notas de negocio estaban validadas), y un multiplicador
   que le toca a casi todo no reordena nada — solo levantaba el 7 % restante, que son
   sobre todo notas técnicas que llegaron ya validadas en la migración. El efecto real era
   *"lo técnico por encima del canon"*, que no es lo que nadie quiso.

   Para `gotcha` (track `tech`) con `severity: high`, boost ×1.3 antes de esta calibración.
   **Este 1,3 no está medido** — es una constante puesta a ojo, y queda marcada como tal
   hasta que haya consultas registradas contra las que probarla (ver § Qué falta).

   `--canonical-only` esconde todo lo que no sea `validated: true`, no `contradicted`, no `superseded_by`.
6. Reconstrucción activa si el resultado es pobre.

Cada resultado siempre lleva su etiqueta de estado visible (`✓ validado`, `sin validar`, `⚠ CONTRADICTED`, `⚠ SUPERSEDED por [[X]]`, `EXPIRADO`, `review due`). Nunca presentar una nota `contradicted`/`superseded_by` como canónica sin avisarlo en el propio texto de la respuesta.

### El log de consultas — esquema 2 (v0.7.0)

Cada `retrieve` escribe una línea en **`Context/_skill-config/retrieval-log/<persona>-<AAAA-MM>.jsonl`**.
**El campo que importa es `notas_usadas`**: cuáles de las devueltas acabaron de verdad en la
respuesta. Eso es un gold set etiquetado por un humano, producido sin trabajo extra, y es lo
único contra lo que este canon podrá medir su recall algún día.

```jsonc
{"schema": "company-brain/retrieval-log/2", "date": "...", "who": "ana", "query": "...",
 "subqueries": [...], "expansion": [...], "filters": {...},
 "devueltas": [{"nota": "DL-...", "bucket": "confirmado"}],
 "notas_usadas": ["DL-..."], "gaps": ["..."], "reformulacion": false, "intent": "explicit",
 "session_id": "2026-09-09-a"}
```

**Un fichero por persona y mes, no un fichero único.** El log vive en el repo a propósito:
así cada `git push` sube las consultas de esa persona y el gold se acumula entre todo el
equipo, que es lo que lo hace valioso. Pero un JSONL único al que aportan varias personas
entra en **conflicto de merge en cada push simultáneo** (es el mismo problema que G9 ya
señala para `extraction-log.jsonl`, y aquí sería mucho peor porque se escribe en cada
consulta, no en cada extracción). Un log que da guerra al hacer push es un log que la gente
deja de escribir — y eso mata el gold, que es justo para lo que existe.

Dos personas nunca escriben el mismo fichero, así que no hay conflicto que resolver.
`.gitattributes` añade `merge=union` como red de seguridad para el caso restante (la misma
persona escribiendo desde dos sitios), no como diseño. Quien lee el log lee el directorio
entero: `python3 tools/cb.py stats`.

**Qué NO se escribe en el log.** Una consulta dice qué estaba intentando averiguar alguien, y
eso no siempre es neutro: una búsqueda sobre el riesgo de fuga de un cliente, sobre un
competidor o sobre una persona del equipo revela intención, no solo interés. La regla es la
de C6 aplicada a las consultas: si la consulta en sí no se podría enseñar en el canal del
equipo, se registra **sin el texto** (`query: "[omitida]"`, y `notas_usadas`/`gaps` sí, que
es lo que tiene valor de medida). Nunca se edita ni se borra una entrada ya escrita para
esconderla a posteriori: se omite al escribirla o no se omite.

- `notas_usadas` ⊆ `devueltas`, **salvo** cuando la nota se encontró a mano tras fallar el
  retrieve: entonces va solo en `notas_usadas`, y ese es el caso más informativo del log.
- `gaps` no es "no encontré nada": es *qué pregunta concreta no tiene nota*. Alimenta
  `capture`/`extract`.
- `expansion` son los términos con los que se amplió la búsqueda. En el vault personal
  esta es la única palanca de recall que pasó el gate con evidencia (+16,9 pp, IC95 %
  [+7,8, +26,5]); registrarla es lo que permitirá saber si aquí también.
- **`outcome` está retirado.** Era un juicio que la IA se ponía a sí misma; en el vault
  personal, donde el mecanismo lleva 78 entradas, salió inútil (69 de 71 marcados
  `success`). Las entradas migradas lo conservan en `outcome_v1_retirado`.
- `session_id` es **obligatorio**. Es lo que permitirá hacer leave-one-session-out el día que
  el log se use para medir algo. Sin él, cualquier señal derivada del log y evaluada contra
  el propio log se mide contra sí misma: en el vault personal eso vale ~20 pp de inflación
  medidos (canal de grafo 45,3 % → 25,6 % con LOSO). Regla: **el log se guarda para medir;
  usarlo como señal de ranking exige holdout por sesión.**
- No se rellena a posteriori. Una entrada reconstruida de memoria contamina el gold, y un
  gold contaminado es peor que un gold pequeño.

Fallos repetidos (misma query ≥2× sin buen resultado) → candidato para `capture`/`extract`.
Best-hit `unvalidated`/`contradicted` → sube prioridad en la cola de `maintain`.

**Cruces de cliente × problema × canal** ("¿qué clientes con WhatsApp han tenido X?") se
resuelven con `python3 tools/cb.py cruce --canal WhatsApp --problema <tag-o-texto>`. Es un
**join, no un recorrido de grafo**: el canal sale de `entities.json` (derivado del
frontmatter) y el problema de `occurrences`. 0,5 s sobre el canon entero, sin índice.

Dos cosas que hay que decir al servir un cruce, siempre:

- **La señal del canal.** `[declarado]` = la familia de canal está en los `search_terms` de
  alguna nota de ese cliente, o sea que alguien la escribió. `[mención]` = la palabra sale en
  el cuerpo. Lo segundo es una pista, no un hecho del cliente (C30), y por defecto no cuenta:
  hay que pedir `--pistas`. En un despliegue real, los clientes con canal declarado duplicaban a los que solo tenían mención.
- **Cuántos clientes tiene el problema en total**, no solo los que pasan el filtro. En un despliegue real, de 83
  problemas compartibles, **77 se han visto con un solo cliente** y 5 con dos; ninguno con
  tres. Un cruce que devuelve un cliente no está fallando — es que la evidencia es esa.

Las familias de canal (`WhatsApp`, `Messenger`, `Web chat`…) se agrupan por token
distintivo y **no** por la ontología, a propósito: en un despliegue real, el canon usaba 157 variantes de término con
"whatsapp" en 263 apariciones y `ontology.json` conocía 5. Añadir las que falten es trabajo de
`enrich` con aprobación humana (C2), no del cruce.

**Queries de agregación sobre `observation shareable`** ("¿cuántas veces se repite X?", "¿qué problemas de runtime son los principales?", "¿qué clientes tuvieron X?") no pasan por el rerank de arriba — se resuelven leyendo directo `occurrences` de las `OB-` shareable que matchean `problem_tag`/`search_terms`: el conteo es `len(occurrences)`, el ranking es por `len(occurrences)` + `severity`, y la lista de clientes se responde por nombre real (resolviendo `client_id` contra `client-directory.json`, o leyendo `client_name` directamente si la nota lo tiene) — también en respuestas que salgan del vault (Slack, GitLab, deck del equipo).

**Queries sobre un término** ("¿qué significa X?", "¿cómo le llamamos a X?", "¿X y Y son lo mismo?") tampoco pasan por el rerank de arriba — se resuelven leyendo directo la `GL-` correspondiente (por `term`/`aliases`) y, si aplica, su `contrasts_with`. Si el término no tiene `GL-` todavía, decirlo explícitamente en vez de improvisar una definición desde el cuerpo de otras notas — es la señal para ofrecer un `capture` de tipo `glossary`.

## Acción: `validate`

El Puente Promover — el único momento del sistema que pide esfuerzo humano. Ritual semanal acotado, no cola infinita.

1. Cargar `{proyecto}/Context/_skill-config/validation-queue.json` (o fusionar las de varios proyectos si `<proyecto>` es `all`).
2. Filtrar por dueño; tomar máximo **5 notas en total** (sumando proyectos si aplica — nunca 5 por proyecto).
3. Presentar una a una: título, motivo (`contradicted`/`superseded`/`expired`/`review_due`/`unvalidated`), evidencia. El humano decide:
   - Sigue siendo cierta → `validated: true`, `last_validated: hoy`. Si la nota estaba `contradicted: true` por un hook, el humano NO lo limpia aquí — `contradicted` solo se resuelve cuando el hook vuelve a pasar en el siguiente `maintain` (regla idéntica a `tech-context-validate`).
   - Desactualizada → la persona edita el cuerpo, luego `validated: true`.
   - Ya no aplica → proponer baja, nunca archivar sin confirmación.
   - No es suyo / no lo sabe → reasignar `owner`, dejar en cola.
4. Escribir los cambios; regenerar o dejar que el próximo `maintain` recomponga la cola.
5. Cerrar con estado terminal: *"Validadas N. Cola restante M."* Si queda vacía: *"canon al día para {proyecto} esta semana."* Fin, no iterar.

## Acción: `manifest`

Índice barato de consumo — para que un agente decida qué nota abrir sin grepear todo el árbol. **Desde v0.3.2 es por proyecto, no global**: escribe `{proyecto}/manifest.json` y `...manifest.md`, cubriendo solo `Context/` de ese proyecto. Si `<proyecto>` es `all`, generar/actualizar el manifest de cada proyecto por separado — no existe (ni se recrea) un manifest único cruzando proyectos; esa idea ya se descartó una vez con `canon-manifest` (ver CHANGELOG v0.3.2) y sigue descartada aquí. Desde v0.4.0, cuando el proyecto tenga notas track `tech`, el manifest de ese proyecto incluye una sección propia "Tech" además de "Canon" — mismo índice, misma cadencia, filtrado por `company_brain_track`.

Por nota: `answers` (qué pregunta responde, de `title`), `consume_when` (cuándo abrirla, de `type`+`title`+cuerpo), `expect` (el `layer`), `freshness` (`fresh`/`stale`/`contradicted`/`superseded`/`unvalidated`), `trust` (`high`/`medium`/`low`, de `validated`+`confidence`), `cost_tokens` (palabras del cuerpo ÷ 0.75, redondeado a la decena).

**Sección "Top Runtime Issues"**: si hay ≥1 `observation` con `shareable: true`, el manifest añade una tabla ordenada por `len(occurrences)` desc, luego `severity` desc — `problem_tag`, conteo de ocurrencias, nombre real y `client_id` de los clientes afectados, `freshness`/`trust` igual que el resto. Esta tabla es exactamente el artefacto pensado para salir del vault (Slack, GitLab, deck del equipo) — el resto del manifest, no necesariamente.

Regenerar tras correr `maintain` o al crear/editar notas — no es un watcher.

## Acción: `health`

Higiene de archivos y cobertura de captura — el chequeo que ninguna otra acción hace: no si una nota individual sigue vigente (eso es `maintain`), sino si el **conjunto de artefactos** del proyecto está completo y sin duplicados. Nace directamente de una sesión de limpieza (2026-08-06) que encontró 8 PDFs de trabajo sueltos en la carpeta de documentos de trabajo sin nota-índice, algunos duplicados el mismo día, y uno huérfano en la raíz del repo.

**Jurisdicción — esto es lo que separa `health` de la salud del vault personal.** Escanea únicamente `{proyecto}/Context/` y los documentos de producto/canon en la carpeta de documentos de trabajo asociada al proyecto (filtrados por dominio Company Brain + `company_brain_track: canon`). **Nunca** escanea `Literature Notes/`, `Permanent Notes/`, `Manuscripts/`, `Cases/` ni `Inbox/` — esas carpetas son jurisdicción exclusiva de la skill de salud del vault personal, si existe. Si `health` encuentra un PDF o nota cuyo contenido parece ser tesis/contenido personal en vez de canon de negocio, lo señala para la skill de extracción del vault personal, si existe y no lo procesa él mismo — mismo patrón que ya usa `extract` con conocimiento personal.

Checks:

1. **PDF huérfano** — cualquier PDF en el árbol escaneado que ninguna nota `.md` cite por `source_file` o por nombre exacto. Reportar con ruta completa.
2. **Duplicado / versión superada** — dos o más PDFs cuyo título comparte la mayoría de palabras clave y fecha de creación cercana (mismo día o consecutivo): candidatos a "misma tesis, exportada dos veces". Heurístico por título+fecha, no por hash de contenido — en caso ambiguo, marcar "revisar a mano", nunca asumir cuál es la versión buena.
3. **Nota-índice ausente para documento de trabajo** — un PDF cuyo texto contiene frases tipo "documento de trabajo", "pendiente: capturar..." sin que exista la nota-índice correspondiente. Es la señal directa de una captura que quedó a medias.
4. **Naming drift** — un PDF cuyo título no coincide exactamente con el de ninguna nota `.md` que lo documenta, sugiriendo que se exportó con un título alternativo en vez de mantener el mismo nombre del documento original.
5. **`company_brain_track` ausente** — cualquier nota bajo dominio Company Brain sin ese campo, cuando el proyecto tiene ambas pistas (tesis y canon) activas.
6. **Integridad de `client-directory.json`** — un `client_id` referenciado en `occurrences` de alguna `OB-` shareable que no existe en `client-directory.json` (huérfano — no se puede confirmar si es un cliente real o un error de asignación), o una entrada de `client-directory.json` que ningún `client_id` en el canon referencia (candidato a limpiar, nunca borrar sin confirmar).
7. **Deriva de glosario** — un término con `GL-` propia (`term` o algún `aliases`) que aparece en el cuerpo de otra nota del canon con una definición distinta a su `canonical_definition` — señal de que el glosario quedó desactualizado o de que alguien lo sigue entendiendo distinto. Heurístico por coincidencia de texto, no semántico — ante duda, "revisar a mano".
8. **Nota `tech` muy servida sin `verify_hooks`** — una `system`/`runbook`/`gotcha` que aparece entre los resultados top de `retrieval-log.jsonl` pero no declara `verify_hooks`. Reporta, no obliga — los hooks son opt-in.
9. **Hook de `tech` que referencia un repo inaccesible** — un `verify_hooks` cuyo `repo` no está declarado en `_skill-config/repos` de la config actual.
10. **Prefijo/track inconsistente** — una nota `Run-`/`Sys-`/`Got-`/`Inv-` sin `company_brain_track: tech`, o una nota `company_brain_track: tech` con un prefijo de los seis tipos `canon`.
11. **Contradicción sin resolver >14 días** (v0.5.0) — una conexión `contradice` en `connections:` cuyas dos notas siguen sin `superseded_by` ni corrección 14 días después de declararse. Señal de que la cola de `validate` no está drenando las contradicciones reales.
12. **Conectividad de ontología** — *retirado como check en v0.7.0*. Vive en la tira de
    `metrics.json`, sin gate y con la razón escrita. Se retiró porque decía literalmente
    "reporta el número, no lo juzga": un check que no puede fallar no es un check, es una
    declaración, y consume el presupuesto de atención de los que sí fallan. El número se
    sigue midiendo (`tools/cb.py gates`, tira `conectividad.dos_o_mas`, 27,7 % el
    2026-09-09) — lo que se retira es su condición de check.
13. **Ficheros sin contrato dentro de `Context/`** (v0.7.0) — cualquier `.md` bajo
    `Context/` que no declare un `type` del contrato. Cuentan como canon en cualquier grep
    y no lo son. Primera pasada en un despliegue real (2026-09-09): **78**, de los cuales 77 son ficheros de
    trabajo de un mismo plan bajo `Tech/plans/` que entraron con la migración de
    `tech-knowledge` sin frontmatter. Reporta y propone dos salidas (darles contrato o
    moverlos fuera de `Context/`); no mueve nada (C14). Comando: `python3 tools/cb.py contract`.
14. **Gates en rojo** (v0.7.0) — corre `python3 tools/cb.py gates` y trae los que estén en
    rojo, con su umbral y la razón de que ese umbral sea ése. Es el único check cuyo
    criterio no vive en esta skill sino en `_skill-config/metrics.json`, a propósito: un
    umbral escrito en la skill es un umbral que nadie audita.
15. **Apuestas vencidas sin cerrar** (v0.7.0) — líneas de `bets.jsonl` con `status: open`
    cuya fecha de revisión ya pasó. Una apuesta que nadie cierra es una predicción que no
    arriesga nada, que es justo el fallo que el mecanismo existe para evitar.

**Nunca actúa por su cuenta.** Igual que `maintain` con los hooks: reporta y propone, no mueve, no archiva, no borra. Cada hallazgo se presenta con una recomendación (crear nota-índice / archivar como duplicado / etiquetar) y espera confirmación explícita de la persona, archivo por archivo — nunca un "archivé N PDFs" sin haber preguntado.

Reporte: `{proyecto}/Context/_reports/Run-health-<fecha>.md`.

Frecuencia sugerida: al cerrar cualquier sesión que haya generado un PDF de trabajo, y como parte del ritual semanal de `validate`.

### El instrumento — `tools/cb.py`

Los checks 13, 14 y 15 no se hacen leyendo: se corren. `tools/cb.py` es un fichero, cero
dependencias, dry-run por defecto y determinista.

| comando | qué hace |
|---|---|
| `stats` | el estado del canon en números: corpus por segmento, relleno por campo y por tipo, eje temporal, grafo, log, apuestas |
| `contract` | los `.md` de `Context/` sin `type` del contrato (check 13) |
| `entities` | reconstruye `entities.json` desde `client-directory.json` + el frontmatter; marca los alias ambiguos |
| `clients` | propone `client_name`/`client_id` donde falten, **solo** con señal en el título |
| `dates` | rellena `occurred_on` desde el `source_date` de `extraction-log.jsonl` |
| `expiry` | compara la caducidad escrita con la que saldría de contar desde el evento — mide, no aplica |
| `supersession` | pares candidatos a supersesión, ordenados en el tiempo. Nunca escribe (C2) |
| `cruce` | cliente × problema × canal: «qué clientes con WhatsApp han tenido X» |
| `grafo` | reconstruye `entity-graph.jsonl` desde el frontmatter |
| `vecinos` | recorre el grafo desde un nodo, filtrando por verbo y profundidad |
| `normalizar` | quita las comillas de los escalares de vocabulario cerrado (`project`, `type`, `status`…) |
| `contradicciones` | regenera `_reports/contradictions.md` |
| `gates` | evalúa `metrics.json` y anexa la corrida a `runs.jsonl` (check 14) |
| `surface` | mide la superficie de instrucción de este propio archivo y la anexa a `instruction-surface.jsonl` |

**Tiene tests, y los tests tienen control negativo.** `python3 tools/test_cb.py` — 23 casos
contra una canon sintética de trece notas (`tools/fixture/`), nunca contra el canon real, que
no es determinista. Cada caso dice en su texto **por qué existe**: casi todos nacen de un bug
que ya ocurrió.

Que pasen no basta. Se verifican reintroduciendo siete bugs reales en `cb.py` y comprobando
que la suite se pone roja con cada uno. La primera vez, **dos de tres mutaciones pasaron**: los
tests estaban escritos para casos que la fixture no contenía — un test que no puede fallar, que
es exactamente por lo que se retiró el check 12. Y una séptima mutación destapó **código
muerto** en el propio `cb.py` (una poda de alias que nunca podía dispararse).

**Antes de tocar `cb.py`, corre los tests. Después de tocarlo, rompe algo a propósito y
comprueba que se ponen rojos.** Un derivado que escribe frontmatter en mil ficheros con una
suite verde que no caza nada es peor que no tener suite.

**No es una novena acción.** Se dobló dentro de `health` a propósito: el ritual semanal ya
mira ahí, y una acción más habría sido superficie nueva para algo que ya tenía sitio.

## Acción: `enrich` (v0.5.0)

Octava acción del motor — mismo patrón que la skill de `enrich` del vault personal, si existe: mejora la recuperación **sin tocar el contenido** de las notas, solo `search_terms` y la sección de conexiones. Acción aparte y no un paso de `maintain` porque `maintain` tiene el invariante "nunca edita el cuerpo ni el frontmatter salvo campos de mantenimiento" — normalizar `search_terms` o proponer `connections:` es edición, y romper ese invariante saldría más caro que una acción más.

1. **Normaliza**: para cada nota, resuelve sus `search_terms` contra `ontology.json` (canónico o alias) y detecta variantes que deberían reescribirse a la forma canónica. Propone la lista completa de cambios (nota → término viejo → término nuevo) para aprobar **en bloque** — no cambia nada hasta que la persona confirme la lista.
2. **Propone candidatos**: términos libres (sin match en la ontología) que se repiten ≥3 veces en el canon → candidatos a entrar en `ontology.json`. Se presentan con su clase sugerida (`product-feature`/`channel`/`integration`) y las notas donde aparecen — la persona decide clase por clase, término por término, o descarta.
3. **Audita**: términos huérfanos (aparecen una sola vez, no son necesariamente un problema — solo se reporta el %), notas por debajo del mínimo de `search_terms` (C3), y deriva ontología↔glosario (un término con entidad en `ontology.json` que también debería tener `GL-`, o viceversa).
4. **Conecta (Pilar B)**: propone `connections:` candidatas entre notas que comparten ≥2 entidades de la ontología o el mismo `problem_tag`/cluster temático, **con el verbo sugerido (C27) y una frase de por qué**. La persona confirma, corrige el verbo, o descarta — nota a nota (C2). Nunca se escribe una conexión sin confirmación, y nunca se fuerzan links por completismo (**G13** — un grafo con pocas aristas ciertas vale más que uno denso de aristas dudosas). Si dos notas propuestas parecen contradecirse, se marca como candidata a `contradice` y sigue la regla de C28 — no se resuelve aquí, se encola.
5. **Escanea el cuerpo contra la ontología**. Los pasos 1-2 solo miran `search_terms` ya escritos — pero una nota puede mencionar "Checkout" o "Webhook" en el cuerpo sin haberlo declarado como `search_term`, y eso es invisible para el graph walk aunque el término esté justo ahí. Este paso busca en el **cuerpo** de cada nota, con coincidencia de palabra completa (no substring), cada entidad de `ontology.json` (canónico + aliases) que aparezca literalmente en el texto y no esté ya en `search_terms`, y propone añadirla. Solo añade el wikilink a `search_terms` — nunca reescribe ni reformatea el cuerpo. Aprobación **en bloque** como el paso 1 (es un match textual verificable, no una inferencia): la persona ve la lista completa nota→términos-a-añadir antes de escribir nada.

Reporte: mismo formato que `maintain`/`health`, en `Context/_reports/Run-enrich-<fecha>.md` — cambios de normalización aplicados (tras aprobación), candidatos pendientes de decisión, conexiones confirmadas/descartadas, huérfanos, links de cuerpo añadidos.

**Nunca actúa por su cuenta** en los pasos 2 y 4 (candidatos y conexiones son siempre propuesta, C2/G13). Los pasos 1 y 5 sí se aplican una vez que la persona aprueba la lista completa, no nota a nota — son mecánicos una vez hay match textual verificado contra una entidad ya existente en la ontología.

---

## Los dos grafos (v0.7.0)

Hay **dos**, y no se mezclan. Confundirlos sería lo peor que le puede pasar a este canon.

| | `graph.jsonl` | `entity-graph.jsonl` |
|---|---|---|
| Qué es | juicio humano: nota ↔ nota con los 4 verbos de C27 | derivación mecánica del frontmatter |
| Tamaño (despliegue real) | 50 aristas | ~5.600 aristas · ~3.450 nodos |
| Quién lo escribe | `enrich` paso 4, arista por arista con confirmación (C2) | `python3 tools/cb.py grafo --write`, en segundos |
| Si se pierde | **no se recupera**: es criterio, no dato | se regenera |
| Aristas | `refuerza` · `contradice` · `extiende` · `depende-de` | ver abajo |

El derivado **incorpora las 50 humanas por referencia**, marcadas `method: humano`, para poder
recorrer los dos a la vez sin copiar ni regenerar nunca las buenas.

### Los verbos del grafo derivado

`decide_sobre` (DL→cliente) · `observa_a` (OB→cliente) · `mapea_a` (CM→cliente) ·
`describe_para` (PR→cliente) · `planifica_para` (Plan→cliente) · `trata_de` (nota→entidad) ·
`es_problema` (OB→problem_tag) · `afecta_a` (problema→cliente, **con fecha**) ·
`usa_canal` / `menciona_canal` (cliente→familia de canal) · `fuente_de` (Source→notas que
produjo) · `es_de_tipo` (nota→tipo).

Tres propiedades que hacen que este grafo se pueda servir sin mentir:

1. **Cada arista dice de dónde sale** (`declared_via`, `declared_on`, `method`) — C32.
2. **Las aristas débiles están tipadas como débiles.** Una mención de cliente en el cuerpo
   entra como `menciona` con `weight: 0.3`, nunca como `decide_sobre`. C30 dice que mencionar
   no atribuye; el grafo es el sitio donde la mención sí cabe, con otro nombre y otro peso.
   Por defecto los recorridos las omiten (`--debiles` las incluye). En un despliegue real, 291.
3. **Un cliente es un solo nodo.** Si un `search_terms` es el nombre de un cliente conocido,
   la arista va al nodo de cliente y no a un nodo de entidad homónimo. Sin esto el mismo
   cliente vive dos veces y ningún recorrido encuentra todo lo suyo — es el objeto entero de
   tener entidades resueltas, y la primera versión de este grafo lo tenía mal.

### Recorrerlo

```bash
python3 tools/cb.py vecinos --nodo "Acme Build"                       # la ficha del cliente
python3 tools/cb.py vecinos --nodo "WhatsApp" --rel usa_canal,afecta_a --saltos 2
python3 tools/cb.py cruce  --canal WhatsApp --problema handoff
```

`--nodo` acepta una ruta, un `cid-XXXX`, un nombre o alias de cliente, o un `problem_tag`. El
nombre de un cliente resuelve **siempre** a su nodo de cliente. Si el texto casa con varios
nodos, el comando lo dice y no elige.

Las aristas que salen de una nota **llevan la fecha del evento**, y `vecinos` ordena por ella
dentro de cada verbo: la ficha de un cliente sale cronológica, no como una lista.

### La clase de una entidad se decide a mano

`entities.json` se regenera, así que cualquier juicio escrito allí se perdería. Las decisiones
sobre entidades viven en **`entities-overrides.json`**, que se edita a mano, nunca se
regenera, y la reconstrucción respeta. Mismo principio que los dos grafos (C36).

Se midió si la clase (`customer` · `person` · `partner` · `reseller` · `competitor`) se podía
derivar del texto y **no se puede**: buscar «competidor» marcaba como competidor a clientes de
los que se habla de la competencia, y «agencia» marcaba a 32 de 113. Así que se clasifica solo
con evidencia inequívoca —el marcador va en el propio nombre canónico— y el resto queda
`customer` con `class_via: "por defecto — nadie la ha decidido"`, que es más honesto que una
etiqueta inventada. `system` y `feature` **no** viven aquí: son `product-feature` /
`integration` / `channel` de `ontology.json`, y dos vocabularios para lo mismo divergen.

**Qué NO hace este grafo**: no se usa para expandir resultados de búsqueda. En el vault
personal eso está medido y con leave-one-session-out aporta ~4 pp, no los ~23 que aparentaba.
Sirve para **responder preguntas estructuradas**, que es otro uso y no hereda ese negativo.

## Apuestas — `bets.jsonl` (v0.7.0)

Una decisión registrada dice qué se decidió. Una **apuesta** dice qué tendría que pasar
para saber si fue buena, y cuándo se mira. Es lo que convierte el canon de un archivo en
algo falsable.

Vive en `Context/_skill-config/bets.jsonl`, una línea por apuesta:

```jsonc
{"id": "bet-0001", "date": "2026-09-09", "status": "open",
 "claim": "la afirmación que se está apostando",
 "prediccion": "el resultado observable, con número y umbral",
 "deadline": "2026-10-09",
 "metrica": "log.con_notas_usadas",        // id de metrics.json, si aplica
 "que_cierra": "el procedimiento exacto para comprobarlo",
 "si_falla": "qué se hace entonces — decidido AHORA, no cuando duela",
 "origen": "de dónde salió la apuesta"}
```

Al cerrarla se añade `closed` y **`evidence`: qué pasó de verdad**, incluso —sobre todo—
cuando la acción resultó equivocada. Una apuesta cerrada cuya evidencia contradice su
`claim` es más valiosa que diez abiertas: es una supersesión con fecha y motivo.

**Por qué es un JSONL y no un décimo tipo de nota.** La v0.3.x lo diseñó como tipo `bet`
con frontmatter, `query_ref` a una `metric` y ciclo de vida propio; llevaba un mes con
cero notas. Ocho campos con estados `open`/`closed` son una línea de JSONL, no una nota
con caducidad, dueño, `search_terms` y validación. El mecanismo equivalente del vault
personal es exactamente esto y tiene veintitantas apuestas cerradas. Se elige la forma que
funciona y se retira el tipo — un tipo menos, no uno más.

Reglas:

- El campo `si_falla` se escribe **al abrir**, nunca al cerrar. Decidir qué harás si
  fallas cuando ya sabes que has fallado no es una predicción, es una excusa.
- Una apuesta sin `deadline` no se abre.
- `health` check 15 trae las vencidas sin cerrar; `metrics.json` las gatea en 3.
- No se borra una apuesta perdida. Se cierra con su evidencia.

## Relación con un vault personal — dos jurisdicciones, no una compartida

La skill de salud de un vault personal de conocimiento (second brain), si existe, gobierna ese vault; la acción `health` de esta
skill gobierna el canon de un proyecto. Comparten vocabulario (staleness, contradicción,
validación) porque heredan el mismo contrato epistémico, no porque sean el mismo sistema.
La frontera es **C15** y es dura en las dos direcciones: si un hallazgo es del pipeline
Literature Notes → Permanent Notes, es del vault personal aunque el tema sea el canon.

## Constraints

C1 — Nunca duplicar contenido de Notion — un `context-map` que apunta, nunca una copia.
C2 — Nunca crear/resolver nada sin aprobación explícita de la persona que está usando la skill (capture pregunta, maintain solo marca, validate requiere confirmación humana).
C3 — Mínimo 4 `search_terms` por nota, objetivo 6.
C4 — Todo link externo va en `external_urls`, no solo en el cuerpo.
C5 — Pre-flight (rungs 1-5 de `capture`) es obligatorio antes de crear.
C6 — Las `observation` son privadas por defecto (`shareable: false`) — nunca se comparten/publican fuera del vault. Excepción explícita y siempre confirmada por la persona: una `observation` sobre un **problema de producto/runtime que afecta a clientes reales** puede marcarse `shareable: true` — en ese caso, su `problem_tag`, conteo de `occurrences`, nombre real y `client_id` sí pueden salir en un reporte para el equipo. Todo lo que sea gap de documentación/proceso interno se queda siempre `shareable: false`, sin excepción.
C7 — JIRA por defecto al proyecto que corresponda; preguntar si no está claro.
C8 — La expiración es una feature: toda nota nace con `expires_on`.
C9 — `metric` requiere las 3 piezas del lint (definición + qué NO cuenta, vista canónica, gotchas) antes de `validated: true`.
C10 — Nunca inventar un `query_ref` — `TODO` si no existe todavía.
C11 — `metric` es solo definición. Nunca un objetivo (eso es una apuesta en `bets.jsonl`, ver § Apuestas) ni una lectura puntual (eso es una consulta en vivo, o evidencia dentro de un `decision-log`).
C12 — `maintain` nunca inventa el resultado de un hook que no puede ejecutar — `skipped`, siempre.
C13 — `validate` nunca presenta más de 5 notas por sesión, sumando todos los proyectos si aplica.
C14 — `health` nunca mueve, archiva ni borra un archivo por su cuenta — solo reporta y propone; la ejecución requiere confirmación explícita de la persona, archivo por archivo.
C15 — `health` nunca escanea `Literature Notes/`, `Permanent Notes/`, `Manuscripts/`, `Cases/` ni `Inbox/` — esa jurisdicción es del vault personal y de la skill de salud del vault personal, si existe, no de esta skill.
C16 — Ningún documento de trabajo (PDF de análisis/síntesis/propuesta) generado por esta skill cierra su sesión sin nota-índice o entrada en el tablero de tareas del equipo — ver regla en § Acción `capture`.
C17 — El nombre real del cliente y de la empresa se escriben directamente: en el cuerpo/frontmatter de la nota, en el reporte final de `extract`, y en el título de la entrada de `extraction-log.jsonl` — no se ocultan tras un pseudónimo. **Decisión explícita del dueño del canon, 2026-08-06** — revierte la política de anonimato original de v0.2 (que este mismo campo aplicaba). `client_id` sigue existiendo, pero solo como clave interna estable para agregación estructurada (`occurrences`, conteo, dedup por `problem_tag`) — nunca derivada de una etiqueta de sector+tamaño (esa etiqueta es un bucket, colisiona entre clientes distintos). El mapeo `client_id` ↔ nombre real vive en `client-directory.json`, que ya no es secreto: puede leerse desde `manifest`, `retrieve` compartido o cualquier reporte.
C18 — Toda `observation shareable: true` mantiene `occurrences` como lista estructurada (fecha + `client_id` + `transcript_ref` + cita) — nunca solo prosa libre en "Evidencia". El conteo y la lista de clientes se leen de ahí, nunca se recalculan a mano ni se mantienen en un contador aparte.
C19 — `extract` nunca reprocesa una fuente ya registrada en `extraction-log.jsonl` sin preguntar antes a la persona qué hacer con ella (reprocesar / añadir `occurrence` / nada) — el fingerprint (`source_id` estable o hash de contenido) decide si una fuente es "la misma", nunca el juicio del momento.
C20 — Ninguna credencial (API key de Fathom u otra) se escribe nunca en el vault — ni en una nota, ni en `_skill-config/`, ni en un reporte. La persona la aporta en el momento de usarla, en la sesión; si no se aporta, `extract` sigue funcionando con la fuente pegada a mano.
C21 — Como el canon vive en un repo git compartido, quien ejecute cualquier acción de escritura (`capture`, `extract`, `maintain`, `validate`, `health`) hace `git pull` sobre el repo del canon antes de empezar (para no trabajar sobre una copia desactualizada ni duplicar lo que otra persona ya capturó) y `git push` después de escribir. Nunca asumir que la copia local está al día sin comprobarlo primero.
C22 — El bounded context de vocabulario (`glossary`/`GL-`) se resuelve antes que cualquier nota que use ese término: `capture`/`extract` nunca redefinen un término dentro de otra nota si ya existe una `GL-` — enlazan por wikilink. Y nunca crean una `GL-` por especulación: solo cuando una fuente evidencia la ambigüedad o la persona la señala explícitamente (mismo principio que C19, aplicado a vocabulario en vez de a fuentes).
C23 — Toda `observation` declara `kind` (`gap-interno`/`anti-pattern`/`gotcha`/`pattern`) — `capture`/`extract` nunca la dejan sin clasificar. Ante duda entre `anti-pattern` y `gotcha`: si hay una alternativa correcta identificable, `anti-pattern`; si es puramente un límite a conocer sin alternativa, `gotcha`. `pattern` solo si el hallazgo es genuinamente positivo, no diagnóstico.
C24 — Los `verify_hooks` del track `tech` nunca corren contra un repo que no esté declarado en `_skill-config/repos` de la config del proyecto — ante duda, `skipped`, igual que C12.
C25 — Una nota migrada desde `tech-knowledge` conserva su `validated`/`last_validated` de origen — la migración nunca regala ni quita validación humana ya obtenida.
C26 — `capture`/`extract` resuelven cada `search_term` candidato contra `ontology.json` antes de escribir — match usa forma canónica, sin match se deja libre o entra como candidato en el reporte (nunca se inventa una entidad nueva sobre la marcha, ni se fuerza un término libre a una clase que no le corresponde).
C27 — El grafo tipado (`connections:`) usa 4 verbos cerrados — `refuerza`/`contradice`/`extiende`/`depende-de` — y ninguno más. No se inventan verbos nuevos fuera de estos cuatro, mismo principio que los 4 callouts canónicos del vault personal del que hereda.
C38 — Ningún cambio en `tools/cb.py` se da por bueno sin correr `tools/test_cb.py`, y ningún test nuevo cuenta hasta que se ha comprobado que se pone rojo al reintroducir el fallo que dice cubrir.
C37 — `extract` escribe `source_date` (la fecha del evento de la fuente) en `extraction-log.jsonl` en cada entrada. Es el único origen desde el que `occurred_on` se puede recuperar después; sin ella la nota queda sin eje temporal para siempre. Si la fuente no trae fecha, `source_date: null` explícito, nunca `processed_on` en su lugar.
C36 — El grafo derivado (`entity-graph.jsonl`) nunca se edita a mano: se regenera. El de juicio humano (`graph.jsonl`) nunca se regenera: se edita nota a nota con confirmación. Una arista derivada jamás se copia dentro del humano.
C34 — El log de consultas se escribe en un fichero por persona y mes. Nunca en un fichero único compartido: eso convierte cada `push` simultáneo en un conflicto de merge, y un log que da guerra deja de escribirse.
C35 — Una consulta que no se podría enseñar en el canal del equipo se registra con `query: "[omitida]"`, conservando `notas_usadas` y `gaps`. No se borra ni se edita una entrada ya escrita para esconderla después.
C33 — Toda entrada del log de consultas lleva `session_id`, y ninguna señal derivada del log (contadores de uso, aristas de co-uso, priors aprendidos) se evalúa contra el propio log sin holdout por sesión.
C29 — `occurred_on` nunca se rellena copiando `captured_on`. Si no se conoce la fecha del evento, se deja vacío: el hueco es el dato (ver § Los dos relojes).
C30 — Mencionar a un cliente en el cuerpo de una nota no le asigna `client_name`. La atribución la da el título del fichero o la persona que captura; una mención es una arista `menciona` del grafo. `metric`, `glossary` y las notas del track `tech` nunca llevan `client_name`.
C31 — Ningún umbral vive en esta skill. Los umbrales están en `_skill-config/metrics.json`, cada uno con su razón escrita y su fecha de baseline. Un número puesto en la prosa de la skill es un número que nadie audita.
C32 — Toda arista de `graph.jsonl` lleva `declared_on` y `declared_via`. Una arista sin procedencia no se distingue de una inventada, y se sirve con la misma autoridad que una que confirmó una persona.

C39 — `capture`/`extract` nunca registran una cifra de rendimiento, tiempo o tasa citada por un cliente o el equipo ("tardó X segundos", "el Y % de las veces") como si fuera una medición. Cada `occurrence` de una `observation`, y el cuerpo de cualquier nota que cite un número así, declara `evidence_basis: measured` (hay metodología reproducible detrás: instrumentación, logs, timing controlado) o `evidence_basis: client-reported` (lo contó quien lo vivió en una llamada o transcript, sin medición detrás; es el caso por defecto de lo que trae Fathom o una conversación pegada). Sin metodología conocida nunca es `measured`: se pregunta a la persona o se deja `client-reported`. Un campo ausente se lee como `client-reported`. Consecuencia: ninguna nota, `retrieve`, `manifest` ni documento presenta una cifra `client-reported` con lenguaje de "documentado", "medido" o "benchmark"; el hallazgo es el síntoma reportado, no el número exacto, y se dice así. Motivado el 2026-09-15: documentos de salida (informes, análisis) citaron latencias de cliente como evidencia documentada enlazando notas que nunca existieron, y la cifra se volvió más sólida en cada repetición sin que nadie la re-verificara contra su origen.

C28 — Declarar una conexión `contradice` entre dos notas nunca marca `contradicted` por su cuenta — ese campo sigue reservado a hooks contra la realidad externa (`maintain`). Encola ambas notas en `validation-queue.json` con prioridad máxima; un humano decide en `validate` cuál sobrevive.

## Gotchas

G1 — Falso negativo en pre-flight: buscar con variaciones de keyword antes de recomendar crear.
G2 — Sobre-capturar en `extract`: sintetizar en una nota, no una por queja/tangente.
G3 — Enlaces de `context-map` que se pudren — solo se detecta si `external_urls` estaba bien poblado.
G4 — Ruido de búsqueda JIRA — filtrar por proyecto y actividad reciente.
G5 — `metric` sin cerrar (como un `MET-activation` cuya definición aún no se ha cerrado) no es un fallo del sistema — es el hueco real que la nota existe para hacer visible.
G6 — La detección de duplicados de `health` es heurística (título + fecha, no hash de contenido) — puede dar falsos positivos entre dos documentos genuinamente distintos que comparten vocabulario. Ante duda, "revisar a mano", nunca archivar automáticamente.
G8 — El fingerprint de fuente no es perfecto: un hash de texto exacto no detecta un "casi el mismo" transcript (recortado, con una corrección de nombre, re-exportado por Fathom con timestamps ligeramente distintos). Cuando la fuente trae un identificador estable (`recording_id` de Fathom, ID de thread) ese es el criterio fuerte; el hash de contenido es solo la red de seguridad para cuando no hay ID. Ante duda razonable de "esto ya lo vi pero no coincide exacto", preguntar a la persona en vez de fiarse ciegamente del fingerprint.
G9 — Dos personas ejecutando `capture`/`extract`/`maintain` sobre el mismo proyecto casi a la vez, sin haber hecho `git pull` cada una (C21), pueden duplicar trabajo o acabar en conflicto de merge en ficheros que varias personas tocan el mismo día (`manifest.json`, `extraction-log.jsonl`, `client-directory.json`, o incluso la misma nota `Context/`). `git pull` justo antes de escribir no protege contra alguien que escribe *después* de ese pull y *antes* de que la primera persona haga `push` — reduce el riesgo, no lo elimina. Si aparece un conflicto de merge en cualquiera de esos ficheros, resolverlo a mano nota por nota — nunca sobreescribir en bloque ni elegir "la mía" por defecto.
G10 — Sobre-capturar `glossary`: no cada palabra que usa el equipo necesita una `GL-` — solo términos donde ya hubo o hay riesgo real de confusión entre personas, evidenciado por una fuente o señalado explícitamente, igual que G2 ya advierte para `extract` en general.
G11 — `kind` no sustituye a `problem_tag`: dos notas del mismo `kind` (dos `gotcha`, por ejemplo) siguen siendo problemas distintos si tienen `problem_tag` distinto — `kind` es la categoría del hallazgo, `problem_tag` es la clave de dedup de ESE hallazgo específico. No usar `kind` como criterio de duplicate-check en el paso 5 de `extract` — sigue siendo `problem_tag`.
G12 — La ontología (`ontology.json`) no es taxonomía de carpetas: clasifica términos, no notas. Una nota no "pertenece" a una entidad — la menciona. No crear subcarpetas ni convenciones de naming a partir de las clases de la ontología.
G13 — No forzar links ni clases por completismo: si un término no encaja limpio en ninguna de las 3 clases nuevas (`product-feature`/`channel`/`integration`), se deja libre — no se fuerza a la clase más parecida. Lo mismo con `connections:`: un grafo con pocas aristas ciertas (confirmadas por una persona) vale más que uno denso de aristas dudosas propuestas por volumen. Visto en la práctica en Fase 1 de la Propuesta v0.5 (2026-08-08): 7 de 55 términos candidatos se dejaron libres a propósito en vez de forzarlos a una clase.

## Qué falta

En `references/estado-y-pendientes.md`, no aquí. Quince puntos de estado —qué está bloqueado
por falta de datos, qué espera juicio humano, qué es dependencia externa y qué está fuera de
alcance a propósito— con la razón de cada uno.

Vive fuera del cuerpo porque **es estado, y el estado caduca**: esta sección llevaba un mes
diciendo «264 notas» y «528 notas» con el canon cuatro veces más grande. Un número dentro del
prompt es un número que nadie audita (C31).

La versión que no caduca son los gates:

```bash
python3 tools/cb.py gates     # qué está en rojo hoy, y contra qué umbral
python3 tools/cb.py stats     # el estado del canon en números
```
