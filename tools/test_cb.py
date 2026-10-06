#!/usr/bin/env python3
"""Tests de `cb.py`. Sin dependencias: `python3 tools/test_cb.py`.

Por que existen: `cb.py` escribe frontmatter en mas de mil ficheros del canon y llego a
1.500 lineas sin una sola prueba. En una sola sesion metio dos bugs que solo se cazaron
mirando la salida a ojo — el parser de fechas ignoraba las entrecomilladas (infracontaba
ocurrencias) y un cliente vivia dos veces en el grafo (`vecinos` devolvia media ficha sin
avisar). Los dos habrian salido aqui en un segundo.

Se prueba contra `tools/fixture/`, una canon sintetica de siete notas, **nunca contra el
canon real**: el real no es determinista (mientras se escribia esto otra sesion le metio 195
notas) y no debe ensuciarse con escrituras de prueba.

Cada caso de la fixture existe por un bug concreto o por una regla que se puede romper en
silencio. Si anades un caso, escribe cual.
"""
import json, os, shutil, subprocess, sys, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CB = os.path.join(RAIZ, "tools", "cb.py")
FIXTURE = os.path.join(RAIZ, "tools", "fixture")
fallos, corridos = [], 0


def corre(*args, base=None, **env):
    e = dict(os.environ, CB_BASE=base or FIXTURE, CB_TODAY="2026-09-09", **env)
    r = subprocess.run([sys.executable, CB, *args], capture_output=True, text=True, env=e, cwd=RAIZ)
    return r


def jsonr(*args, base=None):
    r = corre(*args, "--json", base=base)
    assert r.returncode == 0, f"{args} salio {r.returncode}: {r.stderr[-400:]}"
    return json.loads(r.stdout)


def prueba(nombre, porque):
    def deco(fn):
        global corridos
        corridos += 1
        try:
            fn()
            print(f"  ok    {nombre}")
        except AssertionError as exc:
            fallos.append((nombre, porque, str(exc)))
            print(f"  FALLA {nombre}\n        {exc}\n        (existe porque: {porque})")
        except Exception as exc:  # noqa: BLE001
            fallos.append((nombre, porque, f"{type(exc).__name__}: {exc}"))
            print(f"  ERROR {nombre}: {type(exc).__name__}: {exc}")
        return fn
    return deco


print("cb.py — tests contra la fixture\n")

# ---------------------------------------------------------------- parseo de frontmatter

@prueba("escalares con y sin comillas cuentan igual",
        "el canon tiene `project: Kestrel` y `project: \"Kestrel\"` mezclados; un parser que "
        "distinga los dos parte el corpus en dos mitades invisibles")
def _():
    import glob, re as _re
    md = [f for f in glob.glob(FIXTURE + "/Context/**/*.md", recursive=True)]
    con_type = sum(1 for f in md if _re.search(r"^type:\s*\S", open(f, encoding="utf-8").read(), _re.M))
    d = jsonr("stats")
    # el numero sale del fixture, no clavado aqui: un contador a mano en un test es el
    # mismo error que un numero a mano en el prompt (C31), y ya me mordio en esta sesion
    assert d["corpus"]["total_con_contrato"] == con_type, (d["corpus"], con_type)
    en_disco = sum(1 for f in md if _re.search(r'^type:\s*"?decision-log', open(f, encoding="utf-8").read(), _re.M))
    assert d["por_tipo_detalle"]["decision-log"]["n"] == en_disco, (d["por_tipo_detalle"]["decision-log"], en_disco)
    # y la prueba de fondo: `normalizar` ve las entrecomilladas y no las desnudas
    n = jsonr("normalizar")
    campos = {c["campo"] for c in n["cambios"]}
    assert "project" in campos, f"no detecto los `project` entrecomillados: {n['por_campo']}"
    assert all(c["a"] == "Kestrel" for c in n["cambios"] if c["campo"] == "project"), n["cambios"][:3]

@prueba("client_id escalar y client_id lista se leen igual",
        "las dos formas existen en el canon real; leer solo una pierde clientes en silencio")
def _():
    d = jsonr("cruce")
    ids = {c for f in d["filas"] for c in f["clientes"]}
    assert "cid-0001" in ids and "cid-0002" in ids, ids

@prueba("las fechas de occurrences cuentan con y sin comillas",
        "BUG REAL 2026-09-09: el regex solo cogia `date: 2026-03-05` y no `date: \"2026-03-05\"`, "
        "asi que infracontaba ocurrencias y dejaba problemas a cero")
