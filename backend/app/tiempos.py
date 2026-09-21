"""Partes de tiempo: las horas que se le echan a una obra.

Un parte se puede escribir a mano (tantas horas y minutos de tal día) o
contarlo con el cronómetro, que admite pausas para los descansos. El alta, la
edición, el borrado y la lista salen del CRUD genérico
(admin.TABLAS["tiempos"]); aquí va solo lo que ese CRUD no sabe hacer:
arrancar, pausar y decir qué está contando ahora mismo.

El estado del cronómetro vive en la base, no en el navegador: `segundos` es lo
acumulado de los tramos ya cerrados y `arrancado` la hora (UTC) en que empezó
el tramo abierto, o vacío si está parado. Así el tiempo sigue corriendo aunque
se cierre el panel, y lo que se arrancó en el móvil se ve desde el ordenador.

Cada persona tiene UN cronómetro: arrancar uno pausa el que tuviera corriendo.
Estar en dos obras a la vez no es que sea raro, es que no puede ser, y así el
tiempo no se cuenta dos veces.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from . import db
from .auth import comprobar_referencias, es_admin, exigir, filtro_responsable, sesion_actual

# Va montado antes del CRUD genérico: su /{recurso}/{id} se tragaría
# /tiempos/en-curso como si «en-curso» fuese el id de un parte.
router = APIRouter(prefix="/api/admin/tiempos", tags=["tiempos"])


def _ahora() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _leer(marca: str) -> datetime:
    """La hora guardada, siempre como UTC con zona."""
    d = datetime.fromisoformat(marca)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def con_total(parte: dict) -> dict:
    """El parte con lo que marca el cronómetro ahora mismo.

    `segundos` es lo cerrado y no se toca mientras corre: si el navegador se
    queda sin conexión a media tarde, lo que ya estaba guardado sigue ahí.
    """
    corriendo = bool(parte.get("arrancado"))
    total = parte["segundos"] + (
        max(0, int((_ahora() - _leer(parte["arrancado"])).total_seconds())) if corriendo else 0)
    return {**parte, "corriendo": corriendo, "total": total}


def _visible(u: dict, id_: int) -> dict:
    """El parte, si es de quien lo pide. 404 y no 403: ni existe, para él."""
    cond, params = filtro_responsable(u)
    fila = db.fila(f"SELECT * FROM tiempos WHERE id = ? AND {cond}", (id_, *params))
    if not fila:
        raise HTTPException(404, "No encontrado")
    return fila


def _cerrar_tramo(con, parte: dict) -> int:
    """Guarda lo que llevaba corriendo y lo deja parado. Devuelve el total."""
    if not parte.get("arrancado"):
        return parte["segundos"]
    corridos = max(0, int((_ahora() - _leer(parte["arrancado"])).total_seconds()))
    total = parte["segundos"] + corridos
    con.execute("UPDATE tiempos SET segundos = ?, arrancado = NULL WHERE id = ?",
                (total, parte["id"]))
    return total


def _pausar_los_demas(con, usuario_id, salvo: int = 0):
    """Deja parado cualquier otro cronómetro de esa persona."""
    for otro in db.filas(
            "SELECT * FROM tiempos WHERE arrancado IS NOT NULL AND id != ? AND usuario_id IS ?",
            (salvo, usuario_id)):
        _cerrar_tramo(con, otro)


class Arranque(BaseModel):
    obra_id: int
    concepto: str | None = Field(default=None, max_length=200)
    profesional_id: int | None = None


@router.get("/en-curso")
def en_curso(u: dict = Depends(sesion_actual)):
    """El parte que está contando ahora mismo, o nada."""
    exigir(u, "tiempos")
    fila = db.fila("SELECT * FROM tiempos WHERE arrancado IS NOT NULL AND usuario_id IS ? "
                   "ORDER BY id DESC LIMIT 1", (u["id"],))
    return {"parte": con_total(fila) if fila else None}


@router.post("/arrancar", status_code=201)
def arrancar_nuevo(datos: Arranque, u: dict = Depends(sesion_actual)):
    """Empieza a contar en una obra: crea el parte y lo pone en marcha."""
    exigir(u, "tiempos")
    comprobar_referencias(u, {"obra_id": datos.obra_id})
    # Un miembro apunta a su nombre; el administrador, a quien diga (o a nadie).
    profesional = datos.profesional_id if es_admin(u) else (
        datos.profesional_id or u.get("profesional_id"))
    with db.tx() as con:
        _pausar_los_demas(con, u["id"])
        nuevo = con.execute(
            """INSERT INTO tiempos (obra_id, profesional_id, usuario_id, fecha, concepto,
                                    segundos, arrancado)
               VALUES (?,?,?,date('now'),?,0,?)""",
            (datos.obra_id, profesional, u["id"],
             (datos.concepto or "").strip() or None, _ahora().isoformat())).lastrowid
    return con_total(db.fila("SELECT * FROM tiempos WHERE id = ?", (nuevo,)))


@router.post("/{id_}/arrancar")
def arrancar(id_: int, u: dict = Depends(sesion_actual)):
    """Reanuda un parte parado: el descanso no cuenta y lo de antes se queda."""
    exigir(u, "tiempos")
    parte = _visible(u, id_)
    if parte["arrancado"]:
        return con_total(parte)
    with db.tx() as con:
        _pausar_los_demas(con, parte["usuario_id"], salvo=id_)
        con.execute("UPDATE tiempos SET arrancado = ? WHERE id = ?", (_ahora().isoformat(), id_))
    return con_total(db.fila("SELECT * FROM tiempos WHERE id = ?", (id_,)))


@router.post("/{id_}/pausar")
def pausar(id_: int, u: dict = Depends(sesion_actual)):
    """Para el cronómetro y guarda lo que llevaba."""
    exigir(u, "tiempos")
    parte = _visible(u, id_)
    with db.tx() as con:
        _cerrar_tramo(con, parte)
    return con_total(db.fila("SELECT * FROM tiempos WHERE id = ?", (id_,)))
