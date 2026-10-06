# Contrato de notas — el detalle por tipo

Referencia de `SKILL.md` de `company-brain`. **Se lee al crear o editar una nota**, no al
activar la skill: vive fuera del cuerpo porque el 90 % de las invocaciones no crean notas y
no deben pagar estos campos en contexto. El frontmatter común, los dos relojes y los campos
de cliente sí están en `SKILL.md`, porque los toca cualquier acción.

Movido aquí en la v0.7.0 desde el cuerpo de la skill (1553 palabras). Nada se reescribió:
es el mismo texto, en el sitio donde cuesta cero tokens hasta que hace falta.

---

## Campos extra de `metric`

```yaml
query_ref: "TODO" | "amplitude:<chart_id>" | "metabase:<question_id>"   # NUNCA inventar un id — TODO si no existe
verify_hooks: [chart_exists, event_exists, query_runs]   # declarados, inertes hasta que exista wiring MCP
definition_includes: "Qué cuenta, en una frase sin ambigüedad"
definition_excludes: "Qué NO cuenta — la parte que se skippea y causa re-litigar la definición"
```

## Campos extra de `glossary`

```yaml
term: "Nombre canónico del término — tal como se debe usar de aquí en adelante"
aliases: []                          # variantes/sinónimos que la gente usa para el mismo término
contrasts_with: "[[GL-otro-termino]]" # el término con el que se confunde — casi siempre viene en pareja
canonical_definition: "Una frase, sin ambigüedad, sin jerga que necesite otra nota a pie de página"
not_to_say: []                       # opcional — palabras que este término sustituye porque significaban cosas distintas para cada persona
```

`glossary` se resuelve antes que los demás tipos, no después: si una `CM-`/`OB-`/`DL-`/`PR-` va a usar un término que ya tiene `GL-`, se enlaza por wikilink en vez de redefinirlo en el cuerpo — el bounded context vive en un solo sitio, nunca se repite la definición nota por nota.

## Campos extra de `observation`

Todo `observation` — shareable o no — declara qué tipo de hallazgo es, para que la nota no sea un cajón desastre de "algo pasó":

```yaml
kind: gap-interno | anti-pattern | gotcha | pattern
```

- `gap-interno` — diagnóstico privado de documentación/proceso interno de la empresa, no un problema que un cliente haya sufrido en producción. Casi siempre `shareable: false`.
- `anti-pattern` — fallo de producto/runtime con causa raíz identificable (aunque sea hipótesis, no confirmada) y una alternativa correcta implícita o explícita — el foco es "esto se hizo/pasó mal y hay una forma mejor".
- `gotcha` — trampa o límite de plataforma que se descubre cuando ya duele en producción, sin que haya necesariamente una "forma correcta" — es una limitación a conocer, no un error a corregir.
- `pattern` — algo que funciona bien y por qué. Raro dentro de `observation`, que por diseño captura diagnóstico de lo roto — existe para un hallazgo positivo que no encaja como `process` (que describe cómo funciona una feature, no una estrategia o comportamiento del cliente que vale la pena repetir).

Motivado el 2026-08-06: al comparar contra el esquema de 7 capas de una skill hermana de experto de dominio (`pattern`/`decision`/`anti-pattern`/`benchmark`/`playbook`/`gotcha`/`architecture`), se señaló que `observation` estaba absorbiendo distinciones reales sin marcarlas — la misma incidencia de alucinación de URLs está tipada `anti-pattern` en el vault hermano, aquí era solo "observation" genérica. Se decidió no adoptar los 7 tipos completos: `benchmark`/`playbook`/`architecture` no tienen todavía ningún caso de uso real en este canon, y añadir carpetas/prefijos nuevos sin que nadie dependa de ellos repetiría el error que la Decisión de 2026-08-02 ya advertía evitar (§8, criterio de admisión de tipos). En su lugar, `observation` gana `kind` como campo obligatorio — mismo movimiento que ya se hizo con `shareable` (campos extra sobre el modelo común, no un tipo nuevo). Aplicado retroactivamente a las 34 `observation` existentes en ese momento — ver `CHANGELOG.md` v0.3.8.

