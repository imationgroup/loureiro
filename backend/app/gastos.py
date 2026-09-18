"""Categorías y estados de los gastos, que se editan desde el panel.

Cada gasto guarda el NOMBRE de su categoría y de su estado, no un id: así
eran los gastos de siempre (categoria = 'material') y así se leen sin
cruzar tablas. Por eso renombrar una categoría o un estado renombra también
los gastos que la llevan, y borrar uno que está en uso obliga a decir a
cuál se pasan sus gastos: un gasto no se puede quedar con un estado que ya
no existe.

Cada estado dice si el gasto cuenta como pagado. De ahí sale la columna
`pagado` de siempre, que es la que usan contabilidad y el panel para lo
pendiente de pago: se sigue rellenando sola al guardar.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from . import db
from .auth import exigir, sesion_actual

router = APIRouter(prefix="/api/admin/gastos", tags=["gastos"])

LISTAS = {
    "categorias": {"tabla": "gasto_categorias", "columna": "categoria", "una": "la categoría"},
    "estados": {"tabla": "gasto_estados", "columna": "estado", "una": "el estado"},
}


def estado_pendiente(con=None) -> str | None:
    """El estado que se pone a un gasto nuevo: el primero que no es pagado."""
    con = con or db.conexion()
    fila = con.execute("SELECT nombre FROM gasto_estados ORDER BY pagado, orden, id LIMIT 1").fetchone()
    return fila[0] if fila else None


def completar_gasto(d: dict, existente: dict | None):
    """Comprueba categoría y estado de un gasto y deja `pagado` a juego.

    Se llama desde el CRUD genérico al crear y al editar un gasto.
    """
    if existente is None:
        if not d.get("estado"):
            d["estado"] = estado_pendiente()
        if not d.get("categoria"):
            primera = db.fila("SELECT nombre FROM gasto_categorias ORDER BY orden, id LIMIT 1")
            if primera:
                d["categoria"] = primera["nombre"]
    if "estado" in d:
        e = db.fila("SELECT nombre, pagado FROM gasto_estados WHERE nombre = ? COLLATE NOCASE",
                    (d["estado"] or "",))
        if not e:
            raise HTTPException(422, "Ese estado de gasto no existe.")
        d["estado"], d["pagado"] = e["nombre"], e["pagado"]
    if "categoria" in d and d["categoria"]:
        c = db.fila("SELECT nombre FROM gasto_categorias WHERE nombre = ? COLLATE NOCASE",
                    (d["categoria"],))
        if not c:
            raise HTTPException(422, "Esa categoría de gasto no existe.")
        d["categoria"] = c["nombre"]


def _lista(que: str) -> dict:
    l = LISTAS.get(que)
    if not l:
        raise HTTPException(404, "No encontrado")
    return l


class Elemento(BaseModel):
    nombre: str = Field(min_length=1, max_length=60)
    pagado: bool | None = None      # solo para los estados


def _nombre(e: Elemento) -> str:
    nombre = " ".join(e.nombre.split())
    if not nombre:
        raise HTTPException(422, "Pon un nombre.")
    return nombre


def _repetido(tabla: str, nombre: str, salvo: int = 0):
    if db.escalar(f"SELECT COUNT(*) FROM {tabla} WHERE nombre = ? COLLATE NOCASE AND id != ?",
                  (nombre, salvo)):
        raise HTTPException(409, f"Ya hay una con el nombre «{nombre}».")


@router.get("/{que}")
def listar(que: str, u: dict = Depends(sesion_actual)):
    """La lista con cuántos gastos usan cada una (de toda la empresa)."""
    exigir(u, "costes")
    l = _lista(que)
    return db.filas(f"""
        SELECT x.*, (SELECT COUNT(*) FROM costes c WHERE c.{l['columna']} = x.nombre) AS n
        FROM {l['tabla']} x ORDER BY x.orden, x.id""")


@router.post("/{que}", status_code=201)
def crear(que: str, e: Elemento, u: dict = Depends(sesion_actual)):
    exigir(u, "costes")
    l = _lista(que)
    nombre = _nombre(e)
    _repetido(l["tabla"], nombre)
    with db.tx() as con:
        orden = con.execute(f"SELECT COALESCE(MAX(orden), 0) + 1 FROM {l['tabla']}").fetchone()[0]
        if que == "estados":
            nuevo = con.execute("INSERT INTO gasto_estados (nombre, pagado, orden) VALUES (?,?,?)",
                                (nombre, 1 if e.pagado else 0, orden)).lastrowid
        else:
            nuevo = con.execute("INSERT INTO gasto_categorias (nombre, orden) VALUES (?,?)",
                                (nombre, orden)).lastrowid
    return db.fila(f"SELECT * FROM {l['tabla']} WHERE id = ?", (nuevo,))


@router.put("/{que}/{id_}")
def editar(que: str, id_: int, e: Elemento, u: dict = Depends(sesion_actual)):
    """Renombra (y los gastos que la llevan con ella) o cambia si cuenta como pagado."""
    exigir(u, "costes")
    l = _lista(que)
    viejo = db.fila(f"SELECT * FROM {l['tabla']} WHERE id = ?", (id_,))
    if not viejo:
        raise HTTPException(404, "No encontrado")
    nombre = _nombre(e)
    _repetido(l["tabla"], nombre, id_)
    with db.tx() as con:
        con.execute(f"UPDATE {l['tabla']} SET nombre = ? WHERE id = ?", (nombre, id_))
        con.execute(f"UPDATE costes SET {l['columna']} = ? WHERE {l['columna']} = ?",
                    (nombre, viejo["nombre"]))
        if que == "estados" and e.pagado is not None:
            pagado = 1 if e.pagado else 0
            con.execute("UPDATE gasto_estados SET pagado = ? WHERE id = ?", (pagado, id_))
            con.execute("UPDATE costes SET pagado = ? WHERE estado = ?", (pagado, nombre))
    return db.fila(f"SELECT * FROM {l['tabla']} WHERE id = ?", (id_,))


@router.delete("/{que}/{id_}")
def borrar(que: str, id_: int, mover_a: str | None = None, u: dict = Depends(sesion_actual)):
    """Borra una categoría o un estado. Si hay gastos con él, se pasan a `mover_a`."""
    exigir(u, "costes")
    l = _lista(que)
    viejo = db.fila(f"SELECT * FROM {l['tabla']} WHERE id = ?", (id_,))
    if not viejo:
        raise HTTPException(404, "No encontrado")
    if db.escalar(f"SELECT COUNT(*) FROM {l['tabla']}") <= 1:
        raise HTTPException(409, f"No se puede borrar: tiene que quedar al menos {l['una']}.")
    en_uso = db.escalar(f"SELECT COUNT(*) FROM costes WHERE {l['columna']} = ?", (viejo["nombre"],))
    destino = None
    if en_uso:
        if not mover_a:
            raise HTTPException(409, f"Hay {en_uso} gastos con {l['una']} «{viejo['nombre']}». "
                                     "Di a cuál se pasan.")
        destino = db.fila(f"SELECT * FROM {l['tabla']} WHERE nombre = ? COLLATE NOCASE AND id != ?",
                          (mover_a, id_))
        if not destino:
            raise HTTPException(422, f"No existe {l['una']} a la que pasar los gastos.")
    with db.tx() as con:
        if destino:
            if que == "estados":
                con.execute("UPDATE costes SET estado = ?, pagado = ? WHERE estado = ?",
                            (destino["nombre"], destino["pagado"], viejo["nombre"]))
            else:
                con.execute("UPDATE costes SET categoria = ? WHERE categoria = ?",
                            (destino["nombre"], viejo["nombre"]))
        con.execute(f"DELETE FROM {l['tabla']} WHERE id = ?", (id_,))
    return {"ok": True, "movidos": en_uso}
