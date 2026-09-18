"""Visitas: la toma de datos en casa del cliente, antes del presupuesto.

Cada visita es de un cliente y lleva notas y fotos. Un presupuesto puede
decir de qué visita sale (presupuestos.visita_id), y así quien lo prepara
tiene delante lo que se vio.

El alta, la edición y la lista para desplegables salen del CRUD genérico
(admin.TABLAS["visitas"]). Aquí va lo que ese CRUD no sabe hacer: la lista con
el cliente y el recuento de fotos, el borrado que suelta los presupuestos, y
las fotos.

Las fotos llegan ya reducidas desde el navegador, en JSON y codificadas en
base64, igual que la firma dibujada del presupuesto. Así no hace falta
python-multipart, y cada petición cabe en el límite de 1 MB que Nginx pone
por defecto al cuerpo: el panel sube de una en una.
"""

import base64
import binascii

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from . import db
from .auth import exigir, filtro_responsable, sesion_actual

router = APIRouter(prefix="/api/admin", tags=["visitas"])

# Quien hace presupuestos tiene que poder elegir de qué visita sale el suyo,
# aunque no tenga la pestaña de visitas. Solo la lista y las fotos: crear,
# editar o borrar sigue pidiendo el módulo.
LECTURA = ("visitas", "presupuestos")

# Tope de lo que se guarda por foto, ya decodificada. El panel las manda de
# unos cientos de KB; esto solo para lo que llegue de otra parte.
MAX_FOTO = 3 * 1024 * 1024
MAX_MINIATURA = 200 * 1024
MAX_FOTOS_POR_VISITA = 60

# Se mira la cabecera del fichero, no lo que diga la petición: el tipo que se
# guarda es el que luego se sirve, y tiene que ser de verdad una imagen.
FIRMAS = ((b"\xff\xd8\xff", "image/jpeg"),
          (b"\x89PNG\r\n\x1a\n", "image/png"))


def _tipo_imagen(datos: bytes) -> str | None:
    for cabecera, tipo in FIRMAS:
        if datos.startswith(cabecera):
            return tipo
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "image/webp"
    return None