## Campos extra de `observation` cuando es `shareable: true`

Solo para observaciones sobre un **problema de producto/runtime que afecta a clientes reales** — nunca para diagnóstico de documentación/proceso interno, que se queda `shareable: false` (el default, sin estos campos).

```yaml
shareable: false                  # true solo con confirmación explícita de la persona que usa la skill — nunca inferido en silencio
problem_tag: "slug-estable"       # ej. "prompt-truncation-on-duplication" — mismo problema, mismo tag, siempre
severity: high | medium | low     # impacto técnico/de producto, no de documentación
client_name: "Nombre real de la empresa cliente"   # visible — decisión de equipo, se quiere que se vea quién era el cliente (ver C17)
client_id: []                     # clave interna estable para agregación (conteo/dedup) — no sustituye a client_name, no oculta nada
occurrences:                      # lista estructurada — NUNCA solo prosa libre en "Evidencia" (ver C18)
  - date: YYYY-MM-DD
    client_id: "cid-xxxx"
    transcript_ref: "referencia a la fuente (puede nombrar al cliente/contacto — ver C17)"
    quote: "cita corta, en prosa, del problema tal como se reportó"
    evidence_basis: client-reported   # measured | client-reported — obligatorio si la cita trae una cifra (ver C39); ausente = client-reported
```

`len(occurrences)` es el conteo de repetición — nunca un contador aparte que haya que sincronizar a mano. El set de `client_id` únicos en `occurrences` es la respuesta rápida a "qué clientes tuvieron este problema" — pero el nombre real (`client_name` en frontmatter, o directamente en el cuerpo) es lo que se muestra, no un pseudónimo.

## Campos extra del track `tech`

```yaml
repo: "api-core"               # repo(s) al que refiere la nota
related_files: []               # paths del repo, verificados al capturar
modules: []                     # áreas/módulos clave (lowercase, kebab-case)
severity: high | medium | low   # solo `gotcha` — boost ×1.3 en retrieve si high
sync_last_checked: null         # solo si source_of_truth: external
derives: []                     # notas derivadas de una reference externa que cambió
see_also: []
verify_hooks:                   # idéntico al esquema real de tech-context-maintain — objetos, no strings
  - type: file_exists           # ¿siguen existiendo los related_files?
    target: related_files
  - type: grep_repo             # ¿el repo aún contiene este símbolo/patrón?
    repo: web-widget
    pattern: "showFreeInput"
    expect: present             # present | absent
  - type: package_version       # ¿la versión declarada sigue vigente?
    repo: api-core
    package: "react"
    expect: "^18"
  - type: reference_hash        # ¿cambió el cuerpo de la reference externa?
    source: external_source_url
```

`inventory-repo` añade además `auto_generated: true` y `generated_by` (script que la escribió) — nunca se edita a mano; el cambio va al script de sync, no a la nota (mismo principio que `tech-context-sync` ya aplicaba).

## Campos extra de `reference` (track `tech`, desde v0.6.0)

```yaml
external_source_url: "local-repo://..." | "https://..."   # o "local-upload" para archivos offline
external_source_type: notion | confluence | gdocs | url | pdf | md
sync_interval_days: null | <int>    # solo si source_of_truth: external
derives: []                          # wikilinks a notas auto-extraídas de esta reference
people_consulted: []                 # opcional — quién aportó el conocimiento mirrorado
involves: []                         # opcional — paquetes/entidades técnicas que cubre
```

## Campos extra de `plan` (track `tech`, desde v0.6.0)

```yaml
target_completion: YYYY-MM-DD   # fecha de corte del plan
version: <float>                 # el plan se versiona en el propio archivo, no por historial de notas
last_updated: YYYY-MM-DD
involved_repos: []               # repos que toca el plan (puede ser más de uno)
```

## Campos de mantenimiento (los escribe la acción `maintain`, nunca a mano)

