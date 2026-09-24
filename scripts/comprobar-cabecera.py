"""Comprueba que todas las páginas llevan la misma cabecera.

La cabecera se repite escrita en cada página, que es lo que permite que el
sitio no necesite ni build ni plantillas. El precio de eso es que, al añadir
una sección nueva, es fácil dejarse una página por el camino: pasó al meter
Ofertas, y la página de ofertas se quedó sin el enlace de Preguntas.

Esto lo caza antes de subirlo. Se mira lo que el visitante ve —los enlaces
del menú y en qué orden—, no el HTML letra a letra: el destino del botón de
presupuesto cambia a propósito según la página (ancla propia si esa página
tiene formulario, y a la portada si no lo tiene).

    python scripts/comprobar-cabecera.py

Devuelve 1 si alguna página se sale del patrón, para poder encadenarlo.
"""

import glob
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# El panel y la página de firma tienen cabecera propia a propósito.
FUERA = ("admin", "firmar")

MENU = re.compile(r'<nav class="nav".*?</nav>', re.S)
ENLACE = re.compile(r'<a\b[^>]*>(.*?)</a>', re.S)
ETIQUETAS = re.compile(r"<[^>]+>")


def paginas():
    for patron in ("*.html", "*/*.html", "*/*/*.html"):
        for ruta in glob.glob(os.path.join(RAIZ, patron)):
            rel = os.path.relpath(ruta, RAIZ).replace("\\", "/")
            if not rel.startswith(FUERA):
                yield rel


def enlaces_del_menu(texto):
    menu = MENU.search(texto)
    if not menu:
        return None
    return [" ".join(ETIQUETAS.sub("", e).split()) for e in ENLACE.findall(menu.group(0))]


def main():
    encontrados = {}
    sin_menu = []
    for rel in sorted(paginas()):
        with open(os.path.join(RAIZ, rel), encoding="utf-8") as f:
            enlaces = enlaces_del_menu(f.read())
        if enlaces is None:
            sin_menu.append(rel)
            continue
        encontrados.setdefault(tuple(enlaces), []).append(rel)

    if not encontrados:
        print("No hay ninguna página con cabecera.")
        return 1

    # La buena es la que más se repite; las demás son las que se quedaron atrás.
    patron, suyas = max(encontrados.items(), key=lambda par: len(par[1]))
    print("Cabecera esperada (%d páginas):" % len(suyas))
    print("  " + " · ".join(patron))

    problemas = False
    for otros, paginas_raras in encontrados.items():
        if otros == patron:
            continue
        problemas = True
        faltan = [e for e in patron if e not in otros]
        sobran = [e for e in otros if e not in patron]
        print("\nSe salen del patrón:")
        for p in paginas_raras:
            print("  - " + p)
        if faltan:
            print("    falta: " + ", ".join(faltan))
        if sobran:
            print("    sobra: " + ", ".join(sobran))
        if not faltan and not sobran:
            print("    mismos enlaces, distinto orden")

    if sin_menu:
        print("\nSin cabecera (revisa si es a propósito):")
        for p in sin_menu:
            print("  - " + p)

    if not problemas:
        print("\nTodas iguales.")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
