"""Partes de tiempo: las horas que se le echan a una obra.

Un parte se escribe a mano: tantas horas y minutos de tal día. El alta, la
edición, el borrado y la lista salen del CRUD genérico
(admin.TABLAS["tiempos"]); aquí va solo lo que ese CRUD no sabe hacer: decir
a qué obras (y de qué clientes) puede echar partes cada persona.

Un miembro solo echa partes en las obras a las que está asignado como
profesional (Obras → Asignar); el administrador, en cualquiera.

Hubo un cronómetro (la columna `arrancado` es de entonces). Se quitó: los
partes que se quedaron contando se cierran al arrancar (ver cerrar_cronometros).

Cada parte genera su gasto de mano de obra en la obra: las horas por la
tarifa del profesional (ver gasto_de_parte). Se rehace cada vez que el parte
cambia, así que ese gasto no se toca a mano: se corrige el parte.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from . import db
from .auth import es_admin, exigir, sesion_actual
from .listas import estado_pendiente

# Va montado antes del CRUD genérico: su /{recurso}/{id} se tragaría
# /tiempos/obras como si «obras» fuese el id de un parte.
router = APIRouter(prefix="/api/admin/tiempos", tags=["tiempos"])


def obras_del_parte(u: dict) -> tuple[str, tuple]:
    """Condición SQL (sobre `obras`) con las obras a las que puede echar partes."""
    if es_admin(u):
        return "1=1", ()
    return ("id IN (SELECT obra_id FROM obra_profesionales WHERE profesional_id = ?)",
            (u.get("profesional_id") or 0,))


def comprobar_obra(u: dict, obra_id) -> None:
    """Un miembro no puede echar un parte a una obra a la que no está asignado."""
    if not obra_id or es_admin(u):
        return
    cond, params = obras_del_parte(u)
    if not db.fila(f"SELECT id FROM obras WHERE id = ? AND {cond}", (obra_id, *params)):
        raise HTTPException(403, "Solo puedes echar partes a las obras a las que estás asignado")


@router.get("/obras")
def obras(u: dict = Depends(sesion_actual)):
    """Las obras del desplegable del parte."""
    exigir(u, "tiempos")
    cond, params = obras_del_parte(u)
    return db.filas(f"SELECT * FROM obras WHERE {cond} ORDER BY id DESC", params)


@router.get("/clientes")
def clientes(u: dict = Depends(sesion_actual)):
    """Los clientes de esas obras: los únicos que se pueden elegir en el parte."""
    exigir(u, "tiempos")
    if es_admin(u):
        return db.filas("SELECT * FROM clientes ORDER BY nombre COLLATE NOCASE")
    cond, params = obras_del_parte(u)
    return db.filas(f"""SELECT * FROM clientes WHERE id IN (SELECT cliente_id FROM obras WHERE {cond})
                        ORDER BY nombre COLLATE NOCASE""", params)


def cerrar_cronometros():
    """Guarda lo contado en los partes que se quedaron con el cronómetro en marcha."""
    ahora = datetime.now(timezone.utc)
    with db.tx() as con:
        for p in con.execute("SELECT id, segundos, arrancado FROM tiempos "
                             "WHERE arrancado IS NOT NULL").fetchall():
            desde = datetime.fromisoformat(p["arrancado"])
            if not desde.tzinfo:
                desde = desde.replace(tzinfo=timezone.utc)
            total = (p["segundos"] or 0) + max(0, int((ahora - desde).total_seconds()))
            con.execute("UPDATE tiempos SET segundos = ?, arrancado = NULL WHERE id = ?",
                        (total, p["id"]))
            gasto_de_parte(con, p["id"])


# ═══ El gasto que genera el parte ═════════════════════════════════════════

def _categoria_mano_de_obra(con) -> str:
    """«mano de obra» si sigue en la lista; si la renombraron, la primera."""
    fila = con.execute("SELECT nombre FROM gasto_categorias WHERE nombre = 'mano de obra'").fetchone() \
        or con.execute("SELECT nombre FROM gasto_categorias ORDER BY orden, id LIMIT 1").fetchone()
    return fila["nombre"] if fila else "mano de obra"


def _duracion(segundos: int) -> str:
    h, m = divmod(round(segundos / 60), 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


def gasto_de_parte(con, tiempo_id: int):
    """Crea, rehace o quita el gasto de mano de obra de un parte.

    Importe = horas × tarifa del profesional, sin IVA (como todos los gastos).
    Lleva IVA si el profesional es autónomo (factura); si es de la plantilla,
    no. Sin obra, sin profesional, sin tarifa o sin tiempo no hay gasto.
    El estado de pago se respeta: si ya se marcó pagado, sigue pagado.
    """
    p = con.execute("""SELECT t.*, pr.nombre AS profesional, pr.tarifa_hora, pr.autonomo
                       FROM tiempos t LEFT JOIN profesionales pr ON pr.id = t.profesional_id
                       WHERE t.id = ?""", (tiempo_id,)).fetchone()
    previo = con.execute("SELECT id FROM costes WHERE tiempo_id = ?", (tiempo_id,)).fetchone()
    importe = round((p["segundos"] or 0) / 3600 * (p["tarifa_hora"] or 0), 2) if p else 0
    if not p or not p["obra_id"] or importe <= 0:
        if previo:
            con.execute("DELETE FROM costes WHERE id = ?", (previo["id"],))
        return

    concepto = " · ".join(x for x in (
        "Mano de obra", p["profesional"], (p["concepto"] or "").strip(),
        f"{_duracion(p['segundos'])} a {p['tarifa_hora']:g} €/h") if x)
    datos = {
        "obra_id": p["obra_id"], "profesional_id": p["profesional_id"],
        "categoria": _categoria_mano_de_obra(con), "concepto": concepto[:200],
        "importe": importe, "iva": 21 if p["autonomo"] else 0,
        "fecha": p["fecha"], "usuario_id": p["usuario_id"],
    }
    if previo:
        con.execute("UPDATE costes SET %s WHERE id = ?" % ", ".join(f"{k} = ?" for k in datos),
                    (*datos.values(), previo["id"]))
    else:
        datos.update(tiempo_id=tiempo_id, estado=estado_pendiente(), pagado=0)
        con.execute("INSERT INTO costes (%s) VALUES (%s)"
                    % (", ".join(datos), ", ".join("?" * len(datos))), tuple(datos.values()))


def gastos_del_profesional(con, profesional_id: int):
    """Al cambiar la tarifa de un profesional, se rehacen los gastos de sus partes."""
    for (id_,) in con.execute("SELECT id FROM tiempos WHERE profesional_id = ?",
                              (profesional_id,)).fetchall():
        gasto_de_parte(con, id_)
