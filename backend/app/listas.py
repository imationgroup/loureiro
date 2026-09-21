"""Listas que se editan desde el panel: categorías y estados de los gastos,
estados de las obras y orígenes de los clientes (cómo nos conocieron).

Cada gasto u obra guarda el NOMBRE de su categoría o estado, no un id: así
eran los datos de siempre (categoria = 'material', estado = 'en curso') y así
se leen sin cruzar tablas. Por eso renombrar renombra también los registros
que lo llevan, y borrar uno que está en uso obliga a decir a cuál se pasan:
nada se puede quedar con un estado que ya no existe.

Una lista puede usarse en más de una tabla (el origen está en el cliente y en
la solicitud que lo trajo): entonces renombrar y mover afectan a todas.

Algunas listas llevan una marca por elemento:
- estados de gasto: si el gasto cuenta como pagado. De ahí sale la columna
  `pagado` de siempre, que es la que usa contabilidad, y se rellena sola.
- estados de obra: si la obra cuenta como activa (el contador del panel).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from . import db
from .auth import exigir, sesion_actual

router = APIRouter(prefix="/api/admin/listas", tags=["listas"])

LISTAS = {
    "gasto-categorias": {"tabla": "gasto_categorias", "uso": "costes", "columna": "categoria",
                         "una": "la categoría", "modulo": "costes"},
    "gasto-estados": {"tabla": "gasto_estados", "uso": "costes", "columna": "estado",
                      "una": "el estado", "modulo": "costes",
                      # la marca se copia a esta columna de cada gasto
                      "marca": "pagado", "espejo": "pagado"},
    "obra-estados": {"tabla": "obra_estados", "uso": "obras", "columna": "estado",
                     "una": "el estado", "modulo": "obras", "marca": "activa"},
    "cliente-origenes": {"tabla": "cliente_origenes", "uso": "clientes", "columna": "origen",
                         "una": "el origen", "modulo": "clientes",
                         # el mismo canal se apunta también en la solicitud
                         "tambien": [("solicitudes", "origen")]},
}


def _usos(l: dict) -> list[tuple[str, str]]:
    """Todas las tablas donde se guarda el nombre de un elemento de la lista."""
    return [(l["uso"], l["columna"]), *l.get("tambien", [])]


def completar_cliente(d: dict, existente: dict | None):
    """El origen de un cliente, si se indica, tiene que ser uno de la lista."""
    if d.get("origen"):
        d["origen"] = _existente("cliente_origenes", d["origen"], "origen")["nombre"]


def estado_pendiente(con=None) -> str | None:
    """El estado que se pone a un gasto nuevo: el primero que no es pagado."""
    con = con or db.conexion()
    fila = con.execute("SELECT nombre FROM gasto_estados ORDER BY pagado, orden, id LIMIT 1").fetchone()
    return fila[0] if fila else None


def _primero(tabla: str) -> str | None:
    fila = db.fila(f"SELECT nombre FROM {tabla} ORDER BY orden, id LIMIT 1")
    return fila["nombre"] if fila else None


def _existente(tabla: str, nombre, que: str) -> dict:
    fila = db.fila(f"SELECT * FROM {tabla} WHERE nombre = ? COLLATE NOCASE", (nombre or "",))
    if not fila:
        raise HTTPException(422, f"Ese {que} no existe.")
    return fila


def completar_gasto(d: dict, existente: dict | None):
    """Comprueba categoría y estado de un gasto y deja `pagado` a juego."""
    if existente is None:
        d["estado"] = d.get("estado") or estado_pendiente()
        d["categoria"] = d.get("categoria") or _primero("gasto_categorias")
    if "estado" in d:
        e = _existente("gasto_estados", d["estado"], "estado de gasto")
        d["estado"], d["pagado"] = e["nombre"], e["pagado"]
    if d.get("categoria"):
        d["categoria"] = _existente("gasto_categorias", d["categoria"], "categoría de gasto")["nombre"]


def completar_obra(d: dict, existente: dict | None):
    """El estado de una obra tiene que ser uno de la lista."""
    if existente is None:
        d["estado"] = d.get("estado") or _primero("obra_estados")
    if "estado" in d:
        d["estado"] = _existente("obra_estados", d["estado"], "estado de obra")["nombre"]


def _lista(que: str) -> dict:
    l = LISTAS.get(que)
    if not l:
        raise HTTPException(404, "No encontrado")
    return l


class Elemento(BaseModel):
    nombre: str = Field(min_length=1, max_length=60)
    marca: bool | None = None       # pagado / activa, en las listas que la llevan


def _nombre(e: Elemento) -> str:
    nombre = " ".join(e.nombre.split())
    if not nombre:
        raise HTTPException(422, "Pon un nombre.")
    return nombre


def _repetido(tabla: str, nombre: str, salvo: int = 0):
    if db.escalar(f"SELECT COUNT(*) FROM {tabla} WHERE nombre = ? COLLATE NOCASE AND id != ?",
                  (nombre, salvo)):
        raise HTTPException(409, f"Ya hay uno con el nombre «{nombre}».")


@router.get("/{que}")
def listar(que: str, u: dict = Depends(sesion_actual)):
    """La lista con cuántos registros usan cada elemento (de toda la empresa)."""
    l = _lista(que)
    exigir(u, l["modulo"])
    cuenta = " + ".join(f"(SELECT COUNT(*) FROM {t} r WHERE r.{c} = x.nombre)"
                        for t, c in _usos(l))
    return db.filas(f"SELECT x.*, {cuenta} AS n FROM {l['tabla']} x ORDER BY x.orden, x.id")


@router.post("/{que}", status_code=201)
def crear(que: str, e: Elemento, u: dict = Depends(sesion_actual)):
    l = _lista(que)
    exigir(u, l["modulo"])
    nombre = _nombre(e)
    _repetido(l["tabla"], nombre)
    with db.tx() as con:
        orden = con.execute(f"SELECT COALESCE(MAX(orden), 0) + 1 FROM {l['tabla']}").fetchone()[0]
        if l.get("marca"):
            nuevo = con.execute(
                f"INSERT INTO {l['tabla']} (nombre, {l['marca']}, orden) VALUES (?,?,?)",
                (nombre, 1 if e.marca else 0, orden)).lastrowid
        else:
            nuevo = con.execute(f"INSERT INTO {l['tabla']} (nombre, orden) VALUES (?,?)",
                                (nombre, orden)).lastrowid
    return db.fila(f"SELECT * FROM {l['tabla']} WHERE id = ?", (nuevo,))


@router.put("/{que}/{id_}")
def editar(que: str, id_: int, e: Elemento, u: dict = Depends(sesion_actual)):
    """Renombra (y los registros que lo llevan con él) o cambia su marca."""
    l = _lista(que)
    exigir(u, l["modulo"])
    viejo = db.fila(f"SELECT * FROM {l['tabla']} WHERE id = ?", (id_,))
    if not viejo:
        raise HTTPException(404, "No encontrado")
    nombre = _nombre(e)
    _repetido(l["tabla"], nombre, id_)
    with db.tx() as con:
        con.execute(f"UPDATE {l['tabla']} SET nombre = ? WHERE id = ?", (nombre, id_))
        for t, c in _usos(l):
            con.execute(f"UPDATE {t} SET {c} = ? WHERE {c} = ?", (nombre, viejo["nombre"]))
        if l.get("marca") and e.marca is not None:
            marca = 1 if e.marca else 0
            con.execute(f"UPDATE {l['tabla']} SET {l['marca']} = ? WHERE id = ?", (marca, id_))
            if l.get("espejo"):
                con.execute(f"UPDATE {l['uso']} SET {l['espejo']} = ? WHERE {l['columna']} = ?",
                            (marca, nombre))
    return db.fila(f"SELECT * FROM {l['tabla']} WHERE id = ?", (id_,))


@router.delete("/{que}/{id_}")
def borrar(que: str, id_: int, mover_a: str | None = None, u: dict = Depends(sesion_actual)):
    """Borra un elemento. Si hay registros con él, se pasan a `mover_a`."""
    l = _lista(que)
    exigir(u, l["modulo"])
    viejo = db.fila(f"SELECT * FROM {l['tabla']} WHERE id = ?", (id_,))
    if not viejo:
        raise HTTPException(404, "No encontrado")
    if db.escalar(f"SELECT COUNT(*) FROM {l['tabla']}") <= 1:
        raise HTTPException(409, f"No se puede borrar: tiene que quedar al menos {l['una']}.")
    en_uso = sum(db.escalar(f"SELECT COUNT(*) FROM {t} WHERE {c} = ?", (viejo["nombre"],))
                 for t, c in _usos(l))
    destino = None
    if en_uso:
        if not mover_a:
            raise HTTPException(409, f"Hay {en_uso} registros con {l['una']} «{viejo['nombre']}». "
                                     "Di a cuál se pasan.")
        destino = db.fila(f"SELECT * FROM {l['tabla']} WHERE nombre = ? COLLATE NOCASE AND id != ?",
                          (mover_a, id_))
        if not destino:
            raise HTTPException(422, f"No existe {l['una']} al que pasarlos.")
    with db.tx() as con:
        if destino:
            for t, c in _usos(l):
                con.execute(f"UPDATE {t} SET {c} = ? WHERE {c} = ?",
                            (destino["nombre"], viejo["nombre"]))
            if l.get("espejo"):
                con.execute(f"UPDATE {l['uso']} SET {l['espejo']} = ? WHERE {l['columna']} = ?",
                            (destino[l["marca"]], destino["nombre"]))
        con.execute(f"DELETE FROM {l['tabla']} WHERE id = ?", (id_,))
    return {"ok": True, "movidos": en_uso}
