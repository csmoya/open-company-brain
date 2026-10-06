#!/usr/bin/env python3
"""Instrumento de medida del company brain. Un fichero, subcomandos, cero dependencias.

Por qué existe: hasta la v0.7.0 el canon no tenía ninguna medida que pudiera salir en
rojo. `health` reportaba doce checks y ninguno tenía umbral; el check 12 decía
explicitamente "reporta el numero, no lo juzga". Esto lo mide y lo juzga contra
`_skill-config/metrics.json`, que es el contrato: la regla de entrada es que si un
numero no puede estar en rojo, no ocupa sitio.

Disciplina (heredada de retrieval-eval/ del vault personal, donde se pago aprenderla):
  - determinista: orden estable en todo, sin muestreo
  - sin dependencias: solo stdlib
  - dry-run por defecto: nada escribe sin --write
  - degrada, no aborta: si falta un fichero, lo dice y sigue

Uso: python3 tools/cb.py <subcomando> [--json] [--write]
Subcomandos: stats · contract · entities · clients · dates · expiry · supersession · cruce · grafo · vecinos · normalizar · contradicciones · gates · surface
"""
import argparse, datetime, hashlib, json, os, re, sys, unicodedata
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.environ.get("CB_PROJECT", "example")
# CB_BASE deja apuntar a un arbol cualquiera. Existe para los tests: se prueban contra una
# fixture sintetica y no contra el canon real, que ni debe ensuciarse ni es determinista
# (mientras se escribia esto, otra sesion le metio 195 notas).
BASE = os.environ.get("CB_BASE") or os.path.join(ROOT, PROJECT)
CTX = os.path.join(BASE, "Context")
CFG = os.path.join(CTX, "_skill-config")
REPORTS = os.path.join(CTX, "_reports")
TODAY = datetime.date.fromisoformat(os.environ.get("CB_TODAY", datetime.date.today().isoformat()))

# Tipos del contrato. Los seis de canon, los seis de tech, y `source-raw`, que no es
# canon: es la fuente cruda cacheada y no lleva ciclo de vida (ni status ni expires_on).
CANON_TYPES = ["context-map", "observation", "decision-log", "process", "metric", "glossary"]
TECH_TYPES = ["system", "runbook", "gotcha", "inventory-repo", "reference", "plan"]
RAW_TYPES = ["source-raw"]
ALL_TYPES = CANON_TYPES + TECH_TYPES + RAW_TYPES
EXPIRY_DAYS = {"context-map": 90, "observation": 365, "decision-log": 180, "process": 90,
               "metric": 180, "glossary": 180, "system": 90, "runbook": 90, "gotcha": 365,
               "reference": 90, "plan": 90, "inventory-repo": None}

# --------------------------------------------------------------------------- utilidades

def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", strip_accents(str(s)).lower()).strip()

def read(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""

def split_frontmatter(text):
    """Devuelve (dict_plano, texto_frontmatter, cuerpo). Parser de lineas, no YAML:
    basta para campos escalares y no arrastra dependencia. Las listas se devuelven en
    crudo y el que las necesite las parte."""
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return {}, "", text
    fm, body = m.group(1), m.group(2)
    d = {}
    for k, v in re.findall(r"^([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)$", fm, re.M):
        if k not in d:
            d[k] = v.strip()
    return d, fm, body

def yaml_block(fm, key):
    """El bloque indentado de una clave YAML: hasta la siguiente clave de nivel cero.
    Hace falta porque `occurrences` y `search_terms` son listas y el parser de lineas
    de `split_frontmatter` solo devuelve escalares."""
    m = re.search(rf"^{key}:\s*\n((?:[ \t]+.*\n?)*)", fm, re.M)
    return m.group(1) if m else ""

def client_ids_of(fm):
    """`client_id` puede ser escalar (`cid-0001`) o lista. Las dos formas existen en el canon."""
    blk = yaml_block(fm, "client_id")
    if blk:
        return sorted(set(re.findall(r"(cid-\d+)", blk)))
    m = re.search(r"^client_id:\s*\"?(cid-\d+)\"?", fm, re.M)
    return [m.group(1)] if m else []

def wikilinks(fm, key):
    return [x.split("|")[0].strip() for x in re.findall(r"\[\[([^\]]+)\]\]", yaml_block(fm, key))]

# Familias de canal. La ontologia declara 7 entidades de clase `channel`, pero el canon usa
# 157 variantes distintas de termino con "whatsapp" en 263 apariciones — o sea que la
# ontologia conoce 5 de 157. Preguntar "que clientes tienen WhatsApp" no se puede responder
# contra la ontologia; se responde contra la FAMILIA, que es el token distintivo. Esto no
# inventa entidades de ontologia: eso es trabajo de `enrich` con aprobacion humana (C2).
CHANNEL_FAMILIES = {
    "whatsapp": "WhatsApp",
    "messenger": "Messenger",
    "instagram": "Instagram",
    "telegram": "Telegram",
    "webchat": "Web chat",
    "web chat": "Web chat",
    "livechat": "Live chat",
    "live chat": "Live chat",
    "sms": "SMS",
}

def channel_vocab():
    """Las entidades de clase `channel` de la ontologia, con sus alias. Vocabulario
    controlado: preciso pero incompleto (ver CHANNEL_FAMILIES)."""
    onto = load_json(os.path.join(CFG, "ontology.json"), {})
    out = {}
    for e in (onto.get("entities") or []):
        if e.get("class") == "channel":
            for f in [e.get("canonical", "")] + list(e.get("aliases") or []):
                if f:
                    out[norm(f)] = e["canonical"]
    return out

def families_in(texts):
    """Familias de canal presentes en una lista de textos, por token distintivo."""
    found = set()
    for t in texts:
        n = norm(t)
        for token, fam in CHANNEL_FAMILIES.items():
            if re.search(r"\b" + re.escape(token) + r"\b", n):
                found.add(fam)
    return found

def notes(include_noncontract=False):
    """Todas las notas de Context/, ordenadas por ruta (determinista). Excluye
    _to_delete y la maquinaria (_skill-config, _reports)."""
    out = []
    for dirpath, dirnames, filenames in os.walk(CTX):
        dirnames[:] = sorted(d for d in dirnames if d not in ("_to_delete", "_skill-config", "_reports"))
        for fn in sorted(filenames):
            if not fn.endswith(".md"):
                continue
            p = os.path.join(dirpath, fn)
            text = read(p)
            fm, fmtxt, body = split_frontmatter(text)
            ty = fm.get("type", "").strip().strip('"').strip("'")
            rel = os.path.relpath(p, BASE)
            if ty in ALL_TYPES or include_noncontract:
                out.append({"path": rel, "type": ty, "fm": fm, "fmtxt": fmtxt, "body": body, "abs": p})
    return out

def project_name():
    """El nombre del proyecto tal como lo escribe el propio canon (el `project` mas comun),
    no el de la carpeta: la carpeta es un detalle de disposicion, el valor es contrato."""
    if os.environ.get("CB_PROJECT_NAME"):
        return os.environ["CB_PROJECT_NAME"]
    c = Counter(n["fm"].get("project", "").strip().strip('"').strip("'") for n in notes())
    c.pop("", None)
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if c else PROJECT

def is_date(s):
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", str(s).strip().strip('"')))

def filled(v):
    v = str(v or "").strip().strip('"').strip("'")
    return v not in ("", "null", "none", "[]", "~", "TODO")

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"aviso: {os.path.relpath(path, ROOT)} ilegible ({exc}); sigo con el valor por defecto", file=sys.stderr)
        return default

def dump_json(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2, sort_keys=False)
        fh.write("\n")

def append_jsonl(path, obj):
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")

def read_log_dir(dirpath, legacy=None):
    """Lee un log repartido en un fichero por persona y mes, en orden estable.

    Un JSONL unico al que aporta todo el equipo entra en conflicto de merge en cada push
    simultaneo, y un log que da guerra al hacer push es un log que la gente deja de
    escribir — que mata el gold, que es justo para lo que existe. Un fichero por persona y
    mes: dos personas nunca escriben el mismo fichero.
    """
    out = []
    if os.path.isdir(dirpath):
        for fn in sorted(os.listdir(dirpath)):
            if fn.endswith(".jsonl"):
                out += read_jsonl(os.path.join(dirpath, fn))
    if legacy and os.path.exists(legacy):
        out += read_jsonl(legacy)      # compatibilidad con el fichero unico del esquema 1
    return out

def read_jsonl(path):
    out = []
    for line in read(path).splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out

# ------------------------------------------------------------------------------- stats

def _recuperables(rows):
    """Notas cuyo `occurred_on` se PUEDE recuperar, y cuantas lo tienen.

    Medir la cobertura de `occurred_on` sobre todo el canon hace que el gate se ponga rojo
    cada vez que entra un lote de notas capturadas a mano, que por definicion no tienen
    fuente con fecha: eso es ruido, y un gate que grita sin motivo es peor que ninguno
    (misma logica que C31). Lo que se puede exigir es lo recuperable.
    """
    idx = source_date_index()
    rec = con = 0
    for n in rows:
        sid = n["fm"].get("source_id", "").strip().strip('"')
        if filled(sid) and sid in idx:
            rec += 1
            if is_date(n["fm"].get("occurred_on", "")):
                con += 1
    return {"recuperables": rec, "recuperadas": con}

