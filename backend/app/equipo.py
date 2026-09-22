"""Equipo: las personas que entran al panel y a qué puede entrar cada una.

- El administrador da de alta a alguien con su correo y los módulos que puede
  usar. Le llega un correo con un enlace para crear su propia contraseña: el
  administrador no la conoce nunca.
- Cualquiera puede pedir un enlace para cambiar la contraseña si la olvida.
  La respuesta es siempre la misma, exista o no el correo, para que el
  formulario no sirva para averiguar quién tiene cuenta.

Los enlaces van en el fragmento de la URL (…/admin/#clave=…) y no en la ruta
ni en la query: el fragmento no llega al servidor web, así que no se queda
apuntado en los registros de acceso de nginx.
"""

import logging
import os
from html import escape

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from . import db
from .auth import (MODULOS, cerrar_sesiones_de, crear_clave, crear_hash, crear_sesion,
                   exigir_admin, leer_clave, permisos_de, publico, registrar_intento,
                   sesion_actual, usuario_por_email, usuario_por_id)

log = logging.getLogger("loureiro-equipo")

router = APIRouter(prefix="/api/admin", tags=["equipo"])

PANEL = (os.getenv("PANEL_PUBLICO") or "https://loureirosoluciones.es/admin/").rstrip("/") + "/"
MIN_PASSWORD = 10
HORAS_INVITACION = 7 * 24
HORAS_RECUPERAR = 2


def _ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "desconocida"


# ── Quién soy ────────────────────────────────────────────────────────────

@router.get("/yo")
def yo(u: dict = Depends(sesion_actual)):
    """El usuario de la sesión y sus permisos: el panel pinta el menú con esto."""
    return publico(u)


# ── Correos ──────────────────────────────────────────────────────────────

def _correo(para: str, asunto: str, saludo: str, parrafos: list[str],
            boton: str, enlace: str, pie: str) -> bool:
    # Import tardío: main.py importa este módulo para registrar sus rutas, y
    # importarlo arriba sería una importación circular.
    from .main import send_email

    texto = saludo + "\n\n" + "\n\n".join(parrafos) + f"\n\n{boton}:\n{enlace}\n\n{pie}\n\nLoureiro Soluciones\n"
    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(asunto)}</title></head><body style="margin:0;padding:0;background:#F4F5F7">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F4F5F7;padding:24px 12px"><tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#FFFFFF;border-radius:12px;overflow:hidden;font-family:Arial,Helvetica,sans-serif;color:#22252B">
  <tr><td style="background:#14161A;padding:20px 28px"><span style="font-size:19px;font-weight:bold;color:#FFFFFF">Loureiro</span><span style="font-size:19px;color:#9AA0AA">soluciones</span></td></tr>
  <tr><td style="padding:28px">
    <p style="margin:0 0 14px;font-size:20px;font-weight:bold;color:#14161A">{escape(saludo)}</p>
    {"".join(f'<p style="margin:0 0 14px;font-size:15px;line-height:1.6">{escape(p)}</p>' for p in parrafos)}
    <p style="margin:24px 0"><a href="{escape(enlace)}" style="display:inline-block;background:#F97316;color:#FFFFFF;font-weight:bold;font-size:15px;text-decoration:none;padding:13px 24px;border-radius:999px">{escape(boton)}</a></p>
    <p style="margin:0;font-size:13px;line-height:1.6;color:#6C7079">{escape(pie)}</p>
  </td></tr>
</table></td></tr></table></body></html>"""
    return send_email(to=para, subject=asunto, body=texto, html=html,
                      cabeceras={"Auto-Submitted": "auto-generated"})


def _invitar(m: dict) -> dict:
    token = crear_clave(m["id"], "invitacion", HORAS_INVITACION)
    enlace = f"{PANEL}#clave={token}"
    nombre = m.get("nombre") or ""
    enviado = _correo(
        m["email"], "Tu acceso al panel de Loureiro Soluciones",
        f"Hola{(' ' + nombre) if nombre else ''},",
        ["Te han dado acceso al panel de gestión de Loureiro Soluciones.",
         f"Tu usuario es este correo: {m['email']}. Solo falta que crees tu contraseña."],
        "Crear mi contraseña", enlace,
        "El enlace sirve una sola vez y caduca en 7 días. Si no esperabas este correo, ignóralo.")
    # Si el correo no sale, el enlace se le devuelve al administrador para que
    # se lo pase por otra vía: la cuenta no puede quedarse sin forma de activarse.
    return {"enviado": enviado, "enlace": None if enviado else enlace}


# ── Gestión del equipo (solo administrador) ─────────────────────────────

class Miembro(BaseModel):
    email: EmailStr
    nombre: str = Field(min_length=1, max_length=120)
    rol: str = Field(default="miembro", pattern="^(admin|miembro)$")
    permisos: list[str] = []
    profesional_id: int | None = None
    activo: bool = True


def _estado(u: dict) -> str:
    if not u["activo"]:
        return "baja"
    return "activo" if u.get("password_hash") else "invitado"


def _ficha(fila: dict) -> dict:
    """Un miembro tal como lo ve el administrador en la pestaña Equipo."""
    u = usuario_por_id(fila["id"])
    return {
        "id": u["id"], "email": u["email"], "nombre": u.get("nombre") or u["email"],
        "rol": u["rol"], "activo": u["activo"], "estado": _estado(u),
        "permisos": u["permisos"], "profesional_id": u.get("profesional_id"),
        "profesional": fila.get("profesional"),
        "ultimo_acceso": u.get("ultimo_acceso"), "creado": u.get("creado"),
    }


_SQL_EQUIPO = """
    SELECT u.id, p.nombre AS profesional
    FROM usuarios u LEFT JOIN profesionales p ON p.id = u.profesional_id
