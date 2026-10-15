"""Certificados de instalación eléctrica (CIE), el boletín de toda la vida.

Cada certificado es la cabecera —titular, emplazamiento, derivación
individual, protecciones— más la lista de circuitos del cuadro, que en el
impreso oficial son ocho filas como mucho.

El PDF que se descarga no es un documento parecido al oficial: es el propio
impreso IN614C de la Xunta con los datos escritos encima (ver cie_pdf.py).

Va en su propio módulo y no en el CRUD genérico porque los circuitos se
guardan aparte y tienen que ir y venir con su certificado en la misma
operación, igual que las líneas de un presupuesto.

El impreso se le manda al técnico para que tramite el boletín. Cuando lo ha
tramitado devuelve el CIE oficial firmado y la memoria técnica, que se
adjuntan aquí mismo al certificado (uno de cada).
"""

import base64
import binascii
import os
from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from . import cie_pdf, db
from .auth import (comprobar_referencias, es_admin, exigir, filtro_responsable,
                   sesion_actual)
from .documentos import siguiente_numero

# Antes que el CRUD genérico, que se tragaría /cie como si fuese una tabla.
router = APIRouter(prefix="/api/admin/cie", tags=["certificados"])

MODULO = "certificados"
MAX_CIRCUITOS = 8

# Lo que se puede escribir. Es, campo a campo, lo que tiene el impreso.
CAMPOS = (
    "cliente_id", "obra_id",
    "titular", "titular_nif", "emplazamiento", "numero_via", "piso", "ref_catastral",
    "provincia", "ayuntamiento", "distribuidora", "uso", "superficie",
    "tipo_instalacion", "grado",
    "di_longitud", "di_seccion", "di_tension", "di_potencia",
    "prot_iga", "prot_dif1_int", "prot_dif1_sens",
    "prot_iga2", "prot_dif2_int", "prot_dif2_sens", "prot_resistencia",
    "observaciones", "organismo_control", "acta_numero",
    "empresa_nif", "instalador", "instalador_nif", "fecha",
)

TIPOS = ("nueva", "reforma", "cambio_tension", "cambio_titular", "ampliacion", "otras")
GRADOS = ("BÁSICO", "ELEVADO", "ESPECIAL")


class Circuito(BaseModel):
    numero: str | None = Field(default=None, max_length=10)
    designacion: str | None = Field(default=None, max_length=120)
    seccion: str | None = Field(default=None, max_length=20)
    interruptor: str | None = Field(default=None, max_length=20)


class Certificado(BaseModel):
    titular: str = Field(min_length=1, max_length=160)
    titular_nif: str | None = Field(default=None, max_length=20)
    emplazamiento: str | None = Field(default=None, max_length=160)
    numero_via: str | None = Field(default=None, max_length=20)
    piso: str | None = Field(default=None, max_length=20)
    ref_catastral: str | None = Field(default=None, max_length=30)
    provincia: str | None = Field(default=None, max_length=60)
    ayuntamiento: str | None = Field(default=None, max_length=80)
    distribuidora: str | None = Field(default=None, max_length=80)
    uso: str | None = Field(default=None, max_length=80)
    superficie: str | None = Field(default=None, max_length=20)
    tipo_instalacion: str | None = Field(default=None, max_length=20)
    grado: str | None = Field(default=None, max_length=20)
    di_longitud: str | None = Field(default=None, max_length=20)
    di_seccion: str | None = Field(default=None, max_length=20)
    di_tension: str | None = Field(default=None, max_length=20)
    di_potencia: str | None = Field(default=None, max_length=20)
    prot_iga: str | None = Field(default=None, max_length=30)
    prot_dif1_int: str | None = Field(default=None, max_length=20)
    prot_dif1_sens: str | None = Field(default=None, max_length=20)
    prot_iga2: str | None = Field(default=None, max_length=30)
    prot_dif2_int: str | None = Field(default=None, max_length=20)
    prot_dif2_sens: str | None = Field(default=None, max_length=20)
    prot_resistencia: str | None = Field(default=None, max_length=20)
    observaciones: str | None = Field(default=None, max_length=1200)
    organismo_control: str | None = Field(default=None, max_length=120)
    acta_numero: str | None = Field(default=None, max_length=60)
    empresa_nif: str | None = Field(default=None, max_length=20)
    instalador: str | None = Field(default=None, max_length=120)
    instalador_nif: str | None = Field(default=None, max_length=20)
    fecha: str | None = None
    cliente_id: int | None = None
    obra_id: int | None = None
    usuario_id: int | None = None
    circuitos: list[Circuito] = []


