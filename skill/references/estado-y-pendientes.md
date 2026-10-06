# Estado y pendientes del canon

Referencia de `SKILL.md` de `company-brain`. **Vive fuera del cuerpo de la skill a**
**propósito**: son quince puntos de *estado*, y el estado caduca. Un número dentro del
prompt es un número que nadie audita ni actualiza (C31) — esta misma sección llevaba un mes
diciendo «264 notas» y «528 notas» cuando el canon tenía cuatro veces más.

**Léelo cuando**: alguien pregunte qué le falta al canon, antes de proponer una mejora, o
antes de decidir en qué gastar una sesión. No al activar la skill.

**Antes de citar cualquier cifra de aquí, corre `python3 tools/cb.py stats` y
`python3 tools/cb.py gates`.** Los gates son la versión viva de esto y no caducan.

---

Medido el 2026-09-09 en un despliegue real (~1.300 notas) con `python3 tools/cb.py stats`. **Corre el comando antes de fiarte de
estas cifras**: durante la propia sesión que escribió esta sección el canon pasó de 1.103 a
1,298 notas. Un número dentro del prompt es una foto (C31).

### Bloqueado por falta de datos, no de diseño

1. **El log de consultas tiene 4 entradas.** Es el cuello de botella de todo lo demás: sin
   consultas con `notas_usadas` no hay gold, y sin gold no se puede medir ni un prior por
   tipo, ni el ×1.3 de `gotcha`, ni si el grafo aporta al retrieval. `log.con_notas_usadas`
   está **en rojo** a propósito. `bet-0001` dice qué hacer si en 12 consultas no se puebla:
   mover el paso al disparo automático, **no** escribir más prosa aquí.
2. **Prior por tipo de nota en `retrieve`.** El candidato es obvio —degradar `source-raw`
   (290 notas, 22 % del corpus, casi nunca es la respuesta— y subir
   `decision-log`/`context-map`. En el vault personal el equivalente dio +15,1 pp en
   validación cruzada. **No se implementa sin medir**: precondición `log.volumen ≥ 30` y
   control negativo. Ponerle un número hoy sería repetir el ×1.3.
3. **El ×1.3 de `gotcha severity: high` no está medido.** Constante puesta a ojo, marcada
   como tal en `retrieve`. Misma precondición que el 2.

### Esperando juicio humano

4. **`validate` casi no se ha corrido sobre el canon**: 38 de 744 notas de negocio
   validadas. Es la única puerta de juicio humano del sistema y la que más cambiaría lo
   fiable que es todo lo demás. El gate `validacion.canon` avisa por debajo del 20 %.
5. **Supersesión: 1 de 223 decision-logs** con `supersedes`. Ya no falta mecanismo
   —`occurred_on` lo hace computable— sino lectura: `_reports/contradictions.md` tiene los
   candidatos, regenerable. `bet-0002` dice qué concluir si ninguno resulta real.
6. **78 ficheros sin contrato dentro de `Context/`** (check 13), casi todos de
   un mismo plan bajo `Tech/plans/`. Decisión: darles contrato o moverlos fuera de `Context/`.
   No se tocan (C14).
7. **La clase de 113 entidades no la ha decidido nadie.** Se midió que no se puede derivar del
   texto (falsos positivos: «competidor» marcaba clientes, «agencia» marcaba 32 de 113), así
   que se decide a mano en `entities-overrides.json`, que la regeneración respeta.
8. **`occurred_on` en 403 de 1008 notas con ciclo de vida.** El 100 % de las
   *recuperables* lo tiene (ahí está el gate); el resto son notas capturadas a mano cuya
   fuente no trae fecha, y esas solo las puede fechar una persona. Nunca copiando
   `captured_on` (C29).

### Dependencias externas

9. **Hooks de `metric` sin cablear** (`chart_exists`, `event_exists`, `query_runs` contra
   Amplitude/Metabase) — `maintain` los reporta siempre `skipped` (C12). Por eso el apartado
   1 de `contradictions.md` no puede tener contenido todavía.
10. **`git pull`/`push` (C21) es una convención manual.** Nada comprueba que se haya hecho ni
    avisa de dos personas escribiendo a la vez (G9). Durante la sesión del 2026-09-09 esto
    pasó de verdad: otra sesión añadió 195 notas mientras se editaba la skill.
11. **No hay guía de usuario para el equipo en el repo abierto.** El README explica el
    sistema a quien lo instala; una guía para quien solo lo consulta es por despliegue, y
    cada empresa escribe la suya.
12. **Solo 23 `glossary` y 25 `metric`.** Los tipos funcionan; la cobertura de vocabulario
    compartido sigue fina, y no se fuerza (G10).

### Fuera de alcance a propósito

13. **Sin MCP.** Este canon se consulta con la skill sobre el filesystem. Las palancas de
    retrieval que viven en un indexador servido —stemming, expansión de query, boosts
    léxicos, `expand: entity`— no aplican aquí. Están inventariadas en el plan del vault personal.
14. **El grafo derivado no se usa para expandir búsquedas**, solo para responder preguntas
    estructuradas. En el vault personal la expansión por grafo aporta ~4 pp con
    leave-one-session-out, no los ~23 que aparentaba.
15. **Grafo visual.** Fase 4 del plan, marcada opcional y dependiente de que la expansión
    por entidad demuestre valor. No se ha hecho y no bloquea nada.

Ninguna bloquea el uso de las ocho acciones ya descritas.