def _decodificar(texto: str, maximo: int, que: str) -> tuple[bytes, str]:
    """De data URL (o base64 pelado) a bytes, comprobando que es una imagen."""
    if "," in texto[:100]:
        texto = texto.split(",", 1)[1]
    try:
        datos = base64.b64decode(texto, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(422, f"La {que} no se ha podido leer.")
    if len(datos) > maximo:
        raise HTTPException(413, f"La {que} es demasiado grande.")
    tipo = _tipo_imagen(datos)
    if not tipo:
        raise HTTPException(422, f"La {que} no es una imagen JPEG, PNG o WebP.")
    return datos, tipo


def _visita(u: dict, id_: int) -> dict:
    """La visita si la ve este usuario; si no, 404 (no se confirma que exista)."""
    cond, params = filtro_responsable(u)
    v = db.fila(f"SELECT * FROM visitas WHERE id = ? AND {cond}", (id_, *params))
    if not v:
        raise HTTPException(404, "No encontrado")
    return v


def _presupuestos_de(u: dict, visita_id: int) -> list[dict]:
    cond, params = filtro_responsable(u)
    return db.filas(
        f"""SELECT id, numero, estado, fecha FROM presupuestos
            WHERE visita_id = ? AND {cond} ORDER BY fecha DESC, id DESC""",
        (visita_id, *params))


@router.get("/visitas")
def listar(u: dict = Depends(sesion_actual)):
    """Las visitas con su cliente, cuántas fotos llevan y sus presupuestos.

    Va antes que el CRUD genérico, que se la tragaría con su /{recurso}.
    """
    exigir(u, *LECTURA)
    cond, params = filtro_responsable(u, "v")
    visitas = db.filas(f"""
        SELECT v.*, c.nombre AS cliente,
               (SELECT COUNT(*) FROM visita_fotos f WHERE f.visita_id = v.id) AS n_fotos,
               (SELECT id FROM visita_fotos f WHERE f.visita_id = v.id
                ORDER BY f.id LIMIT 1) AS portada
        FROM visitas v
        LEFT JOIN clientes c ON c.id = v.cliente_id
        WHERE {cond}
        ORDER BY v.fecha DESC, v.id DESC
    """, params)
    # Los presupuestos que salen de cada visita, de una sola consulta.
    cp, pp = filtro_responsable(u)
    por_visita: dict[int, list] = {}
    for p in db.filas(f"""SELECT id, numero, estado, visita_id FROM presupuestos
                          WHERE visita_id IS NOT NULL AND {cp}
                          ORDER BY fecha DESC, id DESC""", pp):
        por_visita.setdefault(p["visita_id"], []).append(
            {"id": p["id"], "numero": p["numero"], "estado": p["estado"]})
    for v in visitas:
        v["presupuestos"] = por_visita.get(v["id"], [])
    return visitas


@router.get("/visitas/{id_}")
def ver(id_: int, u: dict = Depends(sesion_actual)):
    exigir(u, *LECTURA)
    v = _visita(u, id_)
    v["fotos"] = db.filas(
        "SELECT id, tipo, length(datos) AS bytes, creado FROM visita_fotos "
        "WHERE visita_id = ? ORDER BY id", (id_,))
    v["presupuestos"] = _presupuestos_de(u, id_)
    return v


@router.delete("/visitas/{id_}")
def borrar(id_: int, u: dict = Depends(sesion_actual)):
    """Borra la visita con sus fotos. Los presupuestos se quedan, sin visita."""
    exigir(u, "visitas")
    _visita(u, id_)
    with db.tx() as con:
        con.execute("UPDATE presupuestos SET visita_id = NULL WHERE visita_id = ?", (id_,))
        con.execute("DELETE FROM visita_fotos WHERE visita_id = ?", (id_,))
        con.execute("DELETE FROM visitas WHERE id = ?", (id_,))
    return {"ok": True}


class FotoNueva(BaseModel):
    # Data URL de la foto y de su miniatura, ya reducidas por el panel.
    imagen: str = Field(min_length=100, max_length=MAX_FOTO * 4 // 3 + 200)
    miniatura: str | None = Field(default=None, max_length=MAX_MINIATURA * 4 // 3 + 200)


@router.post("/visitas/{id_}/fotos", status_code=201)
def subir_foto(id_: int, foto: FotoNueva, u: dict = Depends(sesion_actual)):
    exigir(u, "visitas")
    _visita(u, id_)
    if db.escalar("SELECT COUNT(*) FROM visita_fotos WHERE visita_id = ?", (id_,)) \
            >= MAX_FOTOS_POR_VISITA:
        raise HTTPException(409, f"Una visita admite hasta {MAX_FOTOS_POR_VISITA} fotos.")
    datos, tipo = _decodificar(foto.imagen, MAX_FOTO, "foto")
    mini = _decodificar(foto.miniatura, MAX_MINIATURA, "miniatura")[0] if foto.miniatura else None
    with db.tx() as con:
        nuevo = con.execute(
            "INSERT INTO visita_fotos (visita_id, tipo, datos, miniatura) VALUES (?,?,?,?)",
            (id_, tipo, datos, mini)).lastrowid
    return db.fila("SELECT id, tipo, length(datos) AS bytes, creado FROM visita_fotos "
                   "WHERE id = ?", (nuevo,))


@router.get("/visitas/{id_}/fotos/{foto_id}")
def ver_foto(id_: int, foto_id: int, mini: bool = False, u: dict = Depends(sesion_actual)):
    """La foto en sí. Con ?mini=1, la miniatura (o la grande si no la tiene)."""
    exigir(u, *LECTURA)
    _visita(u, id_)
    f = db.fila("SELECT tipo, datos, miniatura FROM visita_fotos WHERE id = ? AND visita_id = ?",
                (foto_id, id_))
    if not f:
        raise HTTPException(404, "No encontrado")
    if mini and f["miniatura"]:
        datos = bytes(f["miniatura"])
        tipo = _tipo_imagen(datos) or "image/jpeg"
    else:
        datos, tipo = bytes(f["datos"]), f["tipo"]
    # Una foto no cambia nunca: si se quiere otra, se sube otra con otro id.
    # "private" para que ningún proxy intermedio se quede con una copia.
    return Response(content=datos, media_type=tipo,
                    headers={"Cache-Control": "private, max-age=31536000, immutable"})


@router.delete("/visitas/{id_}/fotos/{foto_id}")
def borrar_foto(id_: int, foto_id: int, u: dict = Depends(sesion_actual)):
    exigir(u, "visitas")
    _visita(u, id_)
    with db.tx() as con:
        cur = con.execute("DELETE FROM visita_fotos WHERE id = ? AND visita_id = ?",
                          (foto_id, id_))
        if cur.rowcount == 0:
            raise HTTPException(404, "No encontrado")
    return {"ok": True}