def _validar(c: Certificado):
    # Como la escribe el catastro: en mayúsculas y sin espacios.
    if c.ref_catastral:
        c.ref_catastral = "".join(c.ref_catastral.split()).upper()
    if c.tipo_instalacion and c.tipo_instalacion not in TIPOS:
        raise HTTPException(422, "Ese tipo de instalación no existe en el impreso.")
    if c.grado and c.grado not in GRADOS:
        raise HTTPException(422, "El grado de electrificación es básico, elevado o especial.")
    if len(c.circuitos) > MAX_CIRCUITOS:
        raise HTTPException(422, "El impreso oficial solo tiene %d filas de circuitos."
                                 % MAX_CIRCUITOS)


def _visible(u: dict, id_: int) -> dict:
    """El certificado, si es de quien lo pide. 404 y no 403: ni existe."""
    cond, params = filtro_responsable(u)
    fila = db.fila(f"SELECT * FROM certificados WHERE id = ? AND {cond}", (id_, *params))
    if not fila:
        raise HTTPException(404, "No encontrado")
    return fila


def _circuitos(id_: int) -> list[dict]:
    return db.filas("""SELECT numero, designacion, seccion, interruptor
                       FROM certificado_circuitos WHERE certificado_id = ?
                       ORDER BY orden, id""", (id_,))


def _guardar_circuitos(con, id_: int, circuitos: list[Circuito]):
    con.execute("DELETE FROM certificado_circuitos WHERE certificado_id = ?", (id_,))
    for i, c in enumerate(circuitos[:MAX_CIRCUITOS]):
        if not any((c.numero, c.designacion, c.seccion, c.interruptor)):
            continue        # una fila vacía no se guarda
        con.execute("""INSERT INTO certificado_circuitos
                         (certificado_id, orden, numero, designacion, seccion, interruptor)
                       VALUES (?,?,?,?,?,?)""",
                    (id_, i, c.numero, c.designacion, c.seccion, c.interruptor))


@router.get("")
def listar(u: dict = Depends(sesion_actual)):
    """Los certificados, con el nombre del cliente para la tabla del panel."""
    exigir(u, MODULO)
    cond, params = filtro_responsable(u, "c")
    return db.filas(f"""
        SELECT c.*, TRIM(COALESCE(cl.nombre, '') || ' ' || COALESCE(cl.apellidos, '')) AS cliente,
               (SELECT COUNT(*) FROM certificado_circuitos x WHERE x.certificado_id = c.id) AS n_circuitos,
               EXISTS (SELECT 1 FROM certificado_archivos a WHERE a.certificado_id = c.id
                       AND a.clase = 'boletin' AND a.completo = 1) AS tiene_boletin,
               EXISTS (SELECT 1 FROM certificado_archivos a WHERE a.certificado_id = c.id
                       AND a.clase = 'memoria' AND a.completo = 1) AS tiene_memoria
        FROM certificados c
        LEFT JOIN clientes cl ON cl.id = c.cliente_id
        WHERE {cond}
        ORDER BY c.fecha DESC, c.id DESC""", params)


