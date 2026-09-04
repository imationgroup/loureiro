#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera sitemap.xml y robots.txt recorriendo el sitio.

Se hace por barrido en vez de a mano porque una lista escrita a mano se
queda desfasada en cuanto se añade una página, y un sitemap que apunta a
URLs que ya no existen —o que se deja fuera las nuevas— hace más daño
que bien.

Reglas de inclusión:
  - Solo HTML que se sirva como página pública.
  - Fuera las que llevan `noindex` (legales, panel).
  - Fuera las redirecciones que quedaron de mover el blog a categorías.
  - Fuera el panel de gestión entero.

La prioridad no es una promesa a Google, es una señal de importancia
relativa dentro del propio sitio: portada > servicios > blog > artículos.

Uso:
    python scripts/generar-sitemap.py
"""

import io
import os
import re
from datetime import date

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://loureirosoluciones.es"

# Carpetas que no se publican como contenido indexable
EXCLUIDAS = {".git", "admin", "backend", "scripts", ".github", "assets"}

# (patrón de la URL, frecuencia, prioridad)
REGLAS = [
    (r"^/$",                       "monthly", "1.0"),
    (r"^/servicios/[^/]+/$",       "monthly", "0.9"),
    (r"^/blog/$",                  "weekly",  "0.8"),
    (r"^/blog/[^/]+/$",            "weekly",  "0.7"),
    (r"^/blog/[^/]+/[^/]+\.html$", "yearly",  "0.6"),
]


def clasificar(url):
    for patron, freq, prio in REGLAS:
        if re.match(patron, url):
            return freq, prio
    return "monthly", "0.5"


def url_de(ruta_rel):
    ruta = ruta_rel.replace(os.sep, "/")
    if ruta == "index.html":
        return "/"
    if ruta.endswith("/index.html"):
        return "/" + ruta[: -len("index.html")]
    return "/" + ruta


def indexable(ruta_abs, contenido):
    if "Contenido movido" in contenido:      # redirección antigua
        return False
    # noindex en cualquiera de sus formas
    if re.search(r'name=["\']robots["\'][^>]*noindex', contenido, re.I):
        return False
    return True


def recorrer():
    paginas = []
    for base, dirs, ficheros in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in EXCLUIDAS and not d.startswith(".")]
        for f in ficheros:
            if not f.endswith(".html"):
                continue
            abs_ = os.path.join(base, f)
            rel = os.path.relpath(abs_, RAIZ)
            contenido = io.open(abs_, encoding="utf-8").read()
            if not indexable(abs_, contenido):
                continue
            paginas.append(url_de(rel))
    return sorted(set(paginas), key=lambda u: (u.count("/"), u))


def escribir_sitemap(urls, hoy):
    partes = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        freq, prio = clasificar(u)
        partes += ["  <url>",
                   f"    <loc>{BASE}{u}</loc>",
                   f"    <lastmod>{hoy}</lastmod>",
                   f"    <changefreq>{freq}</changefreq>",
                   f"    <priority>{prio}</priority>",
                   "  </url>"]
    partes.append("</urlset>")
    io.open(os.path.join(RAIZ, "sitemap.xml"), "w", encoding="utf-8",
            newline="\n").write("\n".join(partes) + "\n")


ROBOTS = f"""# robots.txt de loureirosoluciones.es
# Generado por scripts/generar-sitemap.py

User-agent: *
Allow: /

# Panel de gestión: nada que indexar y datos de clientes detrás
Disallow: /admin/

# Las páginas legales y las URLs antiguas del blog NO se bloquean aquí a
# propósito: ya llevan noindex en el propio HTML. Si se bloqueasen,
# Google no podría entrar a leer ese noindex y podría acabar indexando
# la URL igualmente. Con noindex basta, y hace falta poder rastrearlas
# para que surta efecto.
#
# Tampoco se pone "Disallow: /blog/*.html$" para las URLs antiguas: en
# robots.txt el comodín abarca también las barras, así que esa regla se
# tragaría TODOS los artículos, que viven en /blog/<categoria>/<x>.html.

# El buscador de imágenes sí puede ver las fotos de obra
User-agent: Googlebot-Image
Allow: /assets/img/

Sitemap: {BASE}/sitemap.xml
"""


def main():
    hoy = date.today().isoformat()
    urls = recorrer()
    escribir_sitemap(urls, hoy)
    io.open(os.path.join(RAIZ, "robots.txt"), "w", encoding="utf-8",
            newline="\n").write(ROBOTS)

    print(f"sitemap.xml: {len(urls)} URLs")
    for u in urls:
        freq, prio = clasificar(u)
        print(f"  {prio}  {u}")
    print("robots.txt actualizado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