```yaml
last_verified: YYYY-MM-DD | null
contradicted: true | false
contradicted_on: YYYY-MM-DD | null
contradicted_by: "hook + evidencia, en prosa"
review_due: true | false
superseded_by: null | "[[nota-más-nueva]]"
```

## Naming y carpetas

`<prefijo>-<slug>.md` — `CM-`, `OB-`, `DL-`, `PR-`, `MET-`, `GL-`, `Sys-`, `Run-`, `Got-`, `Inv-`, `Ref-`, `Plan-`. **Desde v0.3.5, cada tipo vive en su propia subcarpeta dentro de `Context/`** — antes los 4 tipos (menos `metric`) estaban sueltos en la misma carpeta plana. El prefijo se mantiene igual y sigue siendo la forma rápida de identificar el tipo por nombre de archivo; la subcarpeta es redundante con el prefijo a propósito. Las `OB-` con `shareable: true` no cambian de prefijo ni de subcarpeta — se distinguen por el campo, no por dónde viven. `GL-` (desde v0.3.6) sigue el mismo patrón que `Metrics/`: subcarpeta propia (`Glossary/`), sin mezclarse con los otros cuatro tipos sueltos.

```
<repo>/
├── skill/SKILL.md                        # esta skill (+ references/)
├── tools/cb.py                           # el instrumento — ver § El instrumento en SKILL.md
└── {proyecto}/                           # ver v0.3.2 — todo el canon de este proyecto vive aquí, autocontenido
    ├── manifest.md  manifest.json        # índice de ESTE proyecto — ver § Acción `manifest`
    └── Context/
        ├── context-maps/CM-*.md          # ver v0.3.5 — antes sueltos en Context/
        ├── observations/OB-*.md          # ver v0.3.5 — antes sueltos en Context/
        ├── decision-logs/DL-*.md         # ver v0.3.5 — antes sueltos en Context/
        ├── processes/PR-*.md             # ver v0.3.5 — antes sueltos en Context/
        ├── Metrics/MET-*.md              # sin cambios desde v0.2
        ├── Glossary/GL-*.md              # desde v0.3.6 — bounded context de vocabulario compartido
        ├── Tech/                         # desde v0.4.0 — track `tech`, ver D1-D2 en el decision-log de integración
        │   ├── systems/Sys-*.md  runbooks/Run-*.md  gotchas/Got-*.md   # capturados a mano
        │   ├── inventory/Inv-*.md        # inventory-repo — auto-generado por sync, nunca a mano
        │   ├── references/Ref-*.md       # desde v0.6.0 — mirror de fuente externa
        │   └── plans/Plan-*.md           # desde v0.6.0 — planes activos multi-semana; puede contener subcarpetas de trabajo (prompts, specs) migradas tal cual, sin contrato de frontmatter
        ├── _skill-config/
        │   ├── validation-queue.json
        │   ├── retrieval-log.jsonl
        │   ├── extraction-log.jsonl        # huella de cada fuente ya procesada por extract — ver C19
        │   └── client-directory.json      # mapea client_id → nombre real, para agregación estructurada — el nombre real también puede citarse en manifest/reportes (ver C17)
        ├── _reports/Run-maintain-<fecha>.md  Run-health-<fecha>.md
        └── _README.md
```

`_skill-config/`, `_reports/` son máquina, no árbol de conocimiento: ninguna acción los trata como notas. `client-directory.json` sigue siendo el índice de referencia de `client_id` ↔ nombre real, pero ya no es secreto: puede citarse en `manifest`, `Run-maintain`/`Run-health` o cualquier artefacto que salga del vault (ver C17 — decisión explícita del dueño del canon, 2026-08-06, revierte la política de anonimato de v0.2). Esto incluye subir la carpeta `{proyecto}/` entera al repo git compartido tal cual — misma decisión.

**Documentos de trabajo fuera de `Context/`** (PDFs de análisis, documentos de estado/decisión) no siguen esta convención de prefijo — pero `health` los cubre igual: ver § Acción `health`.

---