@router.get("/{id_}")
def ver(id_: int, u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
    cert = _visible(u, id_)
    cert["circuitos"] = _circuitos(id_)
    cert["archivos"] = _archivos(id_)
    return cert


@router.post("", status_code=201)
def crear(cert: Certificado, u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
    _validar(cert)
    datos = cert.model_dump()
    circuitos = cert.circuitos
    comprobar_referencias(u, datos)
    # Lo que se crea es de quien lo crea; el administrador puede repartirlo.
    datos["usuario_id"] = datos.get("usuario_id") if es_admin(u) else u["id"]
    datos["fecha"] = datos.get("fecha") or date.today().isoformat()

    columnas = [k for k in CAMPOS if k in datos] + ["usuario_id", "numero"]
    with db.tx() as con:
        numero = siguiente_numero(con, "certificados", int(datos["fecha"][:4]))
        valores = [datos.get(k) for k in columnas[:-1]] + [numero]
        nuevo = con.execute(
            "INSERT INTO certificados (%s) VALUES (%s)"
            % (", ".join(columnas), ", ".join("?" * len(columnas))), valores).lastrowid
        _guardar_circuitos(con, nuevo, circuitos)
    return ver(nuevo, u)


@router.put("/{id_}")
def actualizar(id_: int, cert: Certificado, u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
    existente = _visible(u, id_)
    _validar(cert)
    datos = cert.model_dump()
    comprobar_referencias(u, datos, existente)
    if not es_admin(u):
        datos["usuario_id"] = existente["usuario_id"]

    columnas = [k for k in CAMPOS if k in datos] + ["usuario_id"]
    with db.tx() as con:
        con.execute("UPDATE certificados SET %s WHERE id = ?"
                    % ", ".join("%s = ?" % k for k in columnas),
                    [datos.get(k) for k in columnas] + [id_])
        _guardar_circuitos(con, id_, cert.circuitos)
    return ver(id_, u)


@router.delete("/{id_}", status_code=204)
def borrar(id_: int, u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
    _visible(u, id_)
    with db.tx() as con:
        con.execute("DELETE FROM certificados WHERE id = ?", (id_,))
    return Response(status_code=204)


@router.get("/{id_}/pdf")
def descargar(id_: int, u: dict = Depends(sesion_actual)):
    """El impreso oficial de la Xunta, relleno y aplanado."""
    exigir(u, MODULO)
    cert = _visible(u, id_)
    if not (cert.get("titular") or "").strip():
        raise HTTPException(422, "Falta el titular: sin eso el certificado no vale.")
    if not (cert.get("ref_catastral") or "").strip():
        raise HTTPException(422, "Falta la referencia catastral: sin ella el técnico "
                                 "no puede tramitar el boletín. Guárdala y vuelve a generarlo.")
    datos = cie_pdf.generar(cert, _circuitos(id_))
    return Response(content=datos, media_type="application/pdf",
                    headers={"Content-Disposition":
                             'attachment; filename="%s"' % cie_pdf.nombre_fichero(cert)})


# ═══ Documentación tramitada ══════════════════════════════════════════════
# Lo que devuelve el técnico: el CIE oficial firmado y la memoria técnica.
# Misma subida por trozos que los archivos de las notas (ver notas.py).

CLASES = {"boletin": "CIE firmado", "memoria": "Memoria técnica"}
MAX_ARCHIVO = 20 * 1024 * 1024
# Un trozo en base64 tiene que caber, con el JSON, en el mega de Nginx.
MAX_TROZO = 700 * 1024


class ArchivoNuevo(BaseModel):
    clase: str
    nombre: str = Field(min_length=1, max_length=200)
    tamano: int = Field(gt=0, le=MAX_ARCHIVO)


class Trozo(BaseModel):
    datos: str = Field(min_length=1, max_length=MAX_TROZO * 4 // 3 + 100)


def _archivos(id_: int) -> dict:
    """{clase: {id, nombre, tamano, creado}} de lo que ya está subido."""
    return {a.pop("clase"): a for a in db.filas(
        """SELECT id, clase, nombre, tamano, creado FROM certificado_archivos
           WHERE certificado_id = ? AND completo = 1 ORDER BY id""", (id_,))}


def _archivo(u: dict, id_: int, archivo_id: int) -> dict:
    _visible(u, id_)
    a = db.fila("SELECT * FROM certificado_archivos WHERE id = ? AND certificado_id = ?",
                (archivo_id, id_))
    if not a:
        raise HTTPException(404, "No encontrado")
    return a


@router.post("/{id_}/archivos", status_code=201)
def empezar_archivo(id_: int, datos: ArchivoNuevo, u: dict = Depends(sesion_actual)):
    """Abre la subida del boletín firmado o de la memoria. Luego, trozos y cierre."""
    exigir(u, MODULO)
    _visible(u, id_)
    if datos.clase not in CLASES:
        raise HTTPException(422, "Solo se adjuntan el CIE firmado y la memoria técnica.")
    if os.path.splitext(datos.nombre)[1].lower() != ".pdf":
        raise HTTPException(422, "Tiene que ser un PDF.")
    nombre = os.path.basename(datos.nombre.replace("\\", "/")).strip() or datos.clase + ".pdf"
    with db.tx() as con:
        # Lo que se quedó a medias hace rato (se cortó la subida) no sirve.
        con.execute("""DELETE FROM certificado_archivos WHERE completo = 0
                       AND creado < datetime('now', '-1 hour')""")
        nuevo = con.execute("""INSERT INTO certificado_archivos
                                 (certificado_id, clase, nombre, tipo, tamano)
                               VALUES (?,?,?,?,?)""",
                            (id_, datos.clase, nombre, "application/pdf", datos.tamano)).lastrowid
    return {"id": nuevo, "trozo": MAX_TROZO}


@router.put("/{id_}/archivos/{archivo_id}/trozos/{indice}")
def subir_trozo(id_: int, archivo_id: int, indice: int, trozo: Trozo,
                u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
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
        con.execute("""INSERT OR REPLACE INTO certificado_archivo_trozos (archivo_id, indice, datos)
                       VALUES (?,?,?)""", (archivo_id, indice, datos))
    return {"ok": True}


@router.post("/{id_}/archivos/{archivo_id}/fin")
def cerrar_archivo(id_: int, archivo_id: int, u: dict = Depends(sesion_actual)):
    """Comprueba que ha llegado entero y que es un PDF; si había otro, lo sustituye."""
    exigir(u, MODULO)
    a = _archivo(u, id_, archivo_id)
    total = db.escalar("SELECT SUM(length(datos)) FROM certificado_archivo_trozos WHERE archivo_id = ?",
                       (archivo_id,))
    if total != a["tamano"]:
        raise HTTPException(422, "El archivo no ha llegado entero. Vuelve a subirlo.")
    primero = db.fila("""SELECT datos FROM certificado_archivo_trozos WHERE archivo_id = ?
                         ORDER BY indice LIMIT 1""", (archivo_id,))
    if not bytes(primero["datos"]).startswith(b"%PDF"):
        with db.tx() as con:
            con.execute("DELETE FROM certificado_archivos WHERE id = ?", (archivo_id,))
        raise HTTPException(422, f"«{a['nombre']}» no es un PDF.")
    with db.tx() as con:
        con.execute("""DELETE FROM certificado_archivos
                       WHERE certificado_id = ? AND clase = ? AND id != ?""",
                    (id_, a["clase"], archivo_id))
        con.execute("UPDATE certificado_archivos SET completo = 1 WHERE id = ?", (archivo_id,))
    return {"id": archivo_id, "clase": a["clase"], "nombre": a["nombre"], "tamano": a["tamano"]}


@router.get("/{id_}/archivos/{archivo_id}")
def descargar_archivo(id_: int, archivo_id: int, u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
    a = _archivo(u, id_, archivo_id)
    if not a["completo"]:
        raise HTTPException(404, "No encontrado")
    datos = b"".join(bytes(t["datos"]) for t in db.filas(
        "SELECT datos FROM certificado_archivo_trozos WHERE archivo_id = ? ORDER BY indice",
        (archivo_id,)))
    return Response(content=datos, media_type=a["tipo"], headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(a['nombre'])}",
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store"})


@router.delete("/{id_}/archivos/{archivo_id}")
def borrar_archivo(id_: int, archivo_id: int, u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
    _archivo(u, id_, archivo_id)
    with db.tx() as con:
        con.execute("DELETE FROM certificado_archivos WHERE id = ?", (archivo_id,))
    return {"ok": True}