def _desfase_mediana(rows):
    """Dias entre el evento y su captura. Con el reloj anclado en la captura (decision del
    2026-09-09), este numero ES la exposicion media del canon: cuanto mas grande, mas tiempo
    se presenta fresca una nota despues de que pasara lo que cuenta."""
    d = []
    for n in rows:
        oc, cap = n["fm"].get("occurred_on", "").strip().strip('"'), n["fm"].get("captured_on", "").strip().strip('"')
        if is_date(oc) and is_date(cap):
            d.append((datetime.date.fromisoformat(cap) - datetime.date.fromisoformat(oc)).days)
    d.sort()
    return d[len(d) // 2] if d else 0

def _expuestas(rows):
    """Notas vivas cuyo evento ya cayo fuera de la ventana de vigencia de su tipo."""
    n_exp = 0
    for n in rows:
        ty = n["type"]
        dias = EXPIRY_DAYS.get(ty)
        oc, ex = n["fm"].get("occurred_on", "").strip().strip('"'), n["fm"].get("expires_on", "").strip().strip('"')
        if not dias or not is_date(oc) or not is_date(ex):
            continue
        viva = datetime.date.fromisoformat(ex) >= TODAY
        evento_vencido = datetime.date.fromisoformat(oc) + datetime.timedelta(days=dias) < TODAY
        if viva and evento_vencido:
            n_exp += 1
    return n_exp

def cmd_stats(args):
    ns = notes()
    everything = notes(include_noncontract=True)
    noncontract = [n for n in everything if n["type"] not in ALL_TYPES]
    by_type = Counter(n["type"] for n in ns)
    seg = {"canon": sum(by_type[t] for t in CANON_TYPES),
           "tech": sum(by_type[t] for t in TECH_TYPES),
           "source_raw": sum(by_type[t] for t in RAW_TYPES),
           "sin_contrato": len(noncontract)}
    canon = [n for n in ns if n["type"] in CANON_TYPES]
    tech = [n for n in ns if n["type"] in TECH_TYPES]
    lifecycle = canon + tech   # source-raw no lleva ciclo de vida, no entra en los denominadores

    def rate(rows, pred):
        return {"n": len(rows), "ok": sum(1 for r in rows if pred(r))}

    per_type = {}
    for t in ALL_TYPES:
        rows = [n for n in ns if n["type"] == t]
        if not rows:
            continue
        per_type[t] = {
            "n": len(rows),
            "validated_true": sum(1 for r in rows if str(r["fm"].get("validated", "")).startswith("true")),
            "client_name": sum(1 for r in rows if filled(r["fm"].get("client_name"))),
            "captured_on": sum(1 for r in rows if is_date(r["fm"].get("captured_on", ""))),
            "expires_on": sum(1 for r in rows if is_date(r["fm"].get("expires_on", ""))),
            "status": sum(1 for r in rows if filled(r["fm"].get("status"))),
            "supersedes": sum(1 for r in rows if filled(r["fm"].get("supersedes"))),
            "occurred_on": sum(1 for r in rows if is_date(r["fm"].get("occurred_on", ""))),
            "connections": sum(1 for r in rows if filled(r["fm"].get("connections"))),
        }

    expired = soon = 0
    for n in lifecycle:
        e = n["fm"].get("expires_on", "").strip().strip('"')
        if not is_date(e):
            continue
        d = datetime.date.fromisoformat(e)
        if d < TODAY:
            expired += 1
        elif (d - TODAY).days <= 30:
            soon += 1

    graph = read_jsonl(os.path.join(CFG, "graph.jsonl"))
    rlog = read_log_dir(os.path.join(CFG, "retrieval-log"),
                        legacy=os.path.join(CFG, "retrieval-log.jsonl"))
    bets = read_jsonl(os.path.join(CFG, "bets.jsonl"))
    onto = load_json(os.path.join(CFG, "ontology.json"), {})
    ents = load_json(os.path.join(CFG, "entities.json"), {})

    onto_terms = set()
    for e in (onto.get("entities") or []):
        for v in [e.get("canonical", "")] + list(e.get("aliases") or []):
            if v:
                onto_terms.add(norm(v))
    onto_link = Counter()
    for n in canon + tech:
        terms = re.findall(r"\[\[([^\]]+)\]\]", n["fmtxt"].split("search_terms:")[-1].split("\n" + "x" * 99)[0]) \
            if "search_terms:" in n["fmtxt"] else []
        hits = sum(1 for t in terms if norm(t.split("|")[0]) in onto_terms)
        onto_link[min(hits, 2)] += 1

    # el gold que un eval necesita: entradas del log que declaran QUE notas se usaron
    with_used = sum(1 for r in rlog if r.get("notas_usadas"))
    with_gaps = sum(1 for r in rlog if r.get("gaps"))

    out = {
        "project": PROJECT, "measured_on": TODAY.isoformat(),
        "corpus": {"total_con_contrato": len(ns), "segmentos": seg, "por_tipo": dict(by_type.most_common())},
        "sin_contrato": {"n": len(noncontract),
                         "por_carpeta": dict(Counter(os.path.dirname(n["path"]) for n in noncontract).most_common())},
        "ciclo_de_vida": {"denominador": len(lifecycle), "expiradas": expired, "expiran_30d": soon},
        "temporal": {"denominador": len(lifecycle),
                     "con_occurred_on": sum(1 for n in lifecycle if is_date(n["fm"].get("occurred_on", ""))),
                     "con_source_id": sum(1 for n in lifecycle if filled(n["fm"].get("source_id"))),
                     "desfase_mediana_dias": _desfase_mediana(lifecycle),
                     "expuestas": _expuestas(lifecycle),
                     **_recuperables(lifecycle)},
        "validacion": {"denominador": len(lifecycle),
                       "validated_true": sum(1 for n in lifecycle if str(n["fm"].get("validated", "")).startswith("true")),
                       "canon_validated_true": sum(1 for n in canon if str(n["fm"].get("validated", "")).startswith("true"))},
        "supersesion": {"decision_logs": by_type.get("decision-log", 0),
                        "con_supersedes": sum(1 for n in ns if n["type"] == "decision-log" and filled(n["fm"].get("supersedes")))},
        "entidades": {"client_name_relleno": sum(1 for n in ns if filled(n["fm"].get("client_name"))),
                      "denominador": len(ns),
                      "entities_json": len(ents.get("entities") or []),
                      "ontology_json": len(onto.get("entities") or [])},
        "conectividad_ontologia": {"0_links": onto_link[0], "1_link": onto_link[1], "2_o_mas": onto_link[2]},
        "grafo": {"aristas": len(graph), "por_verbo": dict(Counter(e.get("rel", "?") for e in graph).most_common()),
                  "con_provenance": sum(1 for e in graph if e.get("declared_via"))},
        "log_de_retrieval": {"entradas": len(rlog), "con_notas_usadas": with_used, "con_gaps": with_gaps,
                             "con_session_id": sum(1 for r in rlog if r.get("session_id")),
                             "sesiones_distintas": len({r.get("session_id") for r in rlog if r.get("session_id")}),
                             "por_persona": dict(sorted(Counter(r.get("who") or "sin_autor" for r in rlog).items()))},
        "apuestas": {"total": len(bets), "abiertas": sum(1 for b in bets if b.get("status") == "open"),
                     "vencidas_sin_cerrar": sum(1 for b in bets if b.get("status") == "open"
                                                and is_date(b.get("deadline", "")) and datetime.date.fromisoformat(b["deadline"]) < TODAY)},
        "por_tipo_detalle": per_type,
    }
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    c = out["corpus"]
    print(f"company brain · {project_name()} · medido {TODAY}")
    print(f"\nCorpus: {c['total_con_contrato']} notas con contrato "
          f"(canon {seg['canon']} · tech {seg['tech']} · source-raw {seg['source_raw']}) "
          f"+ {seg['sin_contrato']} ficheros SIN contrato en Context/")
    print(f"\n{'tipo':<16}{'n':>5}{'valid':>7}{'capt':>6}{'occur':>7}{'exp':>6}{'super':>7}{'client':>8}")
    for t, v in sorted(per_type.items(), key=lambda x: -x[1]["n"]):
        print(f"{t:<16}{v['n']:>5}{v['validated_true']:>7}{v['captured_on']:>6}{v['occurred_on']:>7}"
              f"{v['expires_on']:>6}{v['supersedes']:>7}{v['client_name']:>8}")
    v = out["validacion"]
    print(f"\nValidacion: {v['validated_true']}/{v['denominador']} con ciclo de vida "
          f"({100*v['validated_true']/max(v['denominador'],1):.1f} %) · solo canon: {v['canon_validated_true']}/{seg['canon']}")
    print(f"Caducidad: {out['ciclo_de_vida']['expiradas']} expiradas, {out['ciclo_de_vida']['expiran_30d']} en 30 dias")
    t = out["temporal"]
    print(f"Eje temporal: occurred_on en {t['con_occurred_on']}/{t['denominador']} · "
          f"recuperables {t['recuperadas']}/{t['recuperables']} · "
          f"desfase mediana {t['desfase_mediana_dias']} dias")
    print(f"Exposicion del reloj (ancla = captured_on): {t['expuestas']} notas vivas cuyo evento ya vencio")
    s = out["supersesion"]
    print(f"Supersesion: {s['con_supersedes']}/{s['decision_logs']} decision-logs con `supersedes`")
    e = out["entidades"]
    print(f"Entidades: client_name en {e['client_name_relleno']}/{e['denominador']} · "
          f"entities.json {e['entities_json']} · ontology.json {e['ontology_json']}")
    o = out["conectividad_ontologia"]
    print(f"Conectividad ontologia: 0 links {o['0_links']} · 1 {o['1_link']} · >=2 {o['2_o_mas']}")
    g = out["grafo"]
    print(f"Grafo: {g['aristas']} aristas {g['por_verbo']} · con provenance {g['con_provenance']}")
    r = out["log_de_retrieval"]
    print(f"Log de retrieval: {r['entradas']} entradas · con notas_usadas {r['con_notas_usadas']} "
          f"· con gaps {r['con_gaps']} · {r['sesiones_distintas']} sesiones · por persona {r['por_persona']}")
    b = out["apuestas"]
    print(f"Apuestas: {b['total']} ({b['abiertas']} abiertas, {b['vencidas_sin_cerrar']} vencidas sin cerrar)")
    return 0

# ---------------------------------------------------------------------------- contract

def cmd_contract(args):
    """Ficheros .md dentro de Context/ que no declaran un `type` del contrato.
    Cuentan como canon en cualquier grep y no lo son: alimentan el check 13 de health."""
    rows = [n for n in notes(include_noncontract=True) if n["type"] not in ALL_TYPES]
    by_dir = defaultdict(list)
    for n in rows:
        by_dir[os.path.dirname(n["path"])].append(n)
    if args.json:
        print(json.dumps({"n": len(rows), "por_carpeta": {k: [x["path"] for x in v] for k, v in sorted(by_dir.items())}},
                         ensure_ascii=False, indent=2))
        return 0
    print(f"{len(rows)} ficheros en Context/ sin `type` del contrato\n")
    for d, v in sorted(by_dir.items(), key=lambda x: -len(x[1])):
        print(f"  {len(v):>3}  {d or '.'}")
    print("\nNo se mueve ni se borra nada (C14). Decision humana: darles frontmatter o sacarlos de Context/.")
    return 0

# ---------------------------------------------------------------------------- entities

def title_prefix(path):
    """Prefijo de entidad en el nombre de fichero: OB-acme-build-... -> acme build."""
    base = os.path.basename(path)[:-3]
    base = re.sub(r"^(OB|DL|PR|CM|MET|GL|Sys|Run|Got|Inv|Ref|Plan|SRC)-", "", base)
    return norm(base)

ARTICLES = ("the ", "la ", "el ", "los ", "las ", "grupo ")

def alias_forms(canonical):
    """Variantes de escritura con las que un nombre aparece de verdad en el canon:
    el parentetico ("Delta (OMNI)" -> "OMNI"), el nombre sin el parentetico, la
    forma sin articulo ("The Data Lab" -> "Data Lab") y las pegadas sin espacios,
    que es como aparecen en los nombres de fichero (datalab, acmebuild)."""
    out = set()
    base = canonical.strip()
    paren = re.findall(r"\(([^)]*)\)", base)
    outside = re.sub(r"\([^)]*\)", " ", base)
    cands = [outside]
    for pz in paren:
        # un parentetico corto suele ser el alias real; uno largo es una aclaracion
        if pz and len(pz.split()) <= 3 and "," not in pz:
            cands.append(pz)
    for c in list(cands):
        n = norm(c)
        if not n:
            continue
        for art in ARTICLES:
            if n.startswith(art):
                cands.append(n[len(art):])
    for c in cands:
        n = norm(c)
        if not n:
            continue
        out.add(n)
        squashed = n.replace(" ", "")
        if len(squashed) >= 4:
            out.add(squashed)
    out.discard(norm(canonical))
    # un alias de menos de 3 caracteres casa con cualquier cosa; no sirve
    return sorted(a for a in out if len(a) >= 3)

# Clases de entidad. El plan pedia `customer · person · system · feature · competitor`.
# Se midio si la clase se puede derivar del texto y NO se puede: buscar "competidor" marca
# como competidor a un cliente del que se habla de la competencia, y "agencia" marca a 32.
# Derivarla habria sido el grafo denso de aristas dudosas que G13 prohibe. Asi que se
# clasifica solo con evidencia inequivoca (el marcador va en el propio nombre canonico) y
# el resto lo decide una persona en `entities-overrides.json`, que la regeneracion respeta.
# `system` y `feature` no viven aqui a proposito: son `product-feature`/`integration`/
# `channel` de `ontology.json`, y dos vocabularios para lo mismo divergen (paso por eso
# el frontmatter tres veces en la v0.6.0).
OVERRIDES = "entities-overrides.json"

def build_entities():
    ns = notes()
    directory = load_json(os.path.join(CFG, "client-directory.json"), {"clients": []})
    overrides = load_json(os.path.join(CFG, OVERRIDES), {}).get("entities", {})
    by_name = {norm(c["name"]): c for c in directory.get("clients", [])}
    # semilla: los client_name que ya existen en el frontmatter, agrupados por forma normalizada
    variants = defaultdict(set)
    for n in ns:
        v = n["fm"].get("client_name", "").strip().strip('"').strip("'")
        if filled(v):
            variants[norm(v)].add(v)
    # todas las formas de escritura que apuntan al mismo client_id son UNA entidad
    merged = {}
    def slot(cid, canonical):
        e = merged.get(cid)
        if e is None:
            e = merged[cid] = {"id": cid, "canonical": canonical, "class": "customer",
                               "client_id": cid if not cid.startswith("unresolved-") else None,
                               "aliases": set()}
        # el nombre canonico es el del directorio si lo hay; si no, el mas largo visto
        elif len(canonical) > len(e["canonical"]) and e["client_id"] is None:
            e["canonical"] = canonical
        return e
    for key in sorted(variants):
        forms = sorted(variants[key])
        canonical, cid = forms[0], None
        if key in by_name:
            cid, canonical = by_name[key]["client_id"], by_name[key]["name"]
        else:
            for dn, c in sorted(by_name.items()):
                if dn and (dn in key or key in dn):
                    cid, canonical = c["client_id"], c["name"]
                    break
        e = slot(cid or ("unresolved-" + re.sub(r"\s+", "-", key)), canonical)
        for f in forms:
            if norm(f) != norm(e["canonical"]):
                e["aliases"].add(norm(f))
        e["aliases"].update(alias_forms(e["canonical"]))
    # clientes del directorio que ningun client_name menciona: existen y no estan atribuidos
    for c in directory.get("clients", []):
        e = slot(c["client_id"], c["name"])
        e["canonical"] = c["name"]
        e["client_id"] = c["client_id"]
        e["aliases"].update(alias_forms(c["name"]))
    # Canales por cliente. Se separan dos señales a proposito, por la misma razon que
    # C30 separa titulo de cuerpo: que una nota MENCIONE WhatsApp no significa que ese
    # cliente tenga WhatsApp. Declarado = el canal esta en `search_terms`, que alguien
    # escribio. Mencionado = la palabra aparece en el texto. Lo primero es un hecho del
    # cliente; lo segundo es una pista.
    chan = channel_vocab()
    declarados, mencionados, entity_hits = defaultdict(set), defaultdict(set), defaultdict(set)
    for n in ns:
        cids = client_ids_of(n["fmtxt"])
        if not cids:
            continue
        terms = wikilinks(n["fmtxt"], "search_terms")
        # declarado = la familia sale de un `search_terms`, que alguien escribio a proposito
        hay = families_in(terms)
        hay_onto = {canon for f, canon in chan.items() if any(f in norm(t) for t in terms)}
        # mencionado = la familia solo aparece en el texto de la nota. Pista, no hecho (C30).
        pistas = families_in([n["fmtxt"] + n["body"][:3000]])
        for c in cids:
            declarados[c] |= hay
            entity_hits[c] |= hay_onto
            mencionados[c] |= (pistas - hay)

    # que aliases aparecen de verdad en un nombre de fichero: separa lo util del ruido
    prefixes = [title_prefix(n["path"]).replace(" ", "") for n in ns]
    ents = []
    for e in merged.values():
        aliases = sorted(a for a in e["aliases"] if a and norm(a) != norm(e["canonical"]))
        squashed_canon = norm(e["canonical"]).replace(" ", "")
        seen_in_titles = sorted({a for a in aliases + [squashed_canon]
                                 if any(a.replace(" ", "") in p for p in prefixes)})
        cid = e["client_id"]
        ents.append({"id": e["id"], "canonical": e["canonical"], "class": e["class"],
                     "client_id": cid, "aliases": aliases,
                     "aliases_vistos_en_titulos": seen_in_titles,
                     "canales_declarados": sorted(declarados.get(cid, ())) if cid else [],
                     "canales_mencionados": sorted(mencionados.get(cid, ())) if cid else [],
                     "canales_ontologia": sorted(entity_hits.get(cid, ())) if cid else []})
    # un alias que apunta a dos entidades (p.ej. "omni" -> Delta (OMNI) y Epsilon (OMNI))
    # no puede atribuir nada por si solo: se marca y queda fuera de la atribucion automatica
    owners = defaultdict(set)
    for e in ents:
        for a in e["aliases"] + [norm(e["canonical"])]:
            owners[a].add(e["id"])
    colliding = {a for a, ids in owners.items() if len(ids) > 1}
    for e in ents:
        e["aliases_ambiguos"] = sorted(a for a in e["aliases"] if a in colliding)
        e["aliases"] = sorted(a for a in e["aliases"] if a not in colliding)
        # clase por evidencia inequivoca: el marcador esta en el nombre, no inferido del texto
        if re.search(r"contacto individual|persona f[ií]sica", e["canonical"], re.I):
            e["class"] = "person"
            e["class_via"] = "marcador en el nombre canonico"
        else:
            e["class_via"] = "por defecto — nadie la ha decidido"
        # el juicio humano gana y la regeneracion no lo pisa
        ov = overrides.get(e["client_id"] or e["id"]) or {}
        if ov.get("class"):
            e["class"], e["class_via"] = ov["class"], "decidido a mano en " + OVERRIDES
        if ov.get("aliases"):
            e["aliases"] = sorted(set(e["aliases"]) | {norm(a) for a in ov["aliases"]})
    ents.sort(key=lambda x: norm(x["canonical"]))
    return ents, directory

def cmd_entities(args):
    ents, directory = build_entities()
    unresolved = [e for e in ents if not e["client_id"]]
    obj = {"_comment": ("Entidades resueltas del canon. Derivado y regenerable: `python3 tools/cb.py entities --write`. "
                        "La fuente de verdad de un cliente sigue siendo client-directory.json; esto anade las variantes "
                        "de escritura con las que aparece en el frontmatter y en los titulos, para que una consulta por "
                        "cualquiera de ellas llegue a la misma ficha. No es taxonomia de carpetas (G12)."),
           "schema": "company-brain/entities/1", "generated_on": TODAY.isoformat(),
           "firma": corpus_signature(),
           "counts": {"entidades": len(ents), "resueltas_a_client_id": len(ents) - len(unresolved),
                      "sin_resolver": len(unresolved)},
           "entities": ents}
    if args.json:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
        return 0
    amb = sorted({a for e in ents for a in e.get("aliases_ambiguos", [])})
    print(f"{len(ents)} entidades · {len(ents)-len(unresolved)} resueltas a client_id · {len(unresolved)} sin resolver")
    print(f"{len(amb)} alias ambiguos (apuntan a 2+ entidades, excluidos de la atribucion automatica)"
          + (f": {', '.join(amb)}" if amb else ""))
    con_dec = sum(1 for e in ents if e.get("canales_declarados"))
    solo_men = sum(1 for e in ents if not e.get("canales_declarados") and e.get("canales_mencionados"))
    print(f"canales: {con_dec} clientes con canal DECLARADO en search_terms · "
          f"{solo_men} solo con mencion en el cuerpo (pista, no hecho)")
    porclase = Counter(e["class"] for e in ents)
    sin_decidir = sum(1 for e in ents if e.get("class_via", "").startswith("por defecto"))
    print(f"clases: {dict(porclase.most_common())} · {sin_decidir} sin decidir por nadie")
    print(f"la clase NO se deriva del texto (se midio: da falsos positivos). Se decide a mano")
    print(f"en {OVERRIDES}, que la regeneracion respeta.")
    if unresolved:
        print("\nSin resolver (no hay entrada en client-directory.json):")
        for e in unresolved:
            print(f"  - {e['canonical']}   alias: {', '.join(e['aliases']) or '—'}")
    if args.write:
        dump_json(os.path.join(CFG, "entities.json"), obj)
        print(f"\nescrito Context/_skill-config/entities.json")
    else:
        print("\n(dry-run — usa --write para escribir entities.json)")
    return 0

# ----------------------------------------------------------------------------- clients

# Tipos a los que un cliente puede "pertenecer". Una `metric` o una `glossary` definen
# vocabulario de la casa, y un `gotcha`/`system` describe codigo: mencionar a un cliente
# no los hace suyos. Atribuirles client_name convierte la ficha de cliente en un cajon.
CLIENT_SCOPED = ["observation", "decision-log", "context-map", "process"]

def cmd_clients(args):
    """Propone client_name/client_id para las notas que no lo llevan.

    Escribe SOLO cuando la señal esta en el titulo del fichero, que es la convencion real
    de naming de este canon (CM-acme-build-..., DL-beta-corp-...). Una mencion en el cuerpo
    se reporta aparte y no se escribe: eso es una arista `menciona` del grafo, no autoria.
    """
    ents, _ = build_entities()
    ents = [e for e in ents if e["client_id"]]
    ns = [n for n in notes() if n["type"] in CLIENT_SCOPED]
    props, body_only, ambiguous = [], [], []
    for n in ns:
        if filled(n["fm"].get("client_name")):
            continue
        pref = title_prefix(n["path"])          # normalizado, separado por espacios
        pref_squashed = pref.replace(" ", "")
        body = norm(n["body"][:4000])
        t_hits, b_hits = [], []
        for e in ents:
            forms = [norm(e["canonical"])] + e["aliases"]
            forms = [f for f in forms if f]
            # limite de palabra en los dos lados: "acme" no debe casar dentro de "acmebuild"
            in_title = any(re.search(r"\b" + re.escape(f) + r"\b", pref) or
                           (f.replace(" ", "") == pref_squashed) for f in forms)
            in_body = any(re.search(r"\b" + re.escape(f) + r"\b", body) for f in forms)
            if in_title:
                t_hits.append(e)
            elif in_body:
                b_hits.append(e)
        if len(t_hits) > 1:
            ambiguous.append({"path": n["path"], "señal": "titulo",
                              "candidatos": sorted(e["canonical"] for e in t_hits)})
        elif len(t_hits) == 1:
            e = t_hits[0]
            props.append({"path": n["path"], "type": n["type"], "client_name": e["canonical"],
                          "client_id": e["client_id"], "via": "titulo"})
        elif len(b_hits) == 1:
            e = b_hits[0]
            body_only.append({"path": n["path"], "type": n["type"], "client_name": e["canonical"],
                              "client_id": e["client_id"], "via": "cuerpo"})
        elif len(b_hits) > 1:
            ambiguous.append({"path": n["path"], "señal": "cuerpo",
                              "candidatos": sorted(e["canonical"] for e in b_hits)})
    for lst in (props, body_only, ambiguous):
        lst.sort(key=lambda p: p["path"])
    if args.json:
        print(json.dumps({"escribibles": props, "solo_cuerpo": body_only, "ambiguas": ambiguous},
                         ensure_ascii=False, indent=2))
        return 0
    print(f"{len(props)} propuestas escribibles (señal en el titulo) · por tipo {dict(Counter(p['type'] for p in props))}")
    print(f"{len(body_only)} candidatas solo por el cuerpo — NO se escriben, son `menciona`, no autoria")
    print(f"{len(ambiguous)} ambiguas (2+ candidatos) — decision humana\n")
    for p in props[:20]:
        print(f"  {p['client_name']:<30} {p['path']}")
    if len(props) > 20:
        print(f"  … y {len(props)-20} mas")
    if ambiguous:
        print("\nAmbiguas:")
        for a in ambiguous[:12]:
            print(f"  [{a['señal']}] {os.path.basename(a['path'])}  ->  {', '.join(a['candidatos'])}")
        if len(ambiguous) > 12:
            print(f"  … y {len(ambiguous)-12} mas")
    if not args.write:
        print("\n(dry-run — usa --write para escribir el frontmatter de las escribibles)")
        return 0
    written = 0
    for p in props:
        abs_path = os.path.join(BASE, p["path"])
        text = read(abs_path)
        fm, fmtxt, body = split_frontmatter(text)
        new_fm = fmtxt
        for key, val in (("client_name", f'"{p["client_name"]}"'), ("client_id", p["client_id"])):
            if re.search(rf"^{key}:", new_fm, re.M):
                new_fm = re.sub(rf"^{key}:.*$", f"{key}: {val}", new_fm, count=1, flags=re.M)
            else:
                new_fm = new_fm.rstrip("\n") + f"\n{key}: {val}"
        with open(abs_path, "w", encoding="utf-8") as fh:
            fh.write(f"---\n{new_fm}\n---\n{body}")
        written += 1
    print(f"\nescritas {written} notas (solo señal de titulo)")
    return 0

# ------------------------------------------------------------------------------- dates

def source_date_index():
    """source_id -> fecha real del evento, desde extraction-log.jsonl.

    `captured_on` es el dia en que se extrajo la nota, no el dia en que paso lo que
    cuenta: 40 decision-logs comparten captured_on 2026-08-08 porque salieron de la
    misma extraccion masiva. Sin la fecha del evento no hay eje temporal, y sin eje
    temporal `supersedes` no se puede computar ni a mano.
    """
    idx = {}
    for r in read_jsonl(os.path.join(CFG, "extraction-log.jsonl")):
        sid, sd = r.get("source_id"), r.get("source_date")
        if sid and is_date(sd or ""):
            idx.setdefault(sid, sd)
    return idx

def cmd_dates(args):
    idx = source_date_index()
    ns = [n for n in notes() if n["type"] in CANON_TYPES + TECH_TYPES]
    props, unresolved = [], []
    for n in ns:
        if is_date(n["fm"].get("occurred_on", "")):
            continue
        sid = n["fm"].get("source_id", "").strip().strip('"')
        if not filled(sid):
            continue
        if sid in idx:
            props.append({"path": n["path"], "type": n["type"], "occurred_on": idx[sid],
                          "captured_on": n["fm"].get("captured_on", "").strip('"'), "source_id": sid})
        else:
            unresolved.append({"path": n["path"], "source_id": sid})
    props.sort(key=lambda x: x["path"])
    drift = [p for p in props if p["occurred_on"] != p["captured_on"]]
    if args.json:
        print(json.dumps({"propuestas": props, "sin_resolver": unresolved}, ensure_ascii=False, indent=2))
        return 0
    print(f"{len(idx)} source_id con fecha real en extraction-log.jsonl")
    print(f"{len(props)} notas pueden ganar `occurred_on` · {len(unresolved)} con source_id que no resuelve")
    print(f"{len(drift)} de esas {len(props)} tienen occurred_on != captured_on "
          f"(es decir: hoy estan fechadas el dia de la extraccion, no el del evento)\n")
    for x in props[:12]:
        print(f"  {x['occurred_on']}  (captured {x['captured_on']})  {os.path.basename(x['path'])}")
    if len(props) > 12:
        print(f"  … y {len(props)-12} mas")
    if not args.write:
        print("\n(dry-run — usa --write para escribir occurred_on)")
        return 0
    for x in props:
        abs_path = os.path.join(BASE, x["path"])
        fm, fmtxt, body = split_frontmatter(read(abs_path))
        new_fm = fmtxt
        if re.search(r"^occurred_on:", new_fm, re.M):
            new_fm = re.sub(r"^occurred_on:.*$", f"occurred_on: {x['occurred_on']}", new_fm, count=1, flags=re.M)
        else:
            # justo encima de captured_on, para que se lean juntas
            if re.search(r"^captured_on:", new_fm, re.M):
                new_fm = re.sub(r"^(captured_on:)", f"occurred_on: {x['occurred_on']}\n\\1", new_fm, count=1, flags=re.M)
            else:
                new_fm = new_fm.rstrip("\n") + f"\noccurred_on: {x['occurred_on']}"
        with open(abs_path, "w", encoding="utf-8") as fh:
            fh.write(f"---\n{new_fm}\n---\n{body}")
    print(f"\nescritas {len(props)} notas con occurred_on")
    return 0

# ------------------------------------------------------------------------------ expiry

def cmd_expiry(args):
    """Compara el `expires_on` escrito con el que saldria de contar desde `occurred_on`.

    **La politica esta decidida (dueno del canon, 2026-09-09): el reloj cuenta desde `captured_on`.**
    La caducidad de este canon protege de "nadie ha mirado esto en mucho tiempo", no de "el
    mundo cambio desde que esto era cierto". Este comando ya no propone reanclar: mide la
    exposicion que deja esa eleccion — cuantas notas se presentan frescas mucho despues del
    evento que describen — para que el hueco sea visible en vez de silencioso.

    `--write` sigue existiendo pero exige `CB_REANCLAR=si` en el entorno: reanclar (en un despliegue
    real, 403 notas) va contra una decision escrita, y no debe estar a un flag de distancia.
    """
    ns = [n for n in notes() if n["type"] in EXPIRY_DAYS and EXPIRY_DAYS[n["type"]]]
    rows = []
    for n in ns:
        oc = n["fm"].get("occurred_on", "").strip().strip('"')
        ex = n["fm"].get("expires_on", "").strip().strip('"')
        if not is_date(oc):
            continue
        nuevo = (datetime.date.fromisoformat(oc) + datetime.timedelta(days=EXPIRY_DAYS[n["type"]])).isoformat()
        rows.append({"path": n["path"], "type": n["type"], "occurred_on": oc,
                     "expires_on_actual": ex if is_date(ex) else None, "expires_on_desde_evento": nuevo,
                     "expirada_hoy": bool(is_date(ex) and datetime.date.fromisoformat(ex) < TODAY),
                     "expirada_desde_evento": datetime.date.fromisoformat(nuevo) < TODAY})
    rows.sort(key=lambda r: r["path"])
    ahora = sum(1 for r in rows if r["expirada_hoy"])
    luego = sum(1 for r in rows if r["expirada_desde_evento"])
    # exposicion de la politica elegida: notas vivas cuyo evento ya cayo fuera de la ventana
    expuestas = [r for r in rows if not r["expirada_hoy"] and r["expirada_desde_evento"]]
    desfases = []
    for r in rows:
        cap = None
        for n in ns:
            if n["path"] == r["path"]:
                cap = n["fm"].get("captured_on", "").strip().strip('"')
                break
        if is_date(cap or ""):
            desfases.append((datetime.date.fromisoformat(cap)
                             - datetime.date.fromisoformat(r["occurred_on"])).days)
    desfases.sort()
    mediana = desfases[len(desfases)//2] if desfases else 0
    if args.json:
        print(json.dumps({"filas": rows, "expiradas_hoy": ahora, "expiradas_desde_evento": luego},
                         ensure_ascii=False, indent=2))
        return 0
    print(f"{len(rows)} notas con `occurred_on` y caducidad definida")
    print(f"  expiradas con el reloj actual (desde captured_on): {ahora}")
    print(f"  expiradas si el reloj cuenta desde occurred_on:    {luego}")
    print(f"\nDesfase evento -> captura: mediana {mediana} dias (n={len(desfases)})")
    print(f"\nEXPOSICION de la politica elegida: {len(expuestas)} notas se presentan frescas")
    print("aunque su evento ya cayo fuera de la ventana de vigencia de su tipo.")
    print("No es un bug: es lo que se acepta al contar desde la captura. Se mide para que")
    print("el hueco sea visible, y `retrieve` puede citar `occurred_on` al servirlas.")
    by_type = Counter(r["type"] for r in rows if r["expirada_desde_evento"] and not r["expirada_hoy"])
    if by_type:
        print(f"Por tipo: {dict(by_type.most_common())}")
    if args.write and os.environ.get("CB_REANCLAR") != "si":
        print(f"\n`--write` reanclaria {len(rows)} nota(s) al evento, contra la decision escrita del")
        print("2026-09-09. Si de verdad quieres cambiar la politica: CB_REANCLAR=si")
        return 1
    if args.write:
        for r in rows:
            abs_path = os.path.join(BASE, r["path"])
            fm, fmtxt, body = split_frontmatter(read(abs_path))
            new_fm = re.sub(r"^expires_on:.*$", f'expires_on: "{r["expires_on_desde_evento"]}"',
                            fmtxt, count=1, flags=re.M)
            with open(abs_path, "w", encoding="utf-8") as fh:
                fh.write(f"---\n{new_fm}\n---\n{body}")
        print(f"\nreescrito expires_on en {len(rows)} notas, contando desde occurred_on")
    else:
        print("\n(este comando no escribe: la politica de anclaje ya esta decidida.)")
    return 0

# ------------------------------------------------------------------------ supersession

def cmd_supersession(args):
    """Agrupa decision-logs por entidad y solape de search_terms y saca los pares
    ordenados por fecha. NUNCA escribe: el juicio de si B supera a A es humano (C2)."""
    dls = [n for n in notes() if n["type"] == "decision-log"]
    def terms(n):
        seg = n["fmtxt"].split("search_terms:")[-1] if "search_terms:" in n["fmtxt"] else ""
        return {norm(t.split("|")[0]) for t in re.findall(r"\[\[([^\]]+)\]\]", seg)}
    def key(n):
        c = n["fm"].get("client_name", "").strip().strip('"')
        return norm(c) if filled(c) else None
    def when(n):
        for f in ("occurred_on", "captured_on"):
            v = n["fm"].get(f, "").strip().strip('"')
            if is_date(v):
                return v
        return ""
    groups = defaultdict(list)
    for n in dls:
        k = key(n)
        if k:
            groups["cliente:" + k].append(n)
    pairs = []
    for g, rows in sorted(groups.items()):
        rows.sort(key=lambda n: (when(n), n["path"]))
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                a, b = rows[i], rows[j]
                shared = terms(a) & terms(b)
                # sin fechas distintas no hay "antigua" ni "nueva": dos decisiones del
                # mismo dia son dos decisiones, no una superada. Este filtro es la razon
                # de que `dates` tenga que correr antes que esto.
                if len(shared) >= 2 and when(a) and when(b) and when(a) < when(b):
                    pairs.append({"grupo": g, "antigua": a["path"], "nueva": b["path"],
                                  "fecha_antigua": when(a), "fecha_nueva": when(b),
                                  "dias": (datetime.date.fromisoformat(when(b))
                                           - datetime.date.fromisoformat(when(a))).days,
                                  "terminos_compartidos": sorted(shared)[:6]})
    pairs.sort(key=lambda p: (p["grupo"], p["fecha_nueva"], p["antigua"]))
    if args.json:
        print(json.dumps({"pares": pairs, "grupos": len(groups)}, ensure_ascii=False, indent=2))
        return 0
    print(f"{len(dls)} decision-logs · {len(groups)} grupos por cliente · {len(pairs)} pares candidatos")
    print("(candidato = mismo cliente + >=2 search_terms compartidos + fechas de evento distintas;")
    print(" NO es un juicio de supersesion — eso lo decide una persona en `validate`)\n")
    for p in pairs[:30]:
        print(f"  {p['grupo']}\n    antigua {p['fecha_antigua']}  {os.path.basename(p['antigua'])}"
              f"\n    nueva   {p['fecha_nueva']}  {os.path.basename(p['nueva'])}  (+{p['dias']} dias)"
              f"\n    comparten: {', '.join(p['terminos_compartidos'])}\n")
    if len(pairs) > 30:
        print(f"  … y {len(pairs)-30} pares mas")
    print("Siguiente paso: leer cada par y, si B supera a A, escribir `supersedes: [[A]]` en B "
          "y `status: superseded` en A. Nunca automatico (C2).")
    return 0

# -------------------------------------------------------------------------------- cruce

def shareable_problems():
    """Los problemas compartibles con sus clientes, leidos de `occurrences`.

    `occurrences` es la lista estructurada que C18 exige: una entrada por vez que el
    problema aparecio, con fecha, cliente y cita. El conteo se lee de ahi, nunca se
    recalcula ni se estima.
    """
    out = []
    for n in notes():
        if n["type"] != "observation":
            continue
        if not re.search(r"^shareable:\s*true", n["fmtxt"], re.M):
            continue
        occ = yaml_block(n["fmtxt"], "occurrences")
        cids = re.findall(r"client_id:\s*\"?(cid-\d+)\"?", occ)
        # las fechas aparecen con y sin comillas en el canon; las dos formas cuentan
        fechas = sorted(re.findall(r"date:\s*[\"']?(\d{4}-\d{2}-\d{2})", occ))
        tag = (n["fm"].get("problem_tag") or "").strip().strip('"')
        out.append({"tag": tag or os.path.basename(n["path"])[:-3], "path": n["path"],
                    "titulo": (n["fm"].get("title") or "").strip().strip('"'),
                    "severity": (n["fm"].get("severity") or "").strip(),
                    "clientes": sorted(set(cids)), "ocurrencias": len(fechas),
                    "primera": fechas[0] if fechas else "", "ultima": fechas[-1] if fechas else ""})
    out.sort(key=lambda x: (-len(x["clientes"]), -x["ocurrencias"], x["tag"]))
    return out

def cmd_cruce(args):
    """Responde «que clientes con el canal C han tenido el problema X».

    Es un join, no un recorrido de grafo: el canal sale de `entities.json` (derivado del
    frontmatter) y el problema de `occurrences`. No hace falta grafo para esto y por eso
    no lo usa.
    """
    ents, _ = build_entities()
    by_cid = {e["client_id"]: e for e in ents if e["client_id"]}
    probs = shareable_problems()
    canal = args.canal
    def canales(e, incluir_pistas):
        c = set(e.get("canales_declarados") or ())
        if incluir_pistas:
            c |= set(e.get("canales_mencionados") or ())
        return c
    def tiene(cid):
        e = by_cid.get(cid)
        return bool(e) and (not canal or any(norm(canal) in norm(x) for x in canales(e, args.pistas)))

    filas = []
    for pr in probs:
        if args.problema and norm(args.problema) not in norm(pr["tag"]) and norm(args.problema) not in norm(pr["titulo"]):
            continue
        inter = [c for c in pr["clientes"] if tiene(c)]
        if canal and not inter:
            continue
        filas.append({**pr, "clientes_con_canal": inter,
                      "nombres": [by_cid[c]["canonical"] if c in by_cid else c for c in inter],
                      "senal": {(by_cid[c]["canonical"] if c in by_cid else c):
                                ("declarado" if canal and canal_declarado(by_cid.get(c), canal) else
                                 "mencion" if canal else "—") for c in inter}})
    if args.json:
        print(json.dumps({"canal": canal, "problema": args.problema, "filas": filas},
                         ensure_ascii=False, indent=2))
        return 0
    cab = f"problemas compartibles" + (f" · canal {canal}" if canal else "") + \
          (f" · problema ~{args.problema}" if args.problema else "")
    print(f"{cab}\n")
    if not filas:
        print("  nada cruza. Prueba sin --canal, o con --pistas para incluir las menciones de cuerpo.")
        return 0
    for f in filas[:args.limite]:
        marca = " ".join(f"{n} [{f['senal'][n]}]" for n in f["nombres"])
        print(f"  {f['tag']}  ({f['severity'] or 'sin severidad'})")
        print(f"      {len(f['clientes'])} cliente(s) en total · {f['ocurrencias']} ocurrencia(s)"
              + (f" · {f['primera']} → {f['ultima']}" if f["primera"] else ""))
        print(f"      con el canal: {marca or '—'}")
    if len(filas) > args.limite:
        print(f"\n  … y {len(filas)-args.limite} problemas mas (usa --limite)")
    multi = sum(1 for f in filas if len(f["clientes"]) >= 2)
    print(f"\n{len(filas)} problemas · {multi} afectan a 2+ clientes.")
    if not args.pistas and canal:
        print("Solo se cuentan canales DECLARADOS en `search_terms`. `--pistas` incluye las")
        print("menciones en el cuerpo, que son una pista y no un hecho del cliente (C30).")
    return 0

def canal_declarado(e, canal):
    return bool(e) and any(norm(canal) in norm(x) for x in (e.get("canales_declarados") or ()))

# --------------------------------------------------------------------------- normalizar

def cmd_normalizar(args):
    """Tarea 0.4 del plan: un mismo valor escrito de dos formas es dos valores para
    cualquier filtro. `project: "Kestrel"` y `project: Kestrel` convivian 930 contra 232 en un despliegue real.
    No es cosmetico: `retrieve --project Kestrel` con comparacion literal pierde un tercio
    del canon segun como se escriba el filtro."""
    CAMPOS = ("project", "source_project", "company_brain_track", "type", "layer",
              "confidence", "status", "severity", "kind")
    cambios = []
    for n in notes(include_noncontract=True):
        nuevo = n["fmtxt"]
        for campo in CAMPOS:
            for m in list(re.finditer(rf'^{campo}:[ \t]*(.+)$', nuevo, re.M)):
                raw = m.group(1).strip()
                if not raw or raw.startswith(("[", "-", "{")):
                    continue
                limpio = raw.strip('"').strip("'").strip()
                if limpio != raw and limpio and '"' not in limpio and "'" not in limpio:
                    nuevo = nuevo[:m.start(1)] + limpio + nuevo[m.end(1):]
                    cambios.append({"path": n["path"], "campo": campo, "de": raw, "a": limpio})
                    break
        if nuevo != n["fmtxt"] and args.write:
            with open(os.path.join(BASE, n["path"]), "w", encoding="utf-8") as fh:
                fh.write(f"---\n{nuevo}\n---\n{n['body']}")
    por_campo = Counter(c["campo"] for c in cambios)
    if args.json:
        print(json.dumps({"cambios": cambios, "por_campo": dict(por_campo)}, ensure_ascii=False, indent=2))
        return 0
    print(f"{len(cambios)} valores escalares entrecomillados que deberian ser desnudos")
    print(f"por campo: {dict(por_campo.most_common())}")
    print(f"notas afectadas: {len({c['path'] for c in cambios})}")
    print("\nSolo toca escalares de vocabulario cerrado. NO toca `title`, `client_name` ni")
    print("nada con espacios o acentos: ahi las comillas son correctas.")
    if not args.write:
        print("\n(dry-run — usa --write)")
    else:
        print("\nescrito")
    return 0

# ------------------------------------------------------------------------------- firma

def corpus_signature():
    """Huella del corpus + del codigo que deriva de el.

    Un artefacto derivado committeado en git caduca en silencio: el fichero sigue ahi,
    parece valido, y quien lo consulta recibe respuestas de anteayer sin ningun aviso. Paso
    de verdad — el grafo estaba 160 aristas obsoleto tres horas despues de escribirlo,
    porque otra sesion metio 195 notas.

    La firma cubre las dos cosas que pueden invalidar un derivado: el contenido del que
    sale (el frontmatter de cada nota, no su mtime — que cambia al clonar y no significa
    nada) y el codigo que lo deriva (cambiar un verbo del grafo invalida; un `touch` no).
    Mismo patron que la cache del motor de retrieval del vault personal.
    """
    h = hashlib.sha256()
    for n in notes(include_noncontract=True):
        h.update(n["path"].encode())
        h.update(hashlib.sha1(n["fmtxt"].encode()).digest())
    for extra in ("client-directory.json", "ontology.json", "graph.jsonl", OVERRIDES):
        h.update(hashlib.sha1(read(os.path.join(CFG, extra)).encode()).digest())
    h.update(hashlib.sha1(read(os.path.abspath(__file__)).encode()).digest())
    return h.hexdigest()[:16]

def stamp(obj):
    """Sella un derivado con su firma y la fecha."""
    return {"_meta": {"schema": "company-brain/derivado/1", "firma": corpus_signature(),
                      "generado": TODAY.isoformat(),
                      "aviso": ("Derivado y regenerable. Si la firma no coincide con la del corpus "
                                "de ahora, este fichero esta obsoleto: regeneralo antes de fiarte."),
                      **obj}}

def check_fresh(path, quiet=False):
    """Compara la firma guardada con la del corpus de ahora. Avisa, no aborta: un derivado
    obsoleto sigue siendo util para muchas preguntas, y abortar seria peor que avisar."""
    primera = (read(path).split("\n", 1)[0] or "").strip()
    guardada = None
    if primera.startswith("{"):
        try:
            guardada = (json.loads(primera).get("_meta") or {}).get("firma")
        except ValueError:
            pass
    if guardada is None:
        if not quiet:
            print(f"aviso: {os.path.basename(path)} no lleva firma — no se puede saber si esta al dia",
                  file=sys.stderr)
        return None
    ahora = corpus_signature()
    if guardada != ahora and not quiet:
        print(f"AVISO: {os.path.basename(path)} esta OBSOLETO (firma {guardada}, corpus {ahora}).",
              file=sys.stderr)
        print("       Regeneralo: python3 tools/cb.py grafo --write", file=sys.stderr)
    return guardada == ahora

# ------------------------------------------------------------------------------- grafo

# El grafo derivado de entidades. NO se mezcla con `graph.jsonl`, que es el grafo de juicio
# humano (50 aristas, 4 verbos, cada una confirmada por una persona): ese no se regenera
# nunca y vale mas que este. Este se tira y se reconstruye en segundos, y por eso puede
# permitirse aristas debiles siempre que digan que lo son.
#
# Por que existe, y por que un join no bastaba: `cruce` responde cliente x problema x canal.
# La siguiente pregunta ("que sistemas toca este cliente", "que clientes comparten esta
# integracion", "de que fuente salio todo lo que sabemos de X") necesitaba otro join a
# medida. Con las relaciones como aristas, una primitiva de recorrido responde a la familia
# entera. Y ademas recupera lo que el backfill de `clients` tiro a la basura a proposito:
# las 125 menciones de cliente en el cuerpo, que no son autoria (C30) pero SI son relacion.
GRAPH_FILE = "entity-graph.jsonl"

def cmd_grafo(args):
    ents, _ = build_entities()
    by_cid = {e["client_id"]: e for e in ents if e["client_id"]}
    ns = notes()
    edges = []
    hoy = TODAY.isoformat()

    def add(frm, ftype, rel, to, ttype, via, method="derivado", weight=1.0, **extra):
        edges.append({"from": frm, "from_type": ftype, "rel": rel, "to": to, "to_type": ttype,
                      "weight": weight, "method": method, "declared_via": via,
                      "declared_on": hoy, **extra})

    # nota -> cliente, con el verbo que le toca por tipo de nota
    REL_BY_TYPE = {"decision-log": "decide_sobre", "observation": "observa_a",
                   "process": "describe_para", "context-map": "mapea_a", "plan": "planifica_para"}
    ent_alias = [(a, e) for e in ents if e["client_id"] for a in [norm(e["canonical"])] + e["aliases"] if a]
    # alias -> client_id. No hace falta podar los ambiguos aqui: `build_entities` ya los
    # ha sacado de `aliases` antes de devolverlos, asi que `ent_alias` no los contiene.
    # Habia una segunda poda en este punto y era codigo muerto — lo destapo una mutacion de
    # los tests, que se quedaron verdes al borrarla. El test que guarda la propiedad (un
    # `search_terms: [[OMNI]]` no resuelve a ninguno de los dos clientes) se queda: afirma el
    # comportamiento, no la implementacion, y sigue valiendo si la poda cambia de sitio.
    alias_to_cid = {a: e["client_id"] for a, e in ent_alias}

    for n in ns:
        rel = REL_BY_TYPE.get(n["type"])
        cids = client_ids_of(n["fmtxt"])
        # la fecha del evento viaja en la arista: sin ella la ficha de cliente es una lista,
        # no una cronologia, y el outcome 2 del plan pedia una cronologia
        cuando = ""
        for f in ("occurred_on", "captured_on"):
            v = n["fm"].get(f, "").strip().strip('"')
            if is_date(v):
                cuando = v
                break
        for c in cids:
            if rel:
                add(n["path"], "nota", rel, c, "cliente",
                    "cb.py grafo — client_id del frontmatter", weight=1.0, date=cuando)
        # nota -> entidad, por search_terms declarados. Si el termino ES un cliente
        # conocido, la arista va al NODO DE CLIENTE, no a un nodo de entidad con el mismo
        # nombre: si no, el mismo cliente vive dos veces en el grafo y ningun recorrido
        # encuentra todo lo suyo. Es el objeto entero de "entidades resueltas".
        for t in wikilinks(n["fmtxt"], "search_terms"):
            cid = alias_to_cid.get(norm(t))
            if cid:
                if cid not in cids:
                    add(n["path"], "nota", "trata_de", cid, "cliente",
                        "cb.py grafo — search_term que resuelve a un cliente", weight=1.0)
            else:
                add(n["path"], "nota", "trata_de", t, "entidad",
                    "cb.py grafo — search_terms del frontmatter", weight=1.0)
        # nota -> cliente por MENCION en el cuerpo. Arista debil y tipada como tal: no es
        # autoria (C30), pero tirarla era perder informacion que existe.
        body = norm(n["body"][:4000])
        for a, e in ent_alias:
            if e["client_id"] in cids:
                continue
            if re.search(r"\b" + re.escape(a) + r"\b", body):
                add(n["path"], "nota", "menciona", e["client_id"], "cliente",
                    "cb.py grafo — coincidencia de alias en el cuerpo", weight=0.3)
        # nota -> carpeta/tipo
        add(n["path"], "nota", "es_de_tipo", n["type"], "tipo",
            "cb.py grafo — campo type", weight=1.0)

    # fuente -> notas que produjo
    for n in ns:
        if n["type"] != "source-raw":
            continue
        for g in re.findall(r"[-\s]\"?([A-Za-z0-9][^\"\n]*\.md)\"?", yaml_block(n["fmtxt"], "notes_generated")):
            add(n["path"], "nota", "fuente_de", "Context/" + g.strip().lstrip("/"), "nota",
                "cb.py grafo — notes_generated del frontmatter", weight=1.0)

    # cliente -> canal
    for e in ents:
        if not e["client_id"]:
            continue
        for ch in e.get("canales_declarados") or ():
            add(e["client_id"], "cliente", "usa_canal", ch, "canal",
                "cb.py grafo — familia de canal en search_terms de sus notas", weight=1.0)
        for ch in e.get("canales_mencionados") or ():
            add(e["client_id"], "cliente", "menciona_canal", ch, "canal",
                "cb.py grafo — familia de canal solo en el cuerpo", weight=0.3)

    # problema -> cliente, con la fecha de la ocurrencia
    for pr in shareable_problems():
        add(pr["path"], "nota", "es_problema", pr["tag"], "problema",
            "cb.py grafo — problem_tag del frontmatter", weight=1.0)
        occ = yaml_block(read_fm(pr["path"]), "occurrences")
        pares = re.findall(r"date:\s*[\"']?(\d{4}-\d{2}-\d{2})[\"']?\s*\n\s*client_id:\s*[\"']?(cid-\d+)",
                           occ)
        for fecha, cid in pares:
            add(pr["tag"], "problema", "afecta_a", cid, "cliente",
                "cb.py grafo — entrada de occurrences", weight=1.0, date=fecha)

    # el grafo de juicio humano se INCORPORA por referencia, sin copiarse ni regenerarse
    humano = read_jsonl(os.path.join(CFG, "graph.jsonl"))
    for h in humano:
        add("Context/" + h["source"] + ".md", "nota", h["rel"], "Context/" + h["target"] + ".md",
            "nota", h.get("declared_via", "enrich — confirmado por una persona"),
            method="humano", weight=1.0)

    # aristas identicas (mismo origen, verbo, destino y fecha) no aportan nada: dos
    # ocurrencias del mismo problema el mismo dia son un dato de `occurrences`, no dos aristas
    vistas, unicas = set(), []
    for e in edges:
        k = (str(e["from"]), e["rel"], str(e["to"]), e.get("date", ""))
        if k in vistas:
            continue
        vistas.add(k)
        unicas.append(e)
    dup = len(edges) - len(unicas)
    edges = unicas
    edges.sort(key=lambda e: (e["rel"], str(e["from"]), str(e["to"])))
    by_rel = Counter(e["rel"] for e in edges)
    nodos = {(e["from_type"], e["from"]) for e in edges} | {(e["to_type"], e["to"]) for e in edges}
    by_ntype = Counter(t for t, _ in nodos)
    if args.json:
        print(json.dumps({"aristas": len(edges), "por_verbo": dict(by_rel.most_common()),
                          "nodos": len(nodos), "por_tipo_de_nodo": dict(by_ntype.most_common())},
                         ensure_ascii=False, indent=2))
    else:
        print(f"grafo derivado: {len(edges)} aristas · {len(nodos)} nodos"
              + (f" ({dup} duplicadas descartadas)" if dup else ""))
        print(f"\nnodos por tipo: {dict(by_ntype.most_common())}")
        print("\naristas por verbo:")
        for r, c in by_rel.most_common():
            m = "humano" if r in ("extiende", "depende-de", "refuerza", "contradice") else "derivado"
            print(f"  {c:>6}  {r:<16} ({m})")
        debiles = sum(1 for e in edges if e["weight"] < 1.0)
        print(f"\n{debiles} aristas debiles (weight 0.3): son menciones, no atribuciones (C30).")
        print(f"{sum(1 for e in edges if e['method']=='humano')} aristas de juicio humano, "
              "incorporadas por referencia desde graph.jsonl (no se regeneran).")
    if args.write:
        out = os.path.join(CFG, GRAPH_FILE)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(stamp({"aristas": len(edges), "nodos": len(nodos)}),
                                ensure_ascii=False, sort_keys=True) + "\n")
            for e in edges:
                fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
        print(f"\nescrito Context/_skill-config/{GRAPH_FILE}")
    elif not args.json:
        print("\n(dry-run — usa --write para escribir el grafo)")
    return 0

def load_graph():
    path = os.path.join(CFG, GRAPH_FILE)
    check_fresh(path)
    rows = [r for r in read_jsonl(path) if "_meta" not in r]
    out, inc = defaultdict(list), defaultdict(list)
    for e in rows:
        out[str(e["from"])].append(e)
        inc[str(e["to"])].append(e)
    return rows, out, inc

def resolve_node(term, rows):
    """Un nodo por texto: acepta la ruta exacta, un client_id, un nombre de cliente,
    un problem_tag o un trozo de cualquiera de ellos. Devuelve los candidatos."""
    t = norm(term)
    nodes = {}
    for e in rows:
        nodes[str(e["from"])] = e["from_type"]
        nodes[str(e["to"])] = e["to_type"]
    # el nombre de un cliente resuelve SIEMPRE a su nodo de cliente, aunque exista una
    # entidad con el mismo texto: lo contrario devolvia media ficha sin avisar
    ents, _ = build_entities()
    for e in ents:
        if e["client_id"] and e["client_id"] in nodes and (
                t == norm(e["canonical"]) or t in [norm(a) for a in e["aliases"]]):
            return [(e["client_id"], "cliente")]
    exact = [n for n in nodes if norm(n) == t]
    if exact:
        return [(n, nodes[n]) for n in sorted(exact)]
    for e in ents:
        if e["client_id"] and (t == norm(e["canonical"]) or t in [norm(a) for a in e["aliases"]]
                               or t in norm(e["canonical"])):
            if e["client_id"] in nodes:
                return [(e["client_id"], "cliente")]
    part = [n for n in nodes if t in norm(n)]
    return [(n, nodes[n]) for n in sorted(part)[:12]]

def cmd_vecinos(args):
    """Recorre el grafo derivado desde un nodo. Es la primitiva que convierte el grafo en
    algo consultable: `cruce` es un caso particular de esto."""
    rows, out, inc = load_graph()
    if not rows:
        print(f"falta Context/_skill-config/{GRAPH_FILE} — corre `cb.py grafo --write`", file=sys.stderr)
        return 1
    cands = resolve_node(args.nodo or "", rows)
    if not cands:
        print(f"no encuentro ningun nodo que case con {args.nodo!r}")
        return 1
    if len(cands) > 1:
        print(f"{args.nodo!r} casa con {len(cands)} nodos — precisa:")
        for n, t in cands[:12]:
            print(f"  [{t}] {n}")
        return 1
    start, stype = cands[0]
    ents, _ = build_entities()
    label = {e["client_id"]: e["canonical"] for e in ents if e["client_id"]}
    def name(n, t):
        return f"{label.get(n, n)}" if t == "cliente" else str(n)

    seen = {start}
    frontera = [(start, stype, 0, [])]
    filas = []
    rels = [r.strip() for r in (args.rel or "").split(",") if r.strip()]
    while frontera:
        node, ntype, depth, camino = frontera.pop(0)
        if depth >= args.saltos:
            continue
        vecinas = [(e, "→") for e in out.get(node, [])] + [(e, "←") for e in inc.get(node, [])]
        for e, dirn in vecinas:
            if rels and e["rel"] not in rels:
                continue
            if not args.debiles and e["weight"] < 1.0:
                continue
            other = str(e["to"]) if dirn == "→" else str(e["from"])
            otype = e["to_type"] if dirn == "→" else e["from_type"]
            filas.append({"salto": depth + 1, "dir": dirn, "rel": e["rel"], "nodo": other,
                          "tipo": otype, "method": e["method"], "weight": e["weight"],
                          "date": e.get("date", ""), "desde": node})
            if other not in seen:
                seen.add(other)
                frontera.append((other, otype, depth + 1, camino + [e["rel"]]))
    if args.json:
        print(json.dumps({"nodo": start, "tipo": stype, "vecinos": filas}, ensure_ascii=False, indent=2))
        return 0
    print(f"[{stype}] {name(start, stype)}   ({len(filas)} aristas hasta {args.saltos} salto(s))\n")
    for salto in range(1, args.saltos + 1):
        grupo = [f for f in filas if f["salto"] == salto]
        if not grupo:
            continue
        print(f"  — salto {salto} —")
        for rel, items in sorted(collections_groupby(grupo, "rel")):
            print(f"    {rel} ({len(items)})")
            items = sorted(items, key=lambda x: (x["date"] or "9999", str(x["nodo"])))
            for f in items[:args.limite]:
                extra = f"  {f['date']}" if f["date"] else ""
                marca = "" if f["method"] == "derivado" else "  [humano]"
                print(f"        {f['dir']} [{f['tipo']}] {name(f['nodo'], f['tipo'])}{extra}{marca}")
            if len(items) > args.limite:
                print(f"        … y {len(items)-args.limite} mas")
    if not args.debiles:
        print("\n(se omiten las aristas debiles — `--debiles` incluye las menciones de cuerpo)")
    return 0

def collections_groupby(rows, key):
    d = defaultdict(list)
    for r in rows:
        d[r[key]].append(r)
    return sorted(d.items())

def read_fm(relpath):
    return split_frontmatter(read(os.path.join(BASE, relpath)))[1]

# ------------------------------------------------------------------ contradicciones

def cmd_contradicciones(args):
    """Tarea 3.4 del plan: el informe regenerable de contradicciones y supersesiones.

    Es el equivalente de la pestana Contradictions que vende Synapses, en markdown y
    versionado. Nombre fijo y regenerable a proposito: un informe con fecha en el nombre se
    convierte en cuarenta informes y nadie sabe cual mirar.

    Lo que reporta no es lo que un LLM crea que se contradice: son las tres fuentes
    verificables — el campo `contradicted` que escriben los hooks, las aristas `contradice`
    que confirmo una persona, y los `supersedes` rellenos — mas los candidatos mecanicos,
    marcados como candidatos.
    """
    ns = notes()
    contradichas = [n for n in ns if re.search(r"^contradicted:\s*true", n["fmtxt"], re.M)]
    supersede = [n for n in ns if filled(n["fm"].get("supersedes"))]
    humano = read_jsonl(os.path.join(CFG, "graph.jsonl"))
    aristas = [h for h in humano if h.get("rel") == "contradice"]
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_supersession(argparse.Namespace(json=True, write=False))
    cands = json.loads(buf.getvalue())["pares"]

    L = ["---", "type: report", 'title: "Contradicciones y supersesiones del canon"',
         f"project: {project_name()}", "company_brain_track: canon",
         f"generated_on: {TODAY.isoformat()}",
         'generated_by: "python3 tools/cb.py contradicciones --write"',
         "regenerable: true", "---", "",
         "# Contradicciones y supersesiones", "",
         "**Regenerable**: `python3 tools/cb.py contradicciones --write`. Nombre fijo a proposito —",
         "un informe con la fecha en el nombre se convierte en cuarenta informes y nadie sabe cual",
         "mirar. Lo que hay aqui son las tres fuentes verificables, no lo que un modelo opine.", "",
         "## 1. Notas contradichas por la realidad (`contradicted: true`)", "",
         "Lo escriben los hooks de `maintain` al comprobar una nota contra un sistema externo.",
         "Nunca lo escribe una persona ni una arista del grafo (C28).", ""]
    if contradichas:
        L += ["| nota | tipo | cliente |", "|---|---|---|"]
        for n in contradichas:
            L.append(f"| `{os.path.basename(n['path'])[:-3]}` | {n['type']} | "
                     f"{(n['fm'].get('client_name') or '—').strip(chr(34))} |")
    else:
        L.append("Ninguna. Los hooks de `metric` estan sin cablear (`skipped`, C12), asi que este")
        L.append("apartado no puede tener contenido todavia: su vacio es una dependencia externa,")
        L.append("no una senal de que el canon sea coherente.")
    L += ["", f"## 2. Contradicciones confirmadas por una persona (aristas `contradice`)", "",
          "Del grafo de juicio humano, `_skill-config/graph.jsonl`. Una arista aqui NO marca",
          "`contradicted`: encola las dos notas en `validate` con prioridad maxima (C28).", ""]
    if aristas:
        L += ["| A | B | por que | declarada |", "|---|---|---|---|"]
        for h in aristas:
            L.append(f"| `{h['source']}` | `{h['target']}` | {h.get('note','—')} | {h.get('declared_on','—')} |")
    else:
        L.append(f"Ninguna de las {len(humano)} aristas del grafo humano es `contradice` "
                 f"({dict(Counter(h.get('rel') for h in humano).most_common())}).")
        L.append(f"Con 4 verbos y {len(humano)} aristas confirmadas, cero contradicciones es un resultado")
        L.append("plausible, no un fallo: forzar una arista falsa cuesta mas que dejar el hueco (G13).")
    L += ["", "## 3. Supersesiones declaradas (`supersedes` relleno)", ""]
    if supersede:
        L += ["| la nueva | supera a | fecha del evento |", "|---|---|---|"]
        for n in supersede:
            L.append(f"| `{os.path.basename(n['path'])[:-3]}` | {n['fm'].get('supersedes')} | "
                     f"{n['fm'].get('occurred_on','—')} |")
    else:
        n_dl = sum(1 for n in notes() if n["type"] == "decision-log")
        L.append(f"**Ninguna, 0 de {n_dl} decision-logs.** Si `occurred_on` falta, no es descuido:")
        L.append("es **incomputable**. Con solo `captured_on` (el dia de la extraccion) varias")
        L.append("decisiones comparten fecha si salieron de la misma pasada, y no hay forma de")
        L.append("decir cual era la antigua. Con `occurred_on` ya se puede, y de ahi sale el")
        L.append("apartado 4.")
    L += ["", "## 4. Candidatos mecanicos, pendientes de juicio humano", "",
          "Mismo cliente + >=2 `search_terms` compartidos + **fechas de evento distintas**.",
          "Esto **no es** un juicio de supersesion: quien supera a quien lo decide una persona",
          "en `validate` (C2). Apuesta abierta `bet-0002` sobre si alguno resulta real.", ""]
    if cands:
        L += ["| antigua | fecha | la nueva | fecha | Δ | comparten |", "|---|---|---|---|---|---|"]
        for c in cands:
            L.append(f"| `{os.path.basename(c['antigua'])[:-3]}` | {c['fecha_antigua']} | "
                     f"`{os.path.basename(c['nueva'])[:-3]}` | {c['fecha_nueva']} | +{c['dias']}d | "
                     f"{', '.join(c['terminos_compartidos'][:4])} |")
    else:
        L.append("Ninguno.")
    L += ["", "## Que hacer con un candidato", "",
          "1. **B supera a A** → `supersedes: [\"[[A]]\"]` en B. `maintain` derivara `superseded_by`",
          "   en A y `retrieve` la degradara (x0.1). No archivar A: la traza importa.",
          "2. **Se contradicen sin que una supere a la otra** → las dos a `validation-queue.json`",
          "   con prioridad maxima (C28). Nunca marcar `contradicted` a mano.",
          "3. **Independientes** → no tocar nada. Compartir cliente y vocabulario no es superarse.", "",
          f"*{len(contradichas)} contradichas por hooks · {len(aristas)} confirmadas por una persona · "
          f"{len(supersede)} supersesiones declaradas · {len(cands)} candidatos.*", ""]
    txt = "\n".join(L)
    if args.json:
        print(json.dumps({"contradichas": len(contradichas), "aristas_contradice": len(aristas),
                          "supersesiones": len(supersede), "candidatos": len(cands)},
                         ensure_ascii=False, indent=2))
        return 0
    print(f"{len(contradichas)} contradichas por hooks · {len(aristas)} aristas `contradice` humanas · "
          f"{len(supersede)} supersesiones declaradas · {len(cands)} candidatos")
    if args.write:
        out = os.path.join(REPORTS, "contradictions.md")
        os.makedirs(REPORTS, exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(txt)
        print(f"escrito Context/_reports/contradictions.md")
    else:
        print("(dry-run — usa --write para regenerar Context/_reports/contradictions.md)")
    return 0

# ------------------------------------------------------------------------------- gates

def cmd_gates(args):
    contract = load_json(os.path.join(CFG, "metrics.json"), None)
    if contract is None:
        print("falta Context/_skill-config/metrics.json — no hay contrato que evaluar", file=sys.stderr)
        return 1
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_stats(argparse.Namespace(json=True, write=False))
    st = json.loads(buf.getvalue())

    def resolve(path):
        cur = st
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return None
        return cur

    rows = []
    for m in contract.get("metrics", []):
        num, den = resolve(m["numerador"]), (resolve(m["denominador"]) if m.get("denominador") else None)
        if num is None:
            rows.append({"id": m["id"], "estado": "sin_dato", "valor": None, "gate": m.get("gate"),
                         "unidad": m.get("unidad"), "que_mide": m["que_mide"]})
            continue
        val = (num / den) if den not in (None, 0) else float(num)
        gate, warn = m.get("gate"), m.get("aviso")
        direction = m.get("direccion", "mas_es_mejor")
        def below(x, thr):
            return x < thr if direction == "mas_es_mejor" else x > thr
        estado = "verde"
        if gate is not None and below(val, gate):
            estado = "rojo"
        elif warn is not None and below(val, warn):
            estado = "ambar"
        rows.append({"id": m["id"], "estado": estado, "valor": round(val, 4), "gate": gate,
                     "aviso": warn, "unidad": m.get("unidad"), "que_mide": m["que_mide"],
                     "numerador": num, "denominador": den})
    # la tira: metricas que se miran y no bloquean. Existen porque el numero correcto
    # todavia no se conoce, y un gate inventado es un gate que nadie audita.
    strip = []
    for m in contract.get("tira", []):
        num, den = resolve(m["numerador"]), (resolve(m["denominador"]) if m.get("denominador") else None)
        val = None if num is None else ((num / den) if den not in (None, 0) else float(num))
        strip.append({"id": m["id"], "valor": None if val is None else round(val, 4),
                      "unidad": m.get("unidad"), "que_mide": m["que_mide"]})

    run = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "tag": args.tag or "manual", "project": PROJECT,
           "rojo": sum(1 for r in rows if r["estado"] == "rojo"),
           "ambar": sum(1 for r in rows if r["estado"] == "ambar"),
           "verde": sum(1 for r in rows if r["estado"] == "verde"),
           "sin_dato": sum(1 for r in rows if r["estado"] == "sin_dato"),
           "metrics": {r["id"]: r["valor"] for r in rows},
           "tira": {r["id"]: r["valor"] for r in strip}}
    if args.json:
        print(json.dumps({"run": run, "rows": rows, "tira": strip}, ensure_ascii=False, indent=2))
    else:
        icon = {"rojo": "ROJO ", "ambar": "AMBAR", "verde": "verde", "sin_dato": "  —  "}
        print(f"gates del canon · {project_name()} · {TODAY}\n")
        for r in rows:
            v = "—" if r["valor"] is None else (f"{100*r['valor']:.1f} %" if r.get("unidad") == "fraccion" else f"{r['valor']:g}")
            thr = "" if r["gate"] is None else f"  (gate {100*r['gate']:.0f} %)" if r.get("unidad") == "fraccion" else f"  (gate {r['gate']:g})"
            print(f"  [{icon[r['estado']]}] {r['id']:<34} {v:>9}{thr}")
            print(f"           {r['que_mide']}")
        if strip:
            print("\n  tira (sin gate a proposito):")
            for r in strip:
                v = "—" if r["valor"] is None else (f"{100*r['valor']:.1f} %" if r.get("unidad") == "fraccion" else f"{r['valor']:g}")
                print(f"    {r['id']:<34} {v:>9}")
        print(f"\n{run['rojo']} rojo · {run['ambar']} ambar · {run['verde']} verde · {run['sin_dato']} sin dato")
    if args.write:
        append_jsonl(os.path.join(CFG, "runs.jsonl"), run)
        print("\nanotado en Context/_skill-config/runs.jsonl")
    elif not args.json:
        print("(usa --write para anotar la corrida en runs.jsonl)")
    return 0

# ----------------------------------------------------------------------------- surface

INSTRUCTION_RE = re.compile(r"^\s*(?:[-*]\s|\d+\.\s|\*\*(?:C\d+|G\d+))|"
                            r"\b(?:nunca|siempre|debe|obligatorio|no se|jamas)\b", re.I)

def cmd_surface(args):
    """Mide la superficie de instruccion de SKILL.md. Lo unico que se automatiza del
    gobierno de instrucciones es MEDIR: que se borra es juicio humano."""
    # junto al canon si el proyecto la lleva dentro; si no, la del repo (skill/SKILL.md)
    skill = os.path.join(BASE, "SKILL.md")
    if not os.path.exists(skill):
        skill = os.path.join(ROOT, "skill", "SKILL.md")
    targets = [("SKILL.md", skill)]
    per_file, total = {}, 0
    for name, path in targets:
        text = read(path)
        if not text:
            continue
        body = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
        lines = [l for l in body.splitlines() if l.strip()]
        instr = sum(1 for l in lines if INSTRUCTION_RE.search(l))
        words = len(body.split())
        per_file[name] = {"instructions": instr, "lines": len(body.splitlines()),
                          "words": words, "bytes": len(text.encode()), "tokens_aprox": round(words / 0.75)}
        total += instr
    rec = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "project": PROJECT, "total": total, "per_file": per_file}
    if args.json:
        print(json.dumps(rec, ensure_ascii=False, indent=2))
    else:
        print(f"superficie de instruccion · {project_name()}\n")
        for name, v in per_file.items():
            print(f"  {name}: {v['instructions']} instrucciones · {v['words']} palabras · ~{v['tokens_aprox']} tokens")
        hist = read_jsonl(os.path.join(CFG, "instruction-surface.jsonl"))
        if hist:
            prev = hist[-1]
            print(f"\n  anterior ({prev['at'][:10]}): {prev['total']} instrucciones · "
                  f"~{sum(f.get('tokens_aprox',0) for f in prev['per_file'].values())} tokens")
    if args.write:
        append_jsonl(os.path.join(CFG, "instruction-surface.jsonl"), rec)
        print("\nanotado en Context/_skill-config/instruction-surface.jsonl")
    return 0

