"""Imágenes y archivos de las notas.

Igual que las fotos de las visitas (ver visitas.py): llegan ya reducidas desde
el navegador, en base64 dentro de un JSON, con su miniatura aparte, y se
guardan en la base para que la copia de seguridad siga siendo un fichero.

El alta, la edición y el borrado de la nota siguen en el CRUD genérico. Aquí
va la lista, que añade los ids de las imágenes de cada nota para pintar las
miniaturas sin otra petición, y las imágenes en sí.
"""

import base64
import binascii
import os
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from . import db
from .auth import exigir, filtro_responsable, sesion_actual
from .visitas import FotoNueva, MAX_FOTO, MAX_MINIATURA, _decodificar, _tipo_imagen

router = APIRouter(prefix="/api/admin", tags=["notas"])

MAX_FOTOS_POR_NOTA = 30


def adjuntos_de(notas: list[dict]) -> list[dict]:
    """Añade a cada nota sus imágenes (ids) y sus archivos (id, nombre, tamaño)."""
    if not notas:
        return notas
    ids = [n["id"] for n in notas]
    marcas = ",".join("?" * len(ids))
    fotos: dict[int, list[int]] = {}
    for f in db.filas(f"SELECT id, nota_id FROM nota_fotos WHERE nota_id IN ({marcas}) ORDER BY id", ids):
        fotos.setdefault(f["nota_id"], []).append(f["id"])
    archivos: dict[int, list[dict]] = {}
    for a in db.filas(f"""SELECT id, nota_id, nombre, tamano FROM nota_archivos
                          WHERE completo = 1 AND nota_id IN ({marcas}) ORDER BY id""", ids):
        archivos.setdefault(a.pop("nota_id"), []).append(a)
    for n in notas:
        n["fotos"] = fotos.get(n["id"], [])
        n["archivos"] = archivos.get(n["id"], [])
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
    return adjuntos_de(db.filas(
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


# ═══ Archivos ═════════════════════════════════════════════════════════════

MAX_ARCHIVO = 20 * 1024 * 1024
MAX_ARCHIVOS_POR_NOTA = 20
# Un trozo en base64 tiene que caber, con el JSON, en el mega de Nginx.
MAX_TROZO = 700 * 1024

# Lo que se admite, por extensión, con el tipo con el que se sirve y cómo
# empieza el fichero de verdad. Los de Office nuevos y OpenDocument son ZIP;
# los de Office antiguos, OLE. Así una extensión cambiada no cuela otra cosa.
ZIP, OLE = b"PK\x03\x04", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
TIPOS = {
    "pdf": ("application/pdf", (b"%PDF",)),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", (ZIP,)),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", (ZIP,)),
    "pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", (ZIP,)),
    "odt": ("application/vnd.oasis.opendocument.text", (ZIP,)),
    "ods": ("application/vnd.oasis.opendocument.spreadsheet", (ZIP,)),
    "doc": ("application/msword", (OLE,)),
    "xls": ("application/vnd.ms-excel", (OLE,)),
    "ppt": ("application/vnd.ms-powerpoint", (OLE,)),
    "txt": ("text/plain; charset=utf-8", None),
    "csv": ("text/csv; charset=utf-8", None),
}


