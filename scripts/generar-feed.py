#!/usr/bin/env python3
"""Genera feed.xml con los posts del blog.

El RSS es lo que hace que otros sistemas se enteren de que hay post nuevo sin
que nadie les avise. Hoy lo usa Make para publicar la novedad en el Perfil de
Empresa de Google, pero vale igual para cualquier otro conector, para un lector
de feeds o para mandarlo a una newsletter.

Se ejecuta en cada despliegue (ver scripts/deploy.sh), así que el feed siempre
va al día aunque nadie se acuerde de regenerarlo. Solo librería estándar.

La fecha de cada post sale de su primer commit, que es cuando se publicó de
verdad; si el repo no está a mano, del propio fichero.
"""

import html
import re
import subprocess
from email.utils import format_datetime
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
WEB = "https://loureirosoluciones.es"
SALIDA = RAIZ / "feed.xml"
TITULO = "Blog de Loureiro Soluciones"
DESCRIPCION = ("Reformas, electricidad, albañilería, aire acondicionado y mantenimiento "
               "en Ourense y provincia.")


def _meta(texto: str, atributo: str, valor: str) -> str:
    m = re.search(rf'<meta\s+{atributo}="{re.escape(valor)}"\s+content="([^"]*)"', texto)
    return html.unescape(m.group(1)).strip() if m else ""


def _fecha(ruta: Path) -> datetime:
    """Cuándo se publicó: el primer commit del fichero, o su fecha en disco."""
    try:
        salida = subprocess.run(
            ["git", "log", "--diff-filter=A", "--follow", "--format=%cI", "-1", "--",
             str(ruta.relative_to(RAIZ).as_posix())],
            cwd=RAIZ, capture_output=True, text=True, timeout=20)
        if salida.returncode == 0 and salida.stdout.strip():
            return datetime.fromisoformat(salida.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return datetime.fromtimestamp(ruta.stat().st_mtime, timezone.utc)


def posts() -> list[dict]:
    encontrados = []
    for ruta in (RAIZ / "blog").rglob("*.html"):
        if ruta.name == "index.html":
            continue
        texto = ruta.read_text(encoding="utf-8")
        url = _meta(texto, "property", "og:url") or WEB + "/" + ruta.relative_to(RAIZ).as_posix()
        titulo = _meta(texto, "property", "og:title")
        if not titulo:
            m = re.search(r"<title>(.*?)</title>", texto, re.S)
            titulo = html.unescape(m.group(1)).split("|")[0].strip() if m else ruta.stem
        categoria = ruta.parent.name.replace("-", " ") if ruta.parent.name != "blog" else ""
        encontrados.append({
            "url": url,
            "titulo": titulo,
            "descripcion": (_meta(texto, "property", "og:description")
                            or _meta(texto, "name", "description")),
            "imagen": _meta(texto, "property", "og:image"),
            "categoria": categoria.capitalize(),
            "fecha": _fecha(ruta),
        })
    encontrados.sort(key=lambda p: p["fecha"], reverse=True)
    return encontrados


def xml(t: str) -> str:
    return html.escape(t or "", quote=True)


def main():
    lista = posts()
    ahora = format_datetime(datetime.now(timezone.utc))
    piezas = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
              "  <channel>",
              f"    <title>{xml(TITULO)}</title>",
              f"    <link>{WEB}/blog/</link>",
              f"    <description>{xml(DESCRIPCION)}</description>",
              "    <language>es-ES</language>",
              f"    <lastBuildDate>{ahora}</lastBuildDate>",
              f'    <atom:link href="{WEB}/feed.xml" rel="self" type="application/rss+xml"/>']
    for p in lista:
        piezas += [
            "    <item>",
            f"      <title>{xml(p['titulo'])}</title>",
            f"      <link>{xml(p['url'])}</link>",
            f"      <guid isPermaLink=\"true\">{xml(p['url'])}</guid>",
            f"      <pubDate>{format_datetime(p['fecha'])}</pubDate>",
            f"      <description>{xml(p['descripcion'])}</description>",
        ]
        if p["categoria"]:
            piezas.append(f"      <category>{xml(p['categoria'])}</category>")
        if p["imagen"]:
            # enclosure es lo que leen los conectores para coger la foto.
            piezas.append(f'      <enclosure url="{xml(p["imagen"])}" type="image/jpeg" length="0"/>')
        piezas.append("    </item>")
    piezas += ["  </channel>", "</rss>", ""]
    SALIDA.write_text("\n".join(piezas), encoding="utf-8")
    print(f"feed.xml con {len(lista)} posts")


if __name__ == "__main__":
    main()
