"""Estatutos de la empresa: cómo funciona Loureiro, por escrito.

Secciones con título y texto que escribe el administrador y lee todo el
equipo: cómo se atiende una solicitud, qué se hace en una visita, cómo se
cobra una obra, qué se hace ante una avería fuera de hora…

Se lee sin permisos especiales a propósito: de nada sirve escribir cómo
funciona la empresa si luego la mitad de la gente no puede abrirlo. Escribir
sí es solo del administrador.

El texto se guarda tal cual lo escribe el administrador, sin HTML: el panel
lo pinta escapado y solo reconoce viñetas, subtítulos y **negritas**, para
que no se pueda colar una etiqueta en una página que lee todo el equipo.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from . import db
from .auth import exigir_admin, sesion_actual

router = APIRouter(prefix="/api/admin", tags=["estatutos"])


class Seccion(BaseModel):
    titulo: str = Field(min_length=1, max_length=160)
    contenido: str = Field(default="", max_length=20000)


def _titulo(s: Seccion) -> str:
    """Un título de solo espacios pasa el mínimo de Pydantic y quedaría vacío."""
    limpio = s.titulo.strip()
    if not limpio:
        raise HTTPException(422, "Ponle un título a la sección.")
    return limpio


def _ahora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _lista() -> list[dict]:
    return db.filas("""
        SELECT e.*, u.nombre AS autor_nombre, u.email AS autor_email
        FROM estatutos e LEFT JOIN usuarios u ON u.id = e.actualizado_por
        ORDER BY e.orden, e.id
    """)


def _una(id_: int) -> dict:
    fila = db.fila("SELECT * FROM estatutos WHERE id = ?", (id_,))
    if not fila:
        raise HTTPException(404, "No encontrado")
    return fila


@router.get("/estatutos")
def listar(_: dict = Depends(sesion_actual)):
    return _lista()


@router.post("/estatutos", status_code=201)
def crear(s: Seccion, u: dict = Depends(sesion_actual)):
    exigir_admin(u)
    # La nueva va al final: el orden lo decide luego el administrador con las
    # flechas, no escribiendo números a mano.
    ultimo = db.escalar("SELECT MAX(orden) FROM estatutos", por_defecto=0)
    with db.tx() as con:
        nuevo = con.execute(
            """INSERT INTO estatutos (titulo, contenido, orden, actualizado, actualizado_por)
               VALUES (?,?,?,?,?)""",
            (_titulo(s), s.contenido.strip(), ultimo + 1, _ahora(), u["id"])).lastrowid
    return _una(nuevo)


@router.put("/estatutos/{id_}")
def actualizar(id_: int, s: Seccion, u: dict = Depends(sesion_actual)):
    exigir_admin(u)
    _una(id_)
    with db.tx() as con:
        con.execute("""UPDATE estatutos SET titulo = ?, contenido = ?, actualizado = ?,
                       actualizado_por = ? WHERE id = ?""",
                    (_titulo(s), s.contenido.strip(), _ahora(), u["id"], id_))
    return _una(id_)


@router.delete("/estatutos/{id_}")
def borrar(id_: int, u: dict = Depends(sesion_actual)):
    exigir_admin(u)
    _una(id_)
    with db.tx() as con:
        con.execute("DELETE FROM estatutos WHERE id = ?", (id_,))
    return {"ok": True}


@router.post("/estatutos/{id_}/mover")
def mover(id_: int, hacia: str, u: dict = Depends(sesion_actual)):
    """Sube o baja una sección intercambiándola con su vecina."""
    exigir_admin(u)
    if hacia not in ("arriba", "abajo"):
        raise HTTPException(422, "Solo se puede mover arriba o abajo.")
    actual = _una(id_)
    vecina = db.fila(
        "SELECT * FROM estatutos WHERE (orden, id) {} (?, ?) ORDER BY orden {}, id {} LIMIT 1".format(
            "<" if hacia == "arriba" else ">",
            "DESC" if hacia == "arriba" else "ASC",
            "DESC" if hacia == "arriba" else "ASC"),
        (actual["orden"], id_))
    if not vecina:
        return {"ok": True, "movida": False}
    with db.tx() as con:
        con.execute("UPDATE estatutos SET orden = ? WHERE id = ?", (vecina["orden"], id_))
        con.execute("UPDATE estatutos SET orden = ? WHERE id = ?", (actual["orden"], vecina["id"]))
        # Dos secciones con el mismo orden quedarían empatadas; se reparten
        # todos los números de nuevo para que el orden sea siempre claro.
        for i, fila in enumerate(con.execute(
                "SELECT id FROM estatutos ORDER BY orden, id").fetchall(), start=1):
            con.execute("UPDATE estatutos SET orden = ? WHERE id = ?", (i, fila[0]))
    return {"ok": True, "movida": True}