class ArchivoNuevo(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    tamano: int = Field(gt=0, le=MAX_ARCHIVO)


class Trozo(BaseModel):
    datos: str = Field(min_length=1, max_length=MAX_TROZO * 4 // 3 + 100)


def _extension(nombre: str) -> str:
    return os.path.splitext(nombre)[1].lower().lstrip(".")


def _archivo(u: dict, id_: int, archivo_id: int) -> dict:
    _nota(u, id_)
    a = db.fila("SELECT * FROM nota_archivos WHERE id = ? AND nota_id = ?", (archivo_id, id_))
    if not a:
        raise HTTPException(404, "No encontrado")
    return a


@router.post("/notas/{id_}/archivos", status_code=201)
def empezar_archivo(id_: int, datos: ArchivoNuevo, u: dict = Depends(sesion_actual)):
    """Abre la subida de un archivo. Luego llegan los trozos y el cierre."""
    exigir(u, "notas")
    _nota(u, id_)
    ext = _extension(datos.nombre)
    if ext not in TIPOS:
        raise HTTPException(422, "Solo se admiten PDF, Word, Excel, PowerPoint, OpenDocument, TXT y CSV.")
    with db.tx() as con:
        # Lo que se quedó a medias hace rato (se cortó la subida) no sirve.
        con.execute("""DELETE FROM nota_archivos WHERE completo = 0
                       AND creado < datetime('now', '-1 hour')""")
        if con.execute("SELECT COUNT(*) FROM nota_archivos WHERE nota_id = ? AND completo = 1",
                       (id_,)).fetchone()[0] >= MAX_ARCHIVOS_POR_NOTA:
            raise HTTPException(409, f"Una nota admite hasta {MAX_ARCHIVOS_POR_NOTA} archivos.")
        nombre = os.path.basename(datos.nombre.replace("\\", "/")).strip() or f"archivo.{ext}"
        nuevo = con.execute("INSERT INTO nota_archivos (nota_id, nombre, tipo, tamano) VALUES (?,?,?,?)",
                            (id_, nombre, TIPOS[ext][0], datos.tamano)).lastrowid
    return {"id": nuevo, "trozo": MAX_TROZO}


@router.put("/notas/{id_}/archivos/{archivo_id}/trozos/{indice}")
def subir_trozo(id_: int, archivo_id: int, indice: int, trozo: Trozo, u: dict = Depends(sesion_actual)):
    exigir(u, "notas")
    a = _archivo(u, id_, archivo_id)
    if a["completo"]:
        raise HTTPException(409, "Ese archivo ya está subido.")
    try:
        datos = base64.b64decode(trozo.datos, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(422, "El trozo no se ha podido leer.")
    if not datos or len(datos) > MAX_TROZO or indice < 0:
        raise HTTPException(422, "Trozo no válido.")
    with db.tx() as con:
        # Repetir un trozo (un reintento) lo sustituye.
        con.execute("INSERT OR REPLACE INTO nota_archivo_trozos (archivo_id, indice, datos) VALUES (?,?,?)",
                    (archivo_id, indice, datos))
    return {"ok": True}


@router.post("/notas/{id_}/archivos/{archivo_id}/fin")
def cerrar_archivo(id_: int, archivo_id: int, u: dict = Depends(sesion_actual)):
    """Comprueba que ha llegado entero y que es lo que dice ser."""
    exigir(u, "notas")
    a = _archivo(u, id_, archivo_id)
    total = db.escalar("SELECT SUM(length(datos)) FROM nota_archivo_trozos WHERE archivo_id = ?",
                       (archivo_id,))
    if total != a["tamano"]:
        raise HTTPException(422, "El archivo no ha llegado entero. Vuelve a subirlo.")
    primero = db.fila("SELECT datos FROM nota_archivo_trozos WHERE archivo_id = ? ORDER BY indice LIMIT 1",
                      (archivo_id,))
    cabeceras = TIPOS[_extension(a["nombre"])][1]
    if cabeceras and not any(bytes(primero["datos"]).startswith(c) for c in cabeceras):
        with db.tx() as con:
            con.execute("DELETE FROM nota_archivos WHERE id = ?", (archivo_id,))
        raise HTTPException(422, f"«{a['nombre']}» no es un archivo de ese tipo.")
    with db.tx() as con:
        con.execute("UPDATE nota_archivos SET completo = 1 WHERE id = ?", (archivo_id,))
    return {"id": archivo_id, "nombre": a["nombre"], "tamano": a["tamano"]}


@router.get("/notas/{id_}/archivos/{archivo_id}")
def descargar_archivo(id_: int, archivo_id: int, u: dict = Depends(sesion_actual)):
    exigir(u, "notas")
    a = _archivo(u, id_, archivo_id)
    if not a["completo"]:
        raise HTTPException(404, "No encontrado")
    datos = b"".join(bytes(t["datos"]) for t in db.filas(
        "SELECT datos FROM nota_archivo_trozos WHERE archivo_id = ? ORDER BY indice", (archivo_id,)))
    return Response(content=datos, media_type=a["tipo"], headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(a['nombre'])}",
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store"})


@router.delete("/notas/{id_}/archivos/{archivo_id}")
def borrar_archivo(id_: int, archivo_id: int, u: dict = Depends(sesion_actual)):
    exigir(u, "notas")
    _archivo(u, id_, archivo_id)
    with db.tx() as con:
        con.execute("DELETE FROM nota_archivos WHERE id = ?", (archivo_id,))
    return {"ok": True}