# -------------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["stats", "contract", "entities", "clients", "dates", "expiry", "supersession", "cruce", "grafo", "vecinos", "normalizar", "contradicciones", "gates", "surface"])
    ap.add_argument("--json", action="store_true", help="salida JSON, para encadenar")
    ap.add_argument("--write", action="store_true", help="escribe; por defecto es dry-run")
    ap.add_argument("--tag", help="etiqueta de la corrida (gates)")
    ap.add_argument("--canal", help="cruce: filtra por familia de canal (WhatsApp, Messenger, Web chat...)")
    ap.add_argument("--problema", help="cruce: filtra por problem_tag o titulo (subcadena)")
    ap.add_argument("--pistas", action="store_true",
                    help="cruce: incluye canales solo mencionados en el cuerpo (pista, no hecho)")
    ap.add_argument("--limite", type=int, default=15, help="cuantos elementos imprimir por grupo")
    ap.add_argument("--nodo", help="vecinos: nodo de partida (ruta, client_id, nombre de cliente, problem_tag)")
    ap.add_argument("--rel", help="vecinos: filtra por verbo(s), separados por coma")
    ap.add_argument("--saltos", type=int, default=1, help="vecinos: profundidad del recorrido")
    ap.add_argument("--debiles", action="store_true", help="vecinos: incluye aristas de weight < 1 (menciones)")
    args = ap.parse_args()
    if not os.path.isdir(CTX):
        print(f"no encuentro {CTX} — ¿CB_PROJECT correcto?", file=sys.stderr)
        return 1
    return {"stats": cmd_stats, "contract": cmd_contract, "entities": cmd_entities, "clients": cmd_clients,
            "dates": cmd_dates, "expiry": cmd_expiry, "supersession": cmd_supersession, "cruce": cmd_cruce, "grafo": cmd_grafo, "vecinos": cmd_vecinos, "normalizar": cmd_normalizar, "contradicciones": cmd_contradicciones, "gates": cmd_gates,
            "surface": cmd_surface}[args.cmd](args)

if __name__ == "__main__":
    sys.exit(main())
