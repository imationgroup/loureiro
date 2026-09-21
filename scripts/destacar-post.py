#!/usr/bin/env python3
"""Relanza un post del blog como novedad del Perfil de Empresa de Google.

Las novedades de Google envejecen y dejan de verse, así que de vez en cuando
interesa volver a publicar un artículo que ya está en el blog. Esto lo apunta
en blog/novedades.json y regenera el feed: el post sale con la fecha de hoy y
con otro identificador, así que el conector (Make) lo trata como algo nuevo y
lo publica.

    python scripts/destacar-post.py blog/electricidad/placas-solares-revision-e-instalacion.html
    python scripts/destacar-post.py placas          # basta con un trozo del nombre
    python scripts/destacar-post.py --lista         # qué se ha relanzado y cuándo

Después hay que commitear el cambio y desplegar, como cualquier otra cosa.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTACADOS = RAIZ / "blog" / "novedades.json"


def candidatos(texto: str) -> list[Path]:
    posts = [r for r in (RAIZ / "blog").rglob("*.html") if r.name != "index.html"]
    exacto = [r for r in posts if r.as_posix().endswith(texto.replace("\\", "/").lstrip("/"))]
    return exacto or [r for r in posts if texto.lower() in r.stem.lower()]


def url_de(ruta: Path) -> str:
    texto = ruta.read_text(encoding="utf-8")
    m = re.search(r'<meta\s+property="og:url"\s+content="([^"]*)"', texto)
    return m.group(1) if m else "https://loureirosoluciones.es/" + ruta.relative_to(RAIZ).as_posix()


def leer() -> dict:
    if DESTACADOS.exists():
        return json.loads(DESTACADOS.read_text(encoding="utf-8"))
    return {"destacados": {}}


def main():
    p = argparse.ArgumentParser(description="Relanza un post como novedad en Google.")
    p.add_argument("post", nargs="?", help="ruta del post o un trozo de su nombre")
    p.add_argument("--lista", action="store_true", help="enseña lo relanzado y cuándo")
    args = p.parse_args()
    datos = leer()

    if args.lista or not args.post:
        if not datos["destacados"]:
            print("Todavía no se ha relanzado ningún post.")
        for url, cuando in sorted(datos["destacados"].items(), key=lambda x: x[1], reverse=True):
            print(f"{cuando[:16].replace('T', ' ')}  {url}")
        return

    encontrados = candidatos(args.post)
    if not encontrados:
        raise SystemExit(f"No hay ningún post que encaje con «{args.post}».")
    if len(encontrados) > 1:
        print("Hay varios que encajan; afina un poco más:", file=sys.stderr)
        for r in encontrados:
            print("   " + r.relative_to(RAIZ).as_posix(), file=sys.stderr)
        raise SystemExit(1)

    ruta = encontrados[0]
    url = url_de(ruta)
    datos["destacados"][url] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    DESTACADOS.parent.mkdir(parents=True, exist_ok=True)
    DESTACADOS.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Relanzado: " + url)

    subprocess.run([sys.executable, str(RAIZ / "scripts" / "generar-feed.py")], check=False)
    print("Ya está el primero del feed. Commitea y despliega, y el conector lo publicará.")


if __name__ == "__main__":
    main()