def _():
    d = jsonr("cruce")
    sin_comillas = [x for x in d["filas"] if x["tag"] == "widget-roto-al-cargar"]
    con_comillas = [x for x in d["filas"] if x["tag"] == "cuota-mal-contada"]
    assert sin_comillas and con_comillas, [x["tag"] for x in d["filas"]]
    assert sin_comillas[0]["ocurrencias"] == 2, sin_comillas[0]
    # este es el que cae si el regex vuelve a exigir la fecha desnuda
    assert con_comillas[0]["ocurrencias"] == 2, \
        f"fechas entrecomilladas ignoradas: salieron {con_comillas[0]['ocurrencias']} de 2"
    assert len(sin_comillas[0]["clientes"]) == 2, sin_comillas[0]["clientes"]

# --------------------------------------------------------------------------- entidades

@prueba("un alias que apunta a dos clientes queda fuera de la atribucion",
        "en el canon real un alias de siglas apuntaba a dos clientes distintos; usarlo para atribuir "
        "asignaria notas al cliente equivocado")
def _():
    d = jsonr("entities")
    amb = {a for e in d["entities"] for a in e.get("aliases_ambiguos", [])}
    assert "omni" in amb, f"esperaba `omni` como ambiguo, hay: {amb}"
    for e in d["entities"]:
        assert "omni" not in e["aliases"], f"{e['canonical']} conserva un alias ambiguo"
    # y el grafo tampoco puede usarlo: un `search_terms: [[OMNI]]` no debe resolver a
    # ninguno de los dos clientes, porque elegir uno seria elegir al azar
    corre("grafo", "--write")
    rows = [json.loads(l) for l in open(os.path.join(FIXTURE, "Context/_skill-config/entity-graph.jsonl"))
            if l.strip()]
    origen = "Context/context-maps/CM-omni-alcance-compartido.md"
    a_cliente = [r for r in rows if r.get("from") == origen and r.get("rel") == "trata_de"
                 and r.get("to_type") == "cliente"]
    assert not a_cliente, f"un alias ambiguo resolvio a un cliente en el grafo: {a_cliente}"

@prueba("la clase no se inventa: por defecto es customer y lo dice",
        "se midio que derivar la clase del texto da falsos positivos (marcaba competidores "
        "que eran clientes); una etiqueta inventada es peor que ninguna")
def _():
    d = jsonr("entities")
    sin = [e for e in d["entities"] if e.get("class_via", "").startswith("por defecto")]
    assert sin, "ninguna entidad declara que su clase no la ha decidido nadie"

# --------------------------------------------------------- atribucion de cliente (C30)

@prueba("el titulo atribuye, el cuerpo no",
        "C30. Atribuir por mencion metia clientes dentro de `metric` y de `gotcha` de codigo")
def _():
    d = jsonr("clients")
    escribibles = {p["path"] for p in d["escribibles"]}
    assert any("gammalabs" in p for p in escribibles), escribibles
    assert not any("MET-" in p or "Got-" in p for p in escribibles), escribibles

@prueba("metric y las notas tech nunca son candidatas a cliente",
        "una metrica define vocabulario de la casa y un gotcha describe codigo; mencionar "
        "un cliente no los hace suyos")
def _():
    d = jsonr("clients")
    todos = d["escribibles"] + d["solo_cuerpo"]
    assert not [p for p in todos if p["type"] in ("metric", "gotcha", "system", "glossary")], \
        [p["path"] for p in todos if p["type"] in ("metric", "gotcha")]

# ------------------------------------------------------------------------ eje temporal

@prueba("un alias que es subcadena de otra palabra no atribuye",
        "BUG REAL: un alias corto casaba dentro del nombre de otro cliente y bloqueaba cuatro "
        "atribuciones correctas. Aqui `nexo` no debe casar dentro de `nexos`")
def _():
    d = jsonr("clients")
    todos = d["escribibles"] + d["solo_cuerpo"] + d["ambiguas"]
    assert not [p for p in todos if "integracion-de-sistemas" in p["path"]], \
        "atribuyo un cliente por una subcadena dentro de otra palabra"

@prueba("un titulo que nombra a dos clientes no se escribe",
        "en el canon real habia notas cuyo titulo nombra a dos "
        "clientes de verdad; escribir uno de los dos seria atribuir al azar. OJO: el caso "
        "no se puede montar con un alias compartido, porque la deteccion de colisiones ya "
        "lo quita antes — hacen falta dos nombres distintos en el mismo titulo")
def _():
    d = jsonr("clients")
    esc = [p["path"] for p in d["escribibles"]]
    amb = [a["path"] for a in d["ambiguas"]]
    assert any("acme-build-y-beta-corp" in p for p in amb), f"no lo detecto como ambigua: {amb}"
    assert not [p for p in esc if "acme-build-y-beta-corp" in p], f"lo escribio igual: {esc}"

