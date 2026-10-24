"""Tareas: lo que queda por hacer cuando el trabajo ya está hecho.

De momento hay una sola clase: pedir la valoración al cliente cuando se
termina su obra. Se crea sola al pasar la obra a «terminada» (ver
al_guardar_obra, que llama el CRUD de obras) y sale en la campanita hasta que
se le manda la petición o se descarta.

La petición va por correo, que lo manda el servidor, o por WhatsApp, que se
abre desde el panel con el mensaje escrito porque sale del teléfono de quien
lo manda. En los dos casos el enlace es el de reseñas de Google del ajuste
`resenas_url`, el mismo que el botón «Pedir reseña» de la ficha del cliente.

La tarea es del responsable de la obra: un miembro ve las de sus obras; el
administrador, todas.
"""

from datetime import date
from html import escape

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from . import db
from .auth import exigir, filtro_responsable, sesion_actual

# Va antes del CRUD genérico: /api/admin/{recurso} se tragaría /tareas.
router = APIRouter(prefix="/api/admin/tareas", tags=["tareas"])

TIPO_VALORACION = "valoracion"


def al_guardar_obra(obra_id: int):
    """Lo que toca a las tareas cada vez que se guarda una obra.

    Si está terminada, deja pendiente pedirle la valoración al cliente. Una
    por obra: volver a terminarla (se reabrió y se cerró otra vez) no repite
    la tarea, ni aunque ya se hubiera hecho o descartado.

    Las pendientes siguen a la obra: si cambia de cliente o de responsable,
    la tarea también, para pedírsela a quien toca y que la vea quien la lleva.
    """
    o = db.fila("SELECT id, titulo, cliente_id, estado, usuario_id FROM obras WHERE id = ?",
                (obra_id,))
    if not o:
        return
    with db.tx() as con:
        con.execute("UPDATE tareas SET cliente_id = ?, usuario_id = ? "
                    "WHERE obra_id = ? AND estado = 'pendiente'",
                    (o["cliente_id"], o["usuario_id"], o["id"]))
        if (o["estado"] or "").strip().lower() != "terminada":
            return
        con.execute(
            """INSERT INTO tareas (tipo, titulo, obra_id, cliente_id, usuario_id)
               SELECT ?, ?, ?, ?, ?
               WHERE NOT EXISTS (SELECT 1 FROM tareas WHERE tipo = ? AND obra_id = ?)""",
            (TIPO_VALORACION, "Pedir valoración al cliente", o["id"], o["cliente_id"],
             o["usuario_id"], TIPO_VALORACION, o["id"]))


def rellenar_terminadas():
    """Toda obra terminada tiene su tarea, también las de antes de existir Tareas.

    Se ejecuta al arrancar. Como hay una por obra, solo crea las que falten.
    Las de clientes a los que ya se les pidió reseña (el botón de su ficha)
    entran como hechas, con esa fecha; el resto, pendientes.
    """
    with db.tx() as con:
        con.execute(
            """INSERT INTO tareas (tipo, titulo, obra_id, cliente_id, usuario_id, estado,
                                   hecha_el, creado)
               SELECT ?, 'Pedir valoración al cliente', o.id, o.cliente_id, o.usuario_id,
                      CASE WHEN c.resena_pedida IS NOT NULL AND c.resena_pedida != ''
                           THEN 'hecha' ELSE 'pendiente' END,
                      NULLIF(c.resena_pedida, ''),
                      COALESCE(o.fecha_fin_real, o.creado)
               FROM obras o LEFT JOIN clientes c ON c.id = o.cliente_id
               WHERE lower(trim(o.estado)) = 'terminada'
                 AND NOT EXISTS (SELECT 1 FROM tareas t WHERE t.tipo = ? AND t.obra_id = o.id)""",
            (TIPO_VALORACION, TIPO_VALORACION))


_SELECT = """
    SELECT t.*, o.titulo AS obra, o.fecha_fin_real,
           TRIM(COALESCE(c.nombre, '') || ' ' || COALESCE(c.apellidos, '')) AS cliente,
           c.nombre AS cliente_nombre, c.telefono, c.email, c.resena_pedida
    FROM tareas t
    LEFT JOIN obras o ON o.id = t.obra_id
    LEFT JOIN clientes c ON c.id = t.cliente_id"""


def pendientes(u: dict) -> list[dict]:
    """Las tareas pendientes que ve este usuario, para la campanita."""
    cond, params = filtro_responsable(u, "t")
    return db.filas(f"{_SELECT} WHERE t.estado = 'pendiente' AND {cond} "
                    "ORDER BY t.creado DESC, t.id DESC", params)


def _tarea(id_: int, u: dict) -> dict:
    cond, params = filtro_responsable(u, "t")
    t = db.fila(f"{_SELECT} WHERE t.id = ? AND {cond}", (id_, *params))
    if not t:
        raise HTTPException(404, "No encontrado")
    return t


@router.get("")
def listar(u: dict = Depends(sesion_actual)):
    exigir(u, "tareas")
    cond, params = filtro_responsable(u, "t")
    # Primero lo pendiente; dentro, lo último arriba.
    return db.filas(f"{_SELECT} WHERE {cond} "
                    "ORDER BY t.estado != 'pendiente', t.creado DESC, t.id DESC", params)


def _enlace_resenas() -> str:
    fila = db.fila("SELECT valor FROM ajustes WHERE clave = 'resenas_url'")
    return ((fila or {}).get("valor") or "").strip()