"""


def _admins_activos(salvo: int | None = None) -> int:
    return db.escalar("SELECT COUNT(*) FROM usuarios WHERE rol = 'admin' AND activo = 1 AND id != ?",
                      (salvo or 0,))


def _comprobar(m: Miembro, id_: int | None = None) -> tuple[str, list[str]]:
    email = m.email.strip().lower()
    if db.escalar("SELECT COUNT(*) FROM usuarios WHERE email = ? AND id != ?", (email, id_ or 0)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya hay alguien en el equipo con ese correo.")
    if m.profesional_id is not None:
        if not db.escalar("SELECT COUNT(*) FROM profesionales WHERE id = ?", (m.profesional_id,)):
            raise HTTPException(422, "Ese profesional no existe.")
        otro = db.fila("SELECT nombre, email FROM usuarios WHERE profesional_id = ? AND id != ?",
                       (m.profesional_id, id_ or 0))
        if otro:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                f"Esa ficha de profesional ya está vinculada a {otro['nombre'] or otro['email']}.")
    # El administrador lo ve todo: sus permisos no se guardan, no hacen falta.
    permisos = [] if m.rol == "admin" else permisos_de(m.permisos)
    return email, permisos


@router.get("/equipo")
def listar(u: dict = Depends(sesion_actual)):
    exigir_admin(u)
    filas = db.filas(_SQL_EQUIPO + " ORDER BY u.rol = 'admin' DESC, u.activo DESC, "
                                   "COALESCE(u.nombre, u.email) COLLATE NOCASE")
    return [_ficha(f) for f in filas]


@router.post("/equipo", status_code=201)
def crear(m: Miembro, u: dict = Depends(sesion_actual)):
    exigir_admin(u)
    email, permisos = _comprobar(m)
    with db.tx() as con:
        nuevo = con.execute(
            """INSERT INTO usuarios (email, nombre, rol, permisos, profesional_id, activo)
               VALUES (?,?,?,?,?,1)""",
            (email, m.nombre.strip(), m.rol, ",".join(permisos), m.profesional_id)).lastrowid
    ficha = _ficha(db.fila(_SQL_EQUIPO + " WHERE u.id = ?", (nuevo,)))
    return {"miembro": ficha, **_invitar(usuario_por_id(nuevo))}


@router.put("/equipo/{id_}")
def actualizar(id_: int, m: Miembro, u: dict = Depends(sesion_actual)):
    exigir_admin(u)
    antes = usuario_por_id(id_)
    if not antes:
        raise HTTPException(404, "No encontrado")
    if id_ == u["id"] and (m.rol != "admin" or not m.activo):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "No puedes quitarte a ti mismo el acceso de administrador ni darte de baja.")
    if antes["rol"] == "admin" and (m.rol != "admin" or not m.activo) and not _admins_activos(salvo=id_):
        raise HTTPException(status.HTTP_409_CONFLICT, "Tiene que quedar al menos un administrador activo.")
    email, permisos = _comprobar(m, id_)
    with db.tx() as con:
        con.execute("""UPDATE usuarios SET email = ?, nombre = ?, rol = ?, permisos = ?,
                       profesional_id = ?, activo = ? WHERE id = ?""",
                    (email, m.nombre.strip(), m.rol, ",".join(permisos), m.profesional_id,
                     1 if m.activo else 0, id_))
    # Una baja o un cambio de correo cierran las sesiones abiertas. Los
    # permisos no hace falta: se leen de nuevo en cada petición.
    if not m.activo or email != antes["email"]:
        cerrar_sesiones_de(antes)
    return _ficha(db.fila(_SQL_EQUIPO + " WHERE u.id = ?", (id_,)))


@router.post("/equipo/{id_}/invitar")
def reinvitar(id_: int, u: dict = Depends(sesion_actual)):
    exigir_admin(u)
    m = usuario_por_id(id_)
    if not m:
        raise HTTPException(404, "No encontrado")
    if not m["activo"]:
        raise HTTPException(status.HTTP_409_CONFLICT, "Está de baja. Actívalo antes de invitarlo.")
    if m.get("password_hash"):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Ya ha creado su contraseña. Si la ha olvidado, que use «He olvidado mi contraseña».")
    return _invitar(m)


@router.delete("/equipo/{id_}")
def borrar(id_: int, u: dict = Depends(sesion_actual)):
    exigir_admin(u)
    m = usuario_por_id(id_)
    if not m:
        raise HTTPException(404, "No encontrado")
    if id_ == u["id"]:
        raise HTTPException(status.HTTP_409_CONFLICT, "No puedes borrarte a ti mismo.")
    if m["rol"] == "admin" and not _admins_activos(salvo=id_):
        raise HTTPException(status.HTTP_409_CONFLICT, "Tiene que quedar al menos un administrador activo.")
    with db.tx() as con:
        # Lo que llevaba no se borra: se queda sin responsable, que es lo del
        # administrador, y desde ahí se reparte a otra persona.
        for tabla in db.TABLAS_CON_RESPONSABLE:
            con.execute(f"UPDATE {tabla} SET usuario_id = NULL WHERE usuario_id = ?", (id_,))
        con.execute("DELETE FROM sesiones WHERE usuario_id = ? OR email = ?", (id_, m["email"]))
        con.execute("DELETE FROM usuarios WHERE id = ?", (id_,))
    return {"ok": True}


@router.get("/equipo/modulos")
def modulos(u: dict = Depends(sesion_actual)):
    exigir_admin(u)
    return list(MODULOS)


# ── Crear o recuperar la contraseña (sin sesión) ─────────────────────────

class Enlace(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class NuevaClave(Enlace):
    password: str = Field(max_length=200)


@router.post("/clave/comprobar")
def comprobar_enlace(e: Enlace):
    """Para que la pantalla salude por el nombre antes de pedir la contraseña.

    POST y no GET: así el enlace no queda apuntado en ningún registro de accesos.
    """
    c = leer_clave(e.token)
    m = usuario_por_id(c["usuario_id"]) if c else None
    if not m or not m["activo"]:
        raise HTTPException(400, "El enlace no es válido o ha caducado. Pide uno nuevo.")
    return {"email": m["email"], "nombre": m.get("nombre") or "", "tipo": c["tipo"]}


@router.post("/clave")
def fijar_clave(datos: NuevaClave, request: Request):
    if not registrar_intento(_ip(request)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Demasiados intentos. Prueba de nuevo en un rato.")
    c = leer_clave(datos.token)
    m = usuario_por_id(c["usuario_id"]) if c else None
    if not m or not m["activo"]:
        raise HTTPException(400, "El enlace no es válido o ha caducado. Pide uno nuevo.")
    if len(datos.password) < MIN_PASSWORD:
        raise HTTPException(422, f"La contraseña tiene que tener al menos {MIN_PASSWORD} caracteres.")
    if datos.password.strip().lower() in (m["email"], m["email"].split("@")[0]):
        raise HTTPException(422, "La contraseña no puede ser tu correo.")
    # Cambiar la contraseña cierra las sesiones que hubiera abiertas: si
    # alguien la había averiguado, se queda fuera.
    cerrar_sesiones_de(m)
    with db.tx() as con:
        con.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?",
                    (crear_hash(datos.password), m["id"]))
        con.execute("DELETE FROM claves WHERE usuario_id = ?", (m["id"],))
    m = usuario_por_id(m["id"])
    token, expira = crear_sesion(m)
    return {"token": token, "expira": expira, "email": m["email"], "usuario": publico(m)}


class Recuperar(BaseModel):
    email: str = Field(max_length=200)


@router.post("/recuperar")
def recuperar(datos: Recuperar, request: Request):
    if not registrar_intento(_ip(request)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Demasiados intentos. Prueba de nuevo en un rato.")
    m = usuario_por_email(datos.email)
    if m and m["activo"]:
        token = crear_clave(m["id"], "recuperar", HORAS_RECUPERAR)
        nombre = m.get("nombre") or ""
        _correo(m["email"], "Cambia tu contraseña del panel de Loureiro",
                f"Hola{(' ' + nombre) if nombre else ''},",
                ["Alguien ha pedido cambiar la contraseña de tu acceso al panel de Loureiro Soluciones."],
                "Cambiar mi contraseña", f"{PANEL}#clave={token}",
                "El enlace sirve una sola vez y caduca en 2 horas. Si no lo has pedido tú, "
                "ignora este correo: tu contraseña sigue igual.")
    else:
        log.info("[equipo] recuperación pedida para un correo sin cuenta activa")
    # Misma respuesta siempre: el formulario no dice si el correo tiene cuenta.
    return {"ok": True}
