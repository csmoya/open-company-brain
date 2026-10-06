#!/usr/bin/env python3
"""Comprueba que nada de un despliegue privado se cuela en este repo publico.

Por que existe: este motor se desarrolla a la vez que un canon privado real. El canon real
tiene nombres de clientes en titulos, alias y ejemplos, y copiar un cambio de alli aqui es
exactamente como se filtran. Un `grep` a ojo no escala; esto si.

Dos capas:
  1. Patrones genericos, versionados aqui (emails, dominios internos, el nombre del
     empleador si lo pones en OCB_EXTRA_PATTERNS). Corren tambien en CI.
  2. Una denylist privada, un nombre por linea, que NUNCA se commitea: publicarla seria la
     fuga. Se busca en $OCB_DENYLIST o en ~/.config/open-company-brain/denylist.txt. Si no
     existe (CI), esta capa se salta y lo dice.

Coincidencia por palabra completa, sin acentos ni mayusculas. `.leakignore` (una ruta o
un `ruta:termino` por linea) silencia falsos positivos revisados a mano.

Uso: python3 tools/leak_check.py [--staged]      # --staged: solo lo que vas a commitear
Sale con 1 si encuentra algo.
"""
import os, re, subprocess, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT_EXT = {".md", ".py", ".json", ".jsonl", ".txt", ".yml", ".yaml", ".toml", ".cfg", ""}

GENERIC = [
    (r"[\w.+-]+@(?!example\.(com|org)\b)[\w-]+\.[\w.]+", "email que no es de example.com"),
    (r"\b(api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}", "posible credencial"),
    (r"\bProjects/Active/", "ruta de un vault personal"),
]


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def files(staged):
    if staged:
        out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                             cwd=ROOT, capture_output=True, text=True).stdout
    else:
        out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                             cwd=ROOT, capture_output=True, text=True).stdout
    for rel in sorted(set(out.split())):
        if os.path.splitext(rel)[1] in TEXT_EXT and os.path.isfile(os.path.join(ROOT, rel)):
            yield rel


def denylist():
    path = os.environ.get("OCB_DENYLIST") or os.path.expanduser("~/.config/open-company-brain/denylist.txt")
    if not os.path.exists(path):
        return None, path
    terms = set()
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        core = re.sub(r"\s*\(.*?\)", "", line).split(" — ")[0].strip()
        for t in {line, core}:
            if len(t) >= 4:
                terms.add(norm(t))
    return sorted(terms), path


def ignores():
    path = os.path.join(ROOT, ".leakignore")
    rules = set()
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.split("#", 1)[0].strip()
            if line:
                rules.add(norm(line))
    return rules


def main():
    staged = "--staged" in sys.argv
    extra = [p for p in os.environ.get("OCB_EXTRA_PATTERNS", "").split(",") if p.strip()]
    patterns = GENERIC + [(r"\b" + re.escape(p.strip()) + r"\b", "patron extra") for p in extra]
    terms, dl_path = denylist()
    skip = ignores()
    hits = []
    for rel in files(staged):
        if rel == ".leakignore" or norm(rel) in skip:
            continue
        text = open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read()
        low = norm(text)
        for pat, why in patterns:
            for m in re.finditer(pat, text, flags=re.I):
                line = text.count("\n", 0, m.start()) + 1
                hits.append((rel, line, m.group(0), why))
        for t in terms or []:
            if f"{norm(rel)}:{t}" in skip:
                continue
            for m in re.finditer(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", low):
                line = low.count("\n", 0, m.start()) + 1
                hits.append((rel, line, t, "denylist"))
    if terms is None:
        print(f"denylist privada no encontrada ({dl_path}): solo patrones genericos", file=sys.stderr)
    for rel, line, what, why in hits:
        print(f"{rel}:{line}: {what!r} ({why})")
    n = len(terms or [])
    print(f"\nleak_check: {len(hits)} hallazgo(s) · denylist de {n} terminos", file=sys.stderr)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