def _correo_valoracion(t: dict, enlace: str) -> bool:
    from .main import send_email   # import tardío: main importa este módulo

    nombre = (t.get("cliente_nombre") or "").strip().split(" ")[0]
    obra = t.get("obra") or "el trabajo"
    texto = (f"Hola{(' ' + nombre) if nombre else ''},\n\n"
             f"Ya hemos terminado {obra}. Gracias por confiar en Loureiro Soluciones.\n\n"
             "Si has quedado contento con el trabajo, ¿nos dejas una valoración en Google? "
             "Es un minuto y nos ayuda mucho a que otros vecinos nos encuentren:\n"
             f"{enlace}\n\n"
             "Y si algo no ha quedado como esperabas, responde a este correo o llámanos "
             "al 603 905 128 y lo vemos.\n\n"
             "Un saludo,\nLoureiro Soluciones\n")
    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>¿Qué tal ha ido?</title></head><body style="margin:0;padding:0;background:#F4F5F7">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F4F5F7;padding:24px 12px"><tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#FFFFFF;border-radius:12px;overflow:hidden;font-family:Arial,Helvetica,sans-serif;color:#242A36">
  <tr><td style="background:#1E2533;padding:20px 28px"><span style="font-size:19px;font-weight:bold;color:#FFFFFF">Loureiro</span><span style="font-size:19px;color:#9AA2B1">soluciones</span></td></tr>
  <tr><td style="padding:28px">
    <p style="margin:0 0 14px;font-size:20px;font-weight:bold;color:#1E2533">Hola{(' ' + escape(nombre)) if nombre else ''},</p>
    <p style="margin:0 0 14px;font-size:15px;line-height:1.6">Ya hemos terminado <b>{escape(obra)}</b>. Gracias por confiar en nosotros.</p>
    <p style="margin:0 0 14px;font-size:15px;line-height:1.6">Si has quedado contento con el trabajo, ¿nos dejas una valoración en Google? Es un minuto y nos ayuda mucho a que otros vecinos nos encuentren.</p>
    <p style="margin:24px 0"><a href="{escape(enlace)}" style="display:inline-block;background:#F2A81C;color:#2C3444;font-weight:bold;font-size:15px;text-decoration:none;padding:13px 24px;border-radius:999px">Dejar mi valoración</a></p>
    <p style="margin:0;font-size:13px;line-height:1.6;color:#6B7180">Si algo no ha quedado como esperabas, responde a este correo o llámanos al 603 905 128 y lo vemos.</p>
  </td></tr>
</table></td></tr></table></body></html>"""
    return send_email(to=t["email"].strip(), subject="¿Qué tal ha ido? · Loureiro Soluciones",
                      body=texto, html=html)


def _hecha(t: dict, canal: str | None):
    """Apunta la tarea como hecha y la fecha de la reseña pedida en el cliente."""
    hoy = date.today().isoformat()
    with db.tx() as con:
        con.execute("UPDATE tareas SET estado = 'hecha', canal = ?, hecha_el = datetime('now') "
                    "WHERE id = ?", (canal, t["id"]))
        if t.get("cliente_id"):
            con.execute("UPDATE clientes SET resena_pedida = ? WHERE id = ?",
                        (hoy, t["cliente_id"]))


class Envio(BaseModel):
    # correo: lo manda el servidor. whatsapp: el panel abre WhatsApp con el
    # mensaje escrito y aquí solo se apunta.
    canal: str = Field(default="correo", pattern="^(correo|whatsapp)$")


@router.post("/{id_}/enviar")
def enviar(id_: int, datos: Envio, u: dict = Depends(sesion_actual)):
    """Manda al cliente la petición de valoración y da la tarea por hecha."""
    exigir(u, "tareas")
    t = _tarea(id_, u)
    enlace = _enlace_resenas()
    if not enlace:
        raise HTTPException(409, "Falta el enlace de reseñas de Google.")
    if not t.get("cliente_id"):
        raise HTTPException(422, "La obra no tiene cliente: no hay a quién pedírsela.")
    if datos.canal == "whatsapp":
        _hecha(t, "whatsapp")
        return {"enviado": True, "enlace": enlace, "telefono": t.get("telefono"),
                "nombre": t.get("cliente_nombre"), "obra": t.get("obra")}
    if not (t.get("email") or "").strip():
        raise HTTPException(422, "El cliente no tiene correo en su ficha.")
    if not _correo_valoracion(t, enlace):
        raise HTTPException(502, "No se ha podido enviar el correo.")
    _hecha(t, "correo")
    return {"enviado": True, "email": t["email"].strip()}


class Estado(BaseModel):
    estado: str = Field(pattern="^(pendiente|hecha|descartada)$")


@router.put("/{id_}/estado")
def cambiar_estado(id_: int, datos: Estado, u: dict = Depends(sesion_actual)):
    """Descartarla, darla por hecha sin mandar nada (se pidió en persona) o reabrirla."""
    exigir(u, "tareas")
    t = _tarea(id_, u)
    if datos.estado == "hecha":
        _hecha(t, None)
        return _tarea(id_, u)
    with db.tx() as con:
        if datos.estado == "pendiente":
            con.execute("UPDATE tareas SET estado = 'pendiente', canal = NULL, hecha_el = NULL "
                        "WHERE id = ?", (id_,))
        else:
            con.execute("UPDATE tareas SET estado = 'descartada', canal = NULL, "
                        "hecha_el = datetime('now') WHERE id = ?", (id_,))
    return _tarea(id_, u)
