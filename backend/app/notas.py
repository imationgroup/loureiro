"""Imágenes de las notas.

Igual que las fotos de las visitas (ver visitas.py): llegan ya reducidas desde
el navegador, en base64 dentro de un JSON, con su miniatura aparte, y se
guardan en la base para que la copia de seguridad siga siendo un fichero.

El alta, la edición y el borrado de la nota siguen en el CRUD genérico. Aquí
va la lista, que añade los ids de las imágenes de cada nota para pintar las
miniaturas sin otra petición, y las imágenes en sí.
"""

from fastapi import APIRouter, Depends, HTTPException, Response

from . import db
from .auth import exigir, filtro_responsable, sesion_actual
from .visitas import FotoNueva, MAX_FOTO, MAX_MINIATURA, _decodificar, _tipo_imagen

router = APIRouter(prefix="/api/admin", tags=["notas"])

MAX_FOTOS_POR_NOTA = 30


def fotos_de(notas: list[dict]) -> list[dict]:
    """Añade a cada nota la lista de ids de sus imágenes, en orden de subida."""
    if not notas:
        return notas
    ids = [n["id"] for n in notas]
    por_nota: dict[int, list[int]] = {}
    for f in db.filas(f"SELECT id, nota_id FROM nota_fotos WHERE nota_id IN ({','.join('?' * len(ids))}) "
                      "ORDER BY id", ids):
        por_nota.setdefault(f["nota_id"], []).append(f["id"])
    for n in notas:
        n["fotos"] = por_nota.get(n["id"], [])
    return notas


def _nota(u: dict, id_: int) -> dict:
    cond, params = filtro_responsable(u)
    n = db.fila(f"SELECT * FROM notas WHERE id = ? AND {cond}", (id_, *params))
    if not n:
        raise HTTPException(404, "No encontrado")
    return n


@router.get("/notas")
def listar(u: dict = Depends(sesion_actual)):
    """La lista del CRUD genérico, con las imágenes de cada nota.

    Va antes que el CRUD genérico, que se la tragaría con su /{recurso}.
    """
    exigir(u, "notas")
    cond, params = filtro_responsable(u)
    return fotos_de(db.filas(
        f"SELECT * FROM notas WHERE {cond} ORDER BY COALESCE(actualizado, creado) DESC, id DESC",
        params))


@router.post("/notas/{id_}/fotos", status_code=201)
def subir_foto(id_: int, foto: FotoNueva, u: dict = Depends(sesion_actual)):
    exigir(u, "notas")
    _nota(u, id_)
    if db.escalar("SELECT COUNT(*) FROM nota_fotos WHERE nota_id = ?", (id_,)) >= MAX_FOTOS_POR_NOTA:
        raise HTTPException(409, f"Una nota admite hasta {MAX_FOTOS_POR_NOTA} imágenes.")
    datos, tipo = _decodificar(foto.imagen, MAX_FOTO, "imagen")
    mini = _decodificar(foto.miniatura, MAX_MINIATURA, "miniatura")[0] if foto.miniatura else None
    with db.tx() as con:
        nuevo = con.execute(
            "INSERT INTO nota_fotos (nota_id, tipo, datos, miniatura) VALUES (?,?,?,?)",
            (id_, tipo, datos, mini)).lastrowid
    return {"id": nuevo}


@router.get("/notas/{id_}/fotos/{foto_id}")
def ver_foto(id_: int, foto_id: int, mini: bool = False, u: dict = Depends(sesion_actual)):
    exigir(u, "notas")
    _nota(u, id_)
    f = db.fila("SELECT tipo, datos, miniatura FROM nota_fotos WHERE id = ? AND nota_id = ?",
                (foto_id, id_))
    if not f:
        raise HTTPException(404, "No encontrado")
    if mini and f["miniatura"]:
        datos = bytes(f["miniatura"])
        tipo = _tipo_imagen(datos) or "image/jpeg"
    else:
        datos, tipo = bytes(f["datos"]), f["tipo"]
    return Response(content=datos, media_type=tipo,
                    headers={"Cache-Control": "private, max-age=31536000, immutable"})


@router.delete("/notas/{id_}/fotos/{foto_id}")
def borrar_foto(id_: int, foto_id: int, u: dict = Depends(sesion_actual)):
    exigir(u, "notas")
    _nota(u, id_)
    with db.tx() as con:
        cur = con.execute("DELETE FROM nota_fotos WHERE id = ? AND nota_id = ?", (foto_id, id_))
        if cur.rowcount == 0:
            raise HTTPException(404, "No encontrado")
    return {"ok": True}
