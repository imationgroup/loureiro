"""Autenticación del panel.

La contraseña NUNCA se guarda en claro ni viaja al repositorio. En el
`.env` del VPS va solo el hash, generado con `scrypt` (librería estándar,
sin dependencias añadidas) y con sal aleatoria por instalación.

Formato de ADMIN_PASSWORD_HASH:  scrypt$<n>$<r>$<p>$<sal_b64>$<hash_b64>

Para generarlo:  python scripts/set-admin-password.py
"""

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import db

log = logging.getLogger("loureiro-admin")

ADMIN_EMAIL = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
ADMIN_PASSWORD_HASH = (os.getenv("ADMIN_PASSWORD_HASH") or "").strip()
HORAS_SESION = int(os.getenv("SESSION_HOURS", "12"))

# ── Hash de contraseña ───────────────────────────────────────────────────

def crear_hash(password: str, n: int = 2**14, r: int = 8, p: int = 1) -> str:
    sal = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=sal, n=n, r=r, p=p, dklen=32)
    return "scrypt${}${}${}${}${}".format(
        n, r, p,
        base64.b64encode(sal).decode(),
        base64.b64encode(dk).decode(),
    )


def verificar_password(password: str, almacenado: str) -> bool:
    try:
        algo, n, r, p, sal_b64, hash_b64 = almacenado.split("$")
        if algo != "scrypt":
            return False
        dk = hashlib.scrypt(
            password.encode(),
            salt=base64.b64decode(sal_b64),
            n=int(n), r=int(r), p=int(p), dklen=32,
        )
        # Comparación en tiempo constante: no filtra cuántos bytes acertó.
        return hmac.compare_digest(dk, base64.b64decode(hash_b64))
    except Exception:
        return False


# ── Freno a la fuerza bruta ──────────────────────────────────────────────
_INTENTOS: dict[str, list[float]] = {}
_VENTANA = 15 * 60      # 15 minutos
_MAX_INTENTOS = 8


def registrar_intento(ip: str) -> bool:
    """False si esa IP ya ha gastado sus intentos."""
    ahora = time.time()
    cubo = _INTENTOS.setdefault(ip, [])
    cubo[:] = [t for t in cubo if t > ahora - _VENTANA]
    if len(cubo) >= _MAX_INTENTOS:
        return False
    cubo.append(ahora)
    return True


def limpiar_intentos(ip: str):
    _INTENTOS.pop(ip, None)


# ── Sesiones ─────────────────────────────────────────────────────────────

def crear_sesion(email: str) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    ahora = datetime.now(timezone.utc)
    expira = ahora + timedelta(hours=HORAS_SESION)
    with db.tx() as con:
        con.execute(
            "INSERT INTO sesiones (token, email, creada, expira) VALUES (?,?,?,?)",
            (token, email, ahora.isoformat(), expira.isoformat()),
        )
        # Aprovechamos para barrer las caducadas
        con.execute("DELETE FROM sesiones WHERE expira < ?", (ahora.isoformat(),))
    return token, expira.isoformat()


def cerrar_sesion(token: str):
    with db.tx() as con:
        con.execute("DELETE FROM sesiones WHERE token = ?", (token,))


esquema_bearer = HTTPBearer(auto_error=False)


def sesion_actual(cred: HTTPAuthorizationCredentials | None = Depends(esquema_bearer)) -> str:
    """Dependencia de FastAPI: protege todos los endpoints del panel."""
    if cred is None or not cred.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión no iniciada")
    s = db.fila("SELECT email, expira FROM sesiones WHERE token = ?", (cred.credentials,))
    if not s:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión no válida")
    if datetime.fromisoformat(s["expira"]) < datetime.now(timezone.utc):
        cerrar_sesion(cred.credentials)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión caducada")
    return s["email"]


def configurado() -> bool:
    return bool(ADMIN_EMAIL and ADMIN_PASSWORD_HASH)
