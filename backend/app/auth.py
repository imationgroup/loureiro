"""Autenticación del panel, usuarios del equipo y permisos.

Contraseñas
-----------
NUNCA se guardan en claro ni viajan al repositorio. Se guarda solo el hash,
generado con `scrypt` (librería estándar, sin dependencias añadidas) y con
sal aleatoria.

Formato del hash:  scrypt:<n>:<r>:<p>:<sal_b64>:<hash_b64>

El separador es ":" y NO "$" a propósito. Docker Compose interpola las
variables del .env, así que un "$" dentro del valor se interpreta como
"$NOMBRE_DE_VARIABLE" y desaparece: el hash llegaba al contenedor
truncado y el login era imposible. Base64 nunca usa ":", así que es un
separador seguro.

Usuarios
--------
Los usuarios viven en la tabla `usuarios`. El ADMIN_EMAIL y el
ADMIN_PASSWORD_HASH del .env solo sirven para sembrar el primer
administrador cuando la tabla aún no tiene ninguno (ver sembrar_admin). A
partir de ahí manda la base de datos: el correo se cambia en Equipo y la
contraseña con «He olvidado mi contraseña», no volviendo a tocar el .env.

Permisos
--------
El administrador lo ve todo. Un miembro solo entra en los módulos que tenga
marcados, y dentro de ellos solo ve lo que lleva él: cada cliente, obra,
cita, presupuesto, proforma, factura, coste, ingreso y solicitud tiene un
responsable (columna usuario_id). Almacén, proveedores y profesionales son
de la empresa y los ve entero quien tenga ese módulo.

Los permisos se leen de la base de datos en cada petición, no se guardan en
la sesión: si el administrador quita un módulo o da de baja a alguien, vale
desde la siguiente petición, sin esperar a que caduque nada.
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
    return "scrypt:{}:{}:{}:{}:{}".format(
        n, r, p,
        base64.b64encode(sal).decode(),
        base64.b64encode(dk).decode(),
    )


def verificar_password(password: str, almacenado: str) -> bool:
    try:
        algo, n, r, p, sal_b64, hash_b64 = almacenado.split(":")
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


def hash_valido(h: str) -> bool:
    """Comprueba la forma del hash, no solo que exista.

    Sin esto, un hash truncado (por ejemplo, si Compose se comió parte al
    interpolar) se daría por bueno y el login fallaría sin explicación.
    """
    partes = (h or "").split(":")
    if len(partes) != 6 or partes[0] != "scrypt":
        return False
    try:
        int(partes[1]); int(partes[2]); int(partes[3])
        return len(base64.b64decode(partes[4])) == 16 and len(base64.b64decode(partes[5])) == 32
    except Exception:
        return False


# Hash de una contraseña que nadie conoce. En el login se comprueba contra él
# cuando el correo no existe, para que la respuesta tarde lo mismo exista o no
# el usuario y no se pueda averiguar quién está dado de alta.
HASH_FALSO = crear_hash(secrets.token_urlsafe(24))


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


# ── Permisos ─────────────────────────────────────────────────────────────

# Módulos que el administrador puede dar a un miembro. El Panel (resumen) lo
# tiene todo el mundo, con sus propios números; Equipo, solo el administrador.
MODULOS = ("agenda", "solicitudes", "visitas", "obras", "notas", "clientes", "profesionales",
           "presupuestos", "proformas", "facturas", "costes", "contabilidad",
           "stock", "proveedores")


def permisos_de(texto) -> list[str]:
    """Lista limpia de módulos: descarta lo que no sea un módulo conocido."""
    if isinstance(texto, (list, tuple)):
        partes = texto
    else:
        partes = str(texto or "").split(",")
    vistos = []
    for p in (str(x).strip() for x in partes):
        if p in MODULOS and p not in vistos:
            vistos.append(p)
    return vistos


def es_admin(u: dict) -> bool:
    return u.get("rol") == "admin"


def puede(u: dict, *modulos: str) -> bool:
    """¿Tiene alguno de estos módulos? El administrador, siempre."""
    return es_admin(u) or any(m in u["permisos"] for m in modulos)


def exigir(u: dict, *modulos: str):
    if not puede(u, *modulos):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "No tienes acceso a esta parte del panel.")


def exigir_admin(u: dict):
    if not es_admin(u):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Solo el administrador puede hacer esto.")


def filtro_responsable(u: dict, alias: str = "") -> tuple[str, tuple]:
    """Condición SQL para quedarse con lo que lleva el usuario.

    Al administrador no se le filtra nada. Devuelve el trozo de WHERE y sus
    parámetros, para encadenarlo con AND en cualquier consulta.
    """
    if es_admin(u):
        return "1=1", ()
    pre = f"{alias}." if alias else ""
    return f"{pre}usuario_id = ?", (u["id"],)


REFERENCIAS = (("cliente_id", "clientes", "ese cliente"),
               ("obra_id", "obras", "esa obra"),
               ("presupuesto_id", "presupuestos", "ese presupuesto"),
               ("visita_id", "visitas", "esa visita"))


def comprobar_referencias(u: dict, datos: dict, existente: dict | None = None):
    """Un miembro no puede colgar lo suyo de un cliente u obra de otra persona.

    Si pudiera, lo ajeno se le colaría por los nombres que enseñan los
    listados (el cliente de un presupuesto, la obra de una cita). Solo se
    mira lo que cambia: una ficha que el administrador enlazó con algo de otra
    persona se puede seguir editando sin que salte el aviso.
    """
    if es_admin(u):
        return
    for campo, tabla, que in REFERENCIAS:
        valor = datos.get(campo)
        if not valor or (existente and existente.get(campo) == valor):
            continue
        if not db.escalar(f"SELECT COUNT(*) FROM {tabla} WHERE id = ? AND usuario_id = ?",
                          (valor, u["id"])):
            raise HTTPException(422, f"No puedes usar {que}: lo lleva otra persona del equipo.")


def fijar_responsable(u: dict, entrada: dict, datos: dict, creando: bool):
    """Decide el responsable (usuario_id) de lo que se va a guardar.

    - Un miembro no elige: lo que crea es suyo y no se lo puede pasar a otro.
    - El administrador puede ponerlo o cambiarlo. Si al crear no dice nada,
      lo que hace es suyo: es lo normal, y así lo que se da de alta desde
      fuera del panel no queda sin dueño. Para dejarlo en blanco a propósito
      hay que mandar el responsable vacío, que es lo que hace el desplegable
      con «— nadie —».

    `entrada` es lo que llegó en la petición y `datos` lo que se va a
    escribir, que se modifica aquí.
    """
    datos.pop("usuario_id", None)
    if not es_admin(u):
        if creando:
            datos["usuario_id"] = u["id"]
        return
    if "usuario_id" not in entrada:
        if creando:
            datos["usuario_id"] = u["id"]
        return
    valor = entrada["usuario_id"]
    if valor in (None, ""):
        datos["usuario_id"] = None
        return
    try:
        valor = int(valor)
    except (TypeError, ValueError):
        raise HTTPException(422, "Responsable no válido.")
    if not db.escalar("SELECT COUNT(*) FROM usuarios WHERE id = ?", (valor,)):
        raise HTTPException(422, "Ese responsable no existe.")
    datos["usuario_id"] = valor


# ── Usuarios ─────────────────────────────────────────────────────────────

def _usuario(fila: dict | None) -> dict | None:
    if not fila:
        return None
    u = dict(fila)
    u["permisos"] = permisos_de(u.get("permisos"))
    u["activo"] = bool(u.get("activo"))
    return u


def usuario_por_id(id_) -> dict | None:
    return _usuario(db.fila("SELECT * FROM usuarios WHERE id = ?", (id_,)))


def usuario_por_email(email: str) -> dict | None:
    return _usuario(db.fila("SELECT * FROM usuarios WHERE email = ?",
                            ((email or "").strip().lower(),)))


def publico(u: dict) -> dict:
    """Lo que se puede enseñar de un usuario: nunca el hash ni su enlace."""
    return {
        "id": u["id"], "email": u["email"], "nombre": u.get("nombre") or u["email"],
        "rol": u["rol"], "permisos": list(MODULOS) if es_admin(u) else u["permisos"],
        "profesional_id": u.get("profesional_id"),
    }


def sembrar_admin():
    """Crea el primer administrador con los datos del .env.

    Solo actúa si la tabla no tiene ningún administrador: en los arranques
    siguientes no pisa nada, ni el correo cambiado desde Equipo ni una
    contraseña cambiada desde el panel.
    """
    if db.escalar("SELECT COUNT(*) FROM usuarios WHERE rol = 'admin'"):
        return
    if not (ADMIN_EMAIL and hash_valido(ADMIN_PASSWORD_HASH)):
        log.warning("sin administrador en la base y sin ADMIN_EMAIL/ADMIN_PASSWORD_HASH válidos")
        return
    with db.tx() as con:
        ya = con.execute("SELECT id FROM usuarios WHERE email = ?", (ADMIN_EMAIL,)).fetchone()
        if ya:
            con.execute("""UPDATE usuarios SET rol = 'admin', activo = 1,
                           password_hash = COALESCE(password_hash, ?) WHERE id = ?""",
                        (ADMIN_PASSWORD_HASH, ya[0]))
        else:
            con.execute("""INSERT INTO usuarios (email, nombre, rol, password_hash)
                           VALUES (?, 'Administrador', 'admin', ?)""",
                        (ADMIN_EMAIL, ADMIN_PASSWORD_HASH))
    log.info("administrador sembrado desde el .env: %s", ADMIN_EMAIL)


def configurado() -> bool:
    return bool(db.escalar(
        "SELECT COUNT(*) FROM usuarios WHERE rol = 'admin' AND activo = 1 "
        "AND password_hash IS NOT NULL"))


# ── Sesiones ─────────────────────────────────────────────────────────────

def crear_sesion(u: dict) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    ahora = datetime.now(timezone.utc)
    expira = ahora + timedelta(hours=HORAS_SESION)
    with db.tx() as con:
        con.execute(
            "INSERT INTO sesiones (token, email, usuario_id, creada, expira) VALUES (?,?,?,?,?)",
            (token, u["email"], u["id"], ahora.isoformat(), expira.isoformat()),
        )
        # Mismo formato que datetime('now') de SQLite (UTC, sin zona): es el que
        # entiende el «hace 5 min» del panel.
        con.execute("UPDATE usuarios SET ultimo_acceso = ? WHERE id = ?",
                    (ahora.strftime("%Y-%m-%d %H:%M:%S"), u["id"]))
        # Aprovechamos para barrer las caducadas
        con.execute("DELETE FROM sesiones WHERE expira < ?", (ahora.isoformat(),))
    return token, expira.isoformat()


def cerrar_sesion(token: str):
    with db.tx() as con:
        con.execute("DELETE FROM sesiones WHERE token = ?", (token,))


def cerrar_sesiones_de(u: dict):
    """Echa a alguien de todos los sitios donde tenga la sesión abierta."""
    with db.tx() as con:
        con.execute("DELETE FROM sesiones WHERE usuario_id = ? OR email = ?",
                    (u["id"], u["email"]))


esquema_bearer = HTTPBearer(auto_error=False)


def sesion_actual(cred: HTTPAuthorizationCredentials | None = Depends(esquema_bearer)) -> dict:
    """Dependencia de FastAPI: protege todos los endpoints del panel.

    Devuelve el usuario con sus permisos recién leídos de la base de datos.
    """
    if cred is None or not cred.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión no iniciada")
    s = db.fila("SELECT email, usuario_id, expira FROM sesiones WHERE token = ?",
                (cred.credentials,))
    if not s:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión no válida")
    if datetime.fromisoformat(s["expira"]) < datetime.now(timezone.utc):
        cerrar_sesion(cred.credentials)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión caducada")
    # Las sesiones abiertas antes de que existiera el equipo solo tienen el
    # correo: se buscan por él, así nadie tiene que volver a entrar.
    u = usuario_por_id(s["usuario_id"]) if s["usuario_id"] else usuario_por_email(s["email"])
    if not u or not u["activo"] or not u.get("password_hash"):
        cerrar_sesion(cred.credentials)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión no válida")
    return u


# ── Enlaces para crear o recuperar la contraseña ─────────────────────────

def _huella(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def crear_clave(usuario_id: int, tipo: str, horas: int) -> str:
    """Genera un enlace de un solo uso y anula los anteriores de esa persona."""
    token = secrets.token_urlsafe(32)
    expira = (datetime.now(timezone.utc) + timedelta(hours=horas)).isoformat()
    with db.tx() as con:
        con.execute("DELETE FROM claves WHERE usuario_id = ?", (usuario_id,))
        con.execute("INSERT INTO claves (token_hash, usuario_id, tipo, expira) VALUES (?,?,?,?)",
                    (_huella(token), usuario_id, tipo, expira))
    return token


def leer_clave(token: str) -> dict | None:
    """El enlace si existe y no ha caducado; si no, None."""
    if not token:
        return None
    c = db.fila("SELECT * FROM claves WHERE token_hash = ?", (_huella(token),))
    if not c:
        return None
    if datetime.fromisoformat(c["expira"]) < datetime.now(timezone.utc):
        with db.tx() as con:
            con.execute("DELETE FROM claves WHERE token_hash = ?", (c["token_hash"],))
        return None
    return c