@prueba("dos decisiones del mismo dia no son candidatas a supersesion",
        "sin orden temporal no hay antigua ni nueva. Es la razon de que `dates` tenga que "
        "correr antes que `supersession`")
def _():
    d = jsonr("supersession")
    mismo = [p for p in d["pares"] if p["fecha_antigua"] == p["fecha_nueva"]]
    assert not mismo, f"propuso un par sin orden temporal: {mismo}"
    assert all(p["dias"] > 0 for p in d["pares"]), d["pares"]

@prueba("occurred_on solo se propone si la fuente tiene fecha",
        "C29: rellenarlo copiando `captured_on` es justo el error que el campo existe para "
        "hacer visible. fathom:222 no tiene source_date y no debe proponerse")
def _():
    d = jsonr("dates")
    props = {p["source_id"] for p in d["propuestas"]}
    sinres = {p["source_id"] for p in d["sin_resolver"]}
    assert "fathom:222" in sinres or "fathom:222" not in props, (props, sinres)

@prueba("un candidato a supersesion exige fechas de evento distintas",
        "sin eje temporal no hay antigua ni nueva; dos decisiones del mismo dia son dos "
        "decisiones, no una superada")
def _():
    d = jsonr("supersession")
    assert len(d["pares"]) == 1, [(p["antigua"], p["nueva"]) for p in d["pares"]]
    par = d["pares"][0]
    assert par["fecha_antigua"] < par["fecha_nueva"], par
    assert "migra" in par["antigua"] and "renegocia" in par["nueva"], par

# ------------------------------------------------------------------------------ grafo

@prueba("un cliente es un solo nodo",
        "BUG REAL 2026-09-09: un cliente vivia como nodo `cliente` y como nodo `entidad` con "
        "su nombre en search_terms, asi que `vecinos` devolvia media ficha sin avisar")
def _():
    corre("grafo", "--write")
    rows = [json.loads(l) for l in open(os.path.join(FIXTURE, "Context/_skill-config/entity-graph.jsonl"))
            if l.strip()]
    rows = [r for r in rows if "_meta" not in r]
    nombres_cliente = {"beta corp", "acme build", "gamma labs"}
    ent = {str(r["to"]).lower() for r in rows if r.get("to_type") == "entidad"}
    assert not (ent & nombres_cliente), f"clientes duplicados como entidad: {ent & nombres_cliente}"
    # y el `search_terms: [[Beta Corp]]` tiene que haber producido una arista AL CLIENTE
    al_cliente = [r for r in rows if r.get("rel") == "trata_de" and r.get("to_type") == "cliente"]
    assert al_cliente, "un search_term con nombre de cliente no genero arista al nodo de cliente"

@prueba("las menciones de cuerpo entran como arista debil, no como autoria",
        "C30 dice que mencionar no atribuye. El grafo es donde la mencion SI cabe, con otro "
        "verbo y otro peso — tirarla era perder informacion que existe")
def _():
    rows = [json.loads(l) for l in open(os.path.join(FIXTURE, "Context/_skill-config/entity-graph.jsonl"))
            if l.strip()]
    men = [r for r in rows if r.get("rel") == "menciona"]
    assert men, "no hay ninguna arista `menciona`"
    assert all(r["weight"] < 1.0 for r in men), [r["weight"] for r in men]

@prueba("el recorrido omite las aristas debiles por defecto",
        "una mencion en el cuerpo pesa 0.3 y no es autoria (C30). Si `vecinos` las mezcla "
        "con las fuertes sin pedirlo, la ficha de un cliente se llena de notas que solo lo "
        "nombran de pasada y deja de ser una ficha")
def _():
    r = corre("vecinos", "--nodo", "Beta Corp")
    con = corre("vecinos", "--nodo", "Beta Corp", "--debiles")
    assert "menciona" not in r.stdout, "colo una arista debil sin que se la pidieran"
    assert "menciona" in con.stdout, "`--debiles` no trae las menciones"
    assert len(con.stdout) > len(r.stdout), "`--debiles` no anade nada"

@prueba("las aristas humanas se incorporan sin regenerarse",
        "C36. El grafo de juicio humano no se recupera si se pierde; el derivado si")
def _():
    rows = [json.loads(l) for l in open(os.path.join(FIXTURE, "Context/_skill-config/entity-graph.jsonl"))
            if l.strip()]
    hum = [r for r in rows if r.get("method") == "humano"]
    assert len(hum) == 1 and hum[0]["rel"] == "extiende", hum

@prueba("el derivado se sella y detecta que esta obsoleto",
        "un derivado committeado caduca en silencio: paso de verdad, el grafo estaba 160 "
        "aristas obsoleto tres horas despues de escribirlo")
