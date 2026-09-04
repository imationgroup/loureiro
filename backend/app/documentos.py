"""Presupuestos y facturas: documentos con líneas de detalle.

Los dos se comportan igual —cabecera, líneas, totales—, así que comparten
el mismo código: solo cambian los nombres de las tablas y la columna que
enlaza las líneas.

El total NO se guarda en la tabla: se calcula siempre desde las líneas.
Un total almacenado acaba descuadrado en cuanto alguien edita una línea y
falla el recálculo.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from . import db
from .auth import sesion_actual

router = APIRouter(prefix="/api/admin", tags=["documentos"])

DOCUMENTOS = {
    "presupuestos": {
        "tabla": "presupuestos", "lineas": "presupuesto_lineas",
        "fk": "presupuesto_id",
        "campos": ["numero", "cliente_id", "obra_id", "fecha", "validez",
                   "estado", "notas"],
    },
    "facturas": {
        "tabla": "facturas", "lineas": "factura_lineas",
        "fk": "factura_id",
        "campos": ["numero", "cliente_id", "obra_id", "presupuesto_id",
                   "fecha", "vencimiento", "estado", "notas"],
    },
}


class Linea(BaseModel):
    concepto: str
    cantidad: float = 1
    unidad: str = "ud"
    precio: float = 0
    iva: float = 21


class Documento(BaseModel):
    cabecera: dict[str, Any] = {}
    lineas: list[Linea] = []


def _doc(tipo: str):
    d = DOCUMENTOS.get(tipo)
    if not d:
        raise HTTPException(404, "Tipo de documento desconocido")
    return d


def totales(lineas: list[dict]) -> dict:
    base = sum((l["cantidad"] or 0) * (l["precio"] or 0) for l in lineas)
    iva = sum((l["cantidad"] or 0) * (l["precio"] or 0) * (l["iva"] or 0) / 100
              for l in lineas)
    return {"base": round(base, 2), "iva": round(iva, 2),
            "total": round(base + iva, 2)}


def sincronizar_ingreso(factura_id: int):
    """Deja el apunte de la factura en la tabla de ingresos.

    Contabilidad sigue leyendo de un único sitio, así que no hay forma de
    contar dos veces lo mismo. Una factura anulada retira su apunte.
    """
    f = db.fila("SELECT * FROM facturas WHERE id = ?", (factura_id,))
    if not f:
        return
    lineas = db.filas("SELECT * FROM factura_lineas WHERE factura_id = ?",
                      (factura_id,))
    t = totales(lineas)
    base = t["base"]
    iva_pct = round(t["iva"] / base * 100, 2) if base else 21

    existente = db.fila("SELECT id FROM ingresos WHERE factura_id = ?", (factura_id,))
    with db.tx() as con:
        if f["estado"] == "anulada" or base == 0:
            if existente:
                con.execute("DELETE FROM ingresos WHERE id = ?", (existente["id"],))
            return
        datos = (f"Factura {f['numero'] or f['id']}", base, iva_pct, f["fecha"],
                 f["numero"], 1 if f["estado"] == "cobrada" else 0,
                 f["obra_id"], f["cliente_id"], factura_id)
        if existente:
            con.execute("""UPDATE ingresos SET concepto=?, importe=?, iva=?,
                           fecha=?, factura_ref=?, cobrado=?, obra_id=?,
                           cliente_id=? WHERE factura_id=?""", datos)
        else:
            con.execute("""INSERT INTO ingresos
                           (concepto, importe, iva, fecha, factura_ref, cobrado,
                            obra_id, cliente_id, factura_id)
                           VALUES (?,?,?,?,?,?,?,?,?)""", datos)


@router.get("/documentos/{tipo}")
def listar(tipo: str, _: str = Depends(sesion_actual)):
    d = _doc(tipo)
    docs = db.filas(f"""
        SELECT x.*, c.nombre AS cliente, o.titulo AS obra
        FROM {d['tabla']} x
        LEFT JOIN clientes c ON c.id = x.cliente_id
        LEFT JOIN obras o ON o.id = x.obra_id
        ORDER BY x.fecha DESC, x.id DESC
    """)
    for doc in docs:
        lineas = db.filas(f"SELECT * FROM {d['lineas']} WHERE {d['fk']} = ?",
                          (doc["id"],))
        doc.update(totales(lineas))
        doc["n_lineas"] = len(lineas)
    return docs


@router.get("/documentos/{tipo}/{id_}")
def ver(tipo: str, id_: int, _: str = Depends(sesion_actual)):
    d = _doc(tipo)
    doc = db.fila(f"SELECT * FROM {d['tabla']} WHERE id = ?", (id_,))
    if not doc:
        raise HTTPException(404, "No encontrado")
    doc["lineas"] = db.filas(
        f"SELECT * FROM {d['lineas']} WHERE {d['fk']} = ? ORDER BY orden, id",
        (id_,))
    doc.update(totales(doc["lineas"]))
    return doc


def _guardar_lineas(con, d, doc_id, lineas):
    for i, l in enumerate(lineas):
        con.execute(
            f"""INSERT INTO {d['lineas']} ({d['fk']}, concepto, cantidad,
                unidad, precio, iva, orden) VALUES (?,?,?,?,?,?,?)""",
            (doc_id, l.concepto, l.cantidad, l.unidad, l.precio, l.iva, i))


@router.post("/documentos/{tipo}", status_code=201)
def crear(tipo: str, doc: Documento, _: str = Depends(sesion_actual)):
    d = _doc(tipo)
    cab = {k: v for k, v in doc.cabecera.items() if k in d["campos"] and v is not None}
    with db.tx() as con:
        if cab:
            cols = ", ".join(cab)
            cur = con.execute(
                f"INSERT INTO {d['tabla']} ({cols}) VALUES ({', '.join('?' * len(cab))})",
                tuple(cab.values()))
        else:
            cur = con.execute(f"INSERT INTO {d['tabla']} DEFAULT VALUES")
        nuevo = cur.lastrowid
        _guardar_lineas(con, d, nuevo, doc.lineas)
    if tipo == "facturas":
        sincronizar_ingreso(nuevo)
    return ver(tipo, nuevo)


@router.put("/documentos/{tipo}/{id_}")
def actualizar(tipo: str, id_: int, doc: Documento, _: str = Depends(sesion_actual)):
    d = _doc(tipo)
    if not db.fila(f"SELECT id FROM {d['tabla']} WHERE id = ?", (id_,)):
        raise HTTPException(404, "No encontrado")
    cab = {k: v for k, v in doc.cabecera.items() if k in d["campos"]}
    with db.tx() as con:
        if cab:
            sets = ", ".join(f"{k} = ?" for k in cab)
            con.execute(f"UPDATE {d['tabla']} SET {sets} WHERE id = ?",
                        (*cab.values(), id_))
        # Las líneas se reemplazan enteras: es lo que hace el editor del
        # panel y evita casar altas, bajas y cambios una por una.
        con.execute(f"DELETE FROM {d['lineas']} WHERE {d['fk']} = ?", (id_,))
        _guardar_lineas(con, d, id_, doc.lineas)
    if tipo == "facturas":
        sincronizar_ingreso(id_)
    return ver(tipo, id_)


@router.delete("/documentos/{tipo}/{id_}")
def borrar(tipo: str, id_: int, _: str = Depends(sesion_actual)):
    d = _doc(tipo)
    with db.tx() as con:
        if tipo == "facturas":
            con.execute("DELETE FROM ingresos WHERE factura_id = ?", (id_,))
        cur = con.execute(f"DELETE FROM {d['tabla']} WHERE id = ?", (id_,))
        if cur.rowcount == 0:
            raise HTTPException(404, "No encontrado")
    return {"ok": True}


@router.post("/documentos/presupuestos/{id_}/facturar", status_code=201)
def facturar(id_: int, _: str = Depends(sesion_actual)):
    """Convierte un presupuesto aceptado en factura, copiando sus líneas."""
    p = db.fila("SELECT * FROM presupuestos WHERE id = ?", (id_,))
    if not p:
        raise HTTPException(404, "El presupuesto no existe")
    lineas = db.filas(
        "SELECT * FROM presupuesto_lineas WHERE presupuesto_id = ? ORDER BY orden, id",
        (id_,))
    if not lineas:
        raise HTTPException(422, "El presupuesto no tiene líneas que facturar")

    with db.tx() as con:
        cur = con.execute(
            """INSERT INTO facturas (cliente_id, obra_id, presupuesto_id, notas)
               VALUES (?,?,?,?)""",
            (p["cliente_id"], p["obra_id"], id_,
             f"Generada desde el presupuesto {p['numero'] or p['id']}"))
        nueva = cur.lastrowid
        for i, l in enumerate(lineas):
            con.execute(
                """INSERT INTO factura_lineas (factura_id, concepto, cantidad,
                   unidad, precio, iva, orden) VALUES (?,?,?,?,?,?,?)""",
                (nueva, l["concepto"], l["cantidad"], l["unidad"], l["precio"],
                 l["iva"], i))
        con.execute("UPDATE presupuestos SET estado = 'aceptado' WHERE id = ?", (id_,))
    sincronizar_ingreso(nueva)
    return ver("facturas", nueva)
