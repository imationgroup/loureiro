#!/usr/bin/env python3
"""Genera feed.xml con los posts del blog.

El RSS es lo que hace que otros sistemas se enteren de que hay post nuevo sin
que nadie les avise. Hoy lo usa Make para publicar la novedad en el Perfil de
Empresa de Google, pero vale igual para cualquier otro conector, para un lector
de feeds o para mandarlo a una newsletter.

Se ejecuta en cada despliegue (ver scripts/deploy.sh), así que el feed siempre
va al día aunque nadie se acuerde de regenerarlo. Solo librería estándar.

La fecha de cada post sale de su primer commit, siguiendo los cambios de
carpeta: si no se siguieran, todos los artículos que se movieron a carpetas por
categoría tendrían la fecha de la mudanza y el feed saldría desordenado.

Además, `scripts/destacar-post.py` permite empujar un post ya publicado para
que el conector lo vuelva a publicar como novedad: se apunta en
blog/novedades.json y aquí sale con fecha e identificador nuevos.
"""

import html
import json
import re
import subprocess
from email.utils import format_datetime
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
WEB = "https://loureirosoluciones.es"
SALIDA = RAIZ / "feed.xml"
DESTACADOS = RAIZ / "blog" / "novedades.json"
TITULO = "Blog de Loureiro Soluciones"
# Foto de reserva: un item sin imagen no lo puede publicar un conector.
IMAGEN_POR_DEFECTO = WEB + "/assets/img/og-image.jpg"
DESCRIPCION = ("Reformas, electricidad, albañilería, aire acondicionado y mantenimiento "
               "en Ourense y provincia.")


def _meta(texto: str, atributo: str, valor: str) -> str:
    m = re.search(rf'<meta\s+{atributo}="{re.escape(valor)}"\s+content="([^"]*)"', texto)
    return html.unescape(m.group(1)).strip() if m else ""


def es_redireccion(texto: str) -> bool:
    """Las páginas que solo redirigen a otra no son posts.

    Quedaron de cuando los artículos se movieron a carpetas por categoría: no
    tienen texto ni foto, y un conector no puede publicar con ellas.
    """
    redirige = re.search(r'<meta\s+http-equiv="refresh"', texto, re.I)
    oculta = re.search(r'<meta\s+name="robots"\s+content="[^"]*noindex', texto, re.I)
    return bool(redirige or oculta)


def primer_parrafo(texto: str) -> str:
    """El primer párrafo del artículo, por si el post no trae descripción."""
    cuerpo = re.search(r"<article[^>]*>(.*?)</article>", texto, re.S)
    for p in re.findall(r"<p[^>]*>(.*?)</p>", (cuerpo.group(1) if cuerpo else texto), re.S):
        limpio = html.unescape(re.sub(r"<[^>]+>", "", p)).strip()
        limpio = re.sub(r"\s+", " ", limpio)
        if len(limpio) > 40:
            return limpio[:297] + "…" if len(limpio) > 300 else limpio
    return ""


def _fecha(ruta: Path) -> datetime:
    """Cuándo se publicó de verdad: su commit más antiguo, o la fecha del fichero.

    Con --follow la historia atraviesa los cambios de carpeta, así que la
    última línea del log es la creación del artículo y no la mudanza a su
    categoría.
    """
    try:
        salida = subprocess.run(
            ["git", "log", "--follow", "--format=%cI", "--",
             str(ruta.relative_to(RAIZ).as_posix())],
            cwd=RAIZ, capture_output=True, text=True, timeout=30)
        lineas = [l.strip() for l in salida.stdout.splitlines() if l.strip()]
        if salida.returncode == 0 and lineas:
            return datetime.fromisoformat(lineas[-1])
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return datetime.fromtimestamp(ruta.stat().st_mtime, timezone.utc)


def destacados() -> dict:
    """Posts que se han vuelto a lanzar a mano, con la fecha en que se lanzaron."""
    if not DESTACADOS.exists():
        return {}
    try:
        return json.loads(DESTACADOS.read_text(encoding="utf-8")).get("destacados", {})
    except (ValueError, OSError):
        return {}


def posts() -> list[dict]:
    lanzados = destacados()
    encontrados = []
    for ruta in (RAIZ / "blog").rglob("*.html"):
        if ruta.name == "index.html":
            continue
        texto = ruta.read_text(encoding="utf-8")
        if es_redireccion(texto):
            continue
        url = _meta(texto, "property", "og:url") or WEB + "/" + ruta.relative_to(RAIZ).as_posix()
        titulo = _meta(texto, "property", "og:title")
        if not titulo:
            m = re.search(r"<title>(.*?)</title>", texto, re.S)
            titulo = html.unescape(m.group(1)).split("|")[0].strip() if m else ruta.stem
        categoria = ruta.parent.name.replace("-", " ") if ruta.parent.name != "blog" else ""
        encontrados.append({
            "url": url,
            "titulo": titulo,
            # Descripción e imagen nunca vacías: un item a medias hace fallar
            # al conector que publica la novedad.
            "descripcion": (_meta(texto, "property", "og:description")
                            or _meta(texto, "name", "description")
                            or primer_parrafo(texto)
                            or titulo),
            "imagen": _meta(texto, "property", "og:image") or IMAGEN_POR_DEFECTO,
            "categoria": categoria.capitalize(),
            "fecha": _fecha(ruta),
        })
        # Un post relanzado a mano sale con la fecha del relanzamiento y con
        # otro identificador, para que el conector lo vea como algo nuevo.
        relanzado = lanzados.get(encontrados[-1]["url"])
        if relanzado:
            try:
                cuando = datetime.fromisoformat(relanzado)
            except ValueError:
                cuando = None
            if cuando and cuando > encontrados[-1]["fecha"]:
                encontrados[-1]["fecha"] = cuando
                encontrados[-1]["relanzado"] = cuando
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
            (f"      <guid isPermaLink=\"false\">{xml(p['url'])}#novedad-"
             f"{p['relanzado'].strftime('%Y%m%d%H%M')}</guid>" if p.get("relanzado") else
             f"      <guid isPermaLink=\"true\">{xml(p['url'])}</guid>"),
            f"      <pubDate>{format_datetime(p['fecha'])}</pubDate>",
            f"      <description>{xml(p['descripcion'])}</description>",
        ]
        if p["categoria"]:
            piezas.append(f"      <category>{xml(p['categoria'])}</category>")
        # enclosure es lo que leen los conectores para coger la foto.
        tipo = "image/png" if p["imagen"].lower().endswith(".png") else "image/jpeg"
        piezas.append(f'      <enclosure url="{xml(p["imagen"])}" type="{tipo}" length="0"/>')
        piezas.append("    </item>")
    piezas += ["  </channel>", "</rss>", ""]
    SALIDA.write_text("\n".join(piezas), encoding="utf-8")
    print(f"feed.xml con {len(lista)} posts")


if __name__ == "__main__":
    main()