def _():
    path = os.path.join(FIXTURE, "Context/_skill-config/entity-graph.jsonl")
    meta = json.loads(open(path).readline())
    assert "_meta" in meta and meta["_meta"].get("firma"), meta
    nota = os.path.join(FIXTURE, "Context/Metrics/MET-chats-por-cuenta.md")
    orig = open(nota).read()
    try:
        open(nota, "w").write(orig.replace("confidence: high", "confidence: low", 1))
        r = corre("vecinos", "--nodo", "Beta Corp")
        assert "OBSOLETO" in r.stderr, f"no aviso de obsolescencia. stderr={r.stderr[:200]!r}"
    finally:
        open(nota, "w").write(orig)
        corre("grafo", "--write")

# -------------------------------------------------------------------------- escrituras

@prueba("dry-run no toca un solo byte",
        "los subcomandos escriben en el canon entero; un dry-run que escriba es un desastre "
        "silencioso sobre mil ficheros")
def _():
    tmp = tempfile.mkdtemp()
    copia = os.path.join(tmp, "fixture")
    shutil.copytree(FIXTURE, copia)
    antes = {}
    for d, _, fs in os.walk(copia):
        for f in fs:
            antes[os.path.join(d, f)] = open(os.path.join(d, f), "rb").read()
    for cmd in ("clients", "dates", "normalizar", "entities", "contradicciones", "grafo"):
        corre(cmd, base=copia)
    for p, contenido in antes.items():
        assert open(p, "rb").read() == contenido, f"{cmd} escribio en dry-run: {os.path.basename(p)}"
    shutil.rmtree(tmp)

@prueba("--write es idempotente",
        "correr dos veces no debe cambiar nada la segunda: si cambia, el escritor no es "
        "estable y cada pasada ensucia el diff de git")
def _():
    tmp = tempfile.mkdtemp()
    copia = os.path.join(tmp, "fixture")
    shutil.copytree(FIXTURE, copia)
    for cmd in ("normalizar", "clients", "dates"):
        corre(cmd, "--write", base=copia)
    tras_uno = {}
    for d, _, fs in os.walk(copia):
        for f in fs:
            if f.endswith(".md"):
                tras_uno[os.path.join(d, f)] = open(os.path.join(d, f), "rb").read()
    for cmd in ("normalizar", "clients", "dates"):
        corre(cmd, "--write", base=copia)
    for p, contenido in tras_uno.items():
        assert open(p, "rb").read() == contenido, f"la segunda pasada cambio {os.path.basename(p)}"
    shutil.rmtree(tmp)

@prueba("normalizar no toca titulos ni nombres con espacios",
        "las comillas ahi son correctas; quitarlas rompe el YAML")
def _():
    tmp = tempfile.mkdtemp()
    copia = os.path.join(tmp, "fixture")
    shutil.copytree(FIXTURE, copia)
    corre("normalizar", "--write", base=copia)
    t = open(os.path.join(copia, "Context/decision-logs/DL-betacorp-migra-a-pro.md")).read()
    assert 'title: "Beta Corp migra al plan Pro"' in t, "se cargo las comillas del titulo"
    assert 'client_name: "Beta Corp"' in t, "se cargo las comillas de client_name"
    assert "\nproject: Kestrel\n" in t, "no normalizo project"
    shutil.rmtree(tmp)

# --------------------------------------------------------------------------- contratos

@prueba("un fichero sin `type` no cuenta como canon",
        "78 ficheros de trabajo del canon real contaban como notas en cualquier grep")
def _():
    import glob, re as _re
    d = jsonr("contract")
    sin_type = [f for f in glob.glob(FIXTURE + "/Context/**/*.md", recursive=True)
                if not _re.search(r"^type:\s*\S", open(f, encoding="utf-8").read(), _re.M)]
    assert d["n"] == len(sin_type), (d["n"], [os.path.basename(f) for f in sin_type])

@prueba("los gates leen metrics.json y no umbrales escritos en el codigo",
        "C31: un umbral en el codigo es un umbral que nadie audita")
def _():
    r = corre("gates")
    assert r.returncode == 1 and "metrics.json" in r.stderr, (r.returncode, r.stderr[:200])

@prueba("dos corridas identicas dan salidas identicas",
        "sin determinismo, comparar dos medidas no significa nada")
def _():
    for cmd in ("stats", "entities", "cruce", "supersession"):
        a, b = jsonr(cmd), jsonr(cmd)
        a.pop("measured_on", None); b.pop("measured_on", None)
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True), f"{cmd} no es determinista"

print(f"\n{corridos - len(fallos)}/{corridos} pasan")
if fallos:
    print(f"\n{len(fallos)} fallo(s):")
    for n, porque, exc in fallos:
        print(f"  · {n}\n      {exc}\n      existe porque: {porque}")
    sys.exit(1)
