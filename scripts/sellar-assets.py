#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pone un ?v=<hash> a cada CSS y JS referenciado en el HTML.

Por qué hace falta
------------------
Nginx sirve los assets con `Cache-Control: immutable, max-age=2592000`.
Con `immutable` el navegador NO revalida: si el nombre del fichero no
cambia, se queda con su copia vieja hasta 30 días aunque el servidor ya
tenga otra. Resultado: publicas un cambio de CSS y los visitantes que ya
habían entrado siguen viendo el diseño antiguo.

La solución no es quitar la caché —que es buena— sino que la URL cambie
cuando cambia el contenido. El hash se calcula del propio fichero, así
que solo cambia si el asset cambió de verdad.

Uso
---
    python scripts/sellar-assets.py

Hay que ejecutarlo **después de tocar cualquier CSS o JS y antes de
commitear**. Si se olvida, no se rompe nada: simplemente los visitantes
antiguos tardarán en ver el cambio.
"""
import hashlib
import io
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATRON = re.compile(r'(?P<attr>href|src)="(?P<ruta>/assets/(?:css|js)/[^"?]+\.(?:css|js))(?:\?v=[^"]*)?"')


def hash_de(ruta_rel):
    absoluta = os.path.join(RAIZ, ruta_rel.lstrip("/").replace("/", os.sep))
    if not os.path.exists(absoluta):
        return None
    with open(absoluta, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()[:8]


def main():
    os.chdir(RAIZ)
    htmls = []
    for base, _, ficheros in os.walk("."):
        if ".git" in base:
            continue
        for f in ficheros:
            if f.endswith(".html"):
                htmls.append(os.path.join(base, f))

    cache_hash = {}
    tocados = 0
    faltan = set()

    for p in sorted(htmls):
        s = io.open(p, encoding="utf-8").read()
        original = s

        def sustituir(m):
            ruta = m.group("ruta")
            if ruta not in cache_hash:
                cache_hash[ruta] = hash_de(ruta)
            h = cache_hash[ruta]
            if h is None:
                faltan.add(ruta)
                return m.group(0)
            return f'{m.group("attr")}="{ruta}?v={h}"'

        s = PATRON.sub(sustituir, s)
        if s != original:
            io.open(p, "w", encoding="utf-8", newline="\n").write(s)
            tocados += 1

    for ruta, h in sorted(cache_hash.items()):
        print(f"  {ruta}  ->  ?v={h}")
    print(f"\nHTML actualizados: {tocados} de {len(htmls)}")

    if faltan:
        print("\nAVISO, estos assets se referencian pero no existen:", file=sys.stderr)
        for r in sorted(faltan):
            print("  " + r, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
