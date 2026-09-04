#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fija la contraseña del panel en el .env del VPS.

La contraseña NO se escribe nunca en claro, ni aquí ni en el repositorio,
que además es público. Este script la pide por teclado sin mostrarla,
calcula el hash con scrypt y escribe en el .env únicamente ese hash.

Uso, en el VPS:

    cd /home/deploy/apps/loureiro
    python3 scripts/set-admin-password.py

Después:

    docker compose up -d --force-recreate
"""

import base64
import getpass
import hashlib
import io
import os
import re
import secrets
import sys

ENV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


def crear_hash(password: str) -> str:
    n, r, p = 2**14, 8, 1
    sal = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=sal, n=n, r=r, p=p, dklen=32)
    # Separador ":" y no "$": Docker Compose interpola el .env y un "$"
    # dentro del valor se lo come, dejando el hash truncado.
    return f"scrypt:{n}:{r}:{p}:{base64.b64encode(sal).decode()}:{base64.b64encode(dk).decode()}"


def poner(contenido: str, clave: str, valor: str) -> str:
    linea = f"{clave}={valor}"
    if re.search(rf"^{clave}=", contenido, re.M):
        return re.sub(rf"^{clave}=.*$", linea, contenido, flags=re.M)
    sep = "" if contenido.endswith("\n") or not contenido else "\n"
    return contenido + sep + linea + "\n"


def main() -> int:
    if not os.path.exists(ENV):
        print(f"No encuentro {ENV}. ¿Estás en el directorio del proyecto?", file=sys.stderr)
        return 1

    email = input("Email del panel [contacto@loureirosoluciones.es]: ").strip()
    email = email or "contacto@loureirosoluciones.es"

    p1 = getpass.getpass("Contraseña (no se muestra): ")
    if len(p1) < 8:
        print("Demasiado corta: usa 8 caracteres como mínimo.", file=sys.stderr)
        return 1
    p2 = getpass.getpass("Repítela: ")
    if p1 != p2:
        print("No coinciden.", file=sys.stderr)
        return 1

    contenido = io.open(ENV, encoding="utf-8").read()
    contenido = poner(contenido, "ADMIN_EMAIL", email)
    contenido = poner(contenido, "ADMIN_PASSWORD_HASH", crear_hash(p1))
    io.open(ENV, "w", encoding="utf-8", newline="\n").write(contenido)
    os.chmod(ENV, 0o600)

    print("\nListo. En el .env queda solo el hash, nunca la contraseña.")
    print("Aplica el cambio con:")
    print("  docker compose up -d --force-recreate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
