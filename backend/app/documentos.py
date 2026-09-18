"""Presupuestos y facturas: documentos con líneas de detalle.

Los dos se comportan igual —cabecera, líneas, totales—, así que comparten
el mismo código: solo cambian los nombres de las tablas y la columna que
enlaza las líneas.

El total NO se guarda en la tabla: se calcula siempre desde las líneas.
Un total almacenado acaba descuadrado en cuanto alguien edita una línea y
falla el recálculo.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from . import db, pdf
from .auth import (comprobar_referencias, exigir, fijar_responsable, filtro_responsable,
                   sesion_actual)

router = APIRouter(prefix="/api/admin", tags=["documentos"])

DOCUMENTOS = {
    "presupuestos": {
        "tabla": "presupuestos", "lineas": "presupuesto_lineas",
        "fk": "presupuesto_id",
        # Quien lleva obras necesita la lista para elegir de qué presupuesto
        # sale cada obra, aunque no tenga la pestaña de presupuestos. Solo la
        # lista: abrir, editar o descargar uno sigue pidiendo su módulo.
        "lectura": ("presupuestos", "obras"),
        "campos": ["numero", "cliente_id", "obra_id", "visita_id", "fecha", "validez",
                   "estado", "notas", "motivo_cancelacion", "cancelado_el"],
    },
    "facturas": {
        "tabla": "facturas", "lineas": "factura_lineas",
        "fk": "factura_id",
        "campos": ["numero", "cliente_id", "obra_id", "presupuesto_id",
                   "fecha", "vencimiento", "estado", "notas"],
    },
    "proformas": {
        "tabla": "proformas", "lineas": "proforma_lineas",
        "fk": "proforma_id",
        "campos": ["numero", "cliente_id", "obra_id", "presupuesto_id",
                   "fecha", "validez", "estado", "notas"],
    },
}


# Series con numeración automática, una por tipo y año: P-2026-087,
# PF-2026-001, F-2026-005...
#
# Las proformas llevan su propia serie (PF) y nunca la de facturas: una
# proforma no es una factura, y si consumiese números de esa serie dejaría
# huecos en una numeración que tiene que ser correlativa.
SERIES = {"presupuestos": "P", "proformas": "PF", "facturas": "F"}

# Estados válidos de cada documento. Un presupuesto no se "rechaza": se
# cancela, y al cancelarlo hay que decir por qué.
ESTADOS = {
    "presupuestos": ("borrador", "enviado", "firmado", "aceptado", "cancelado"),
    "facturas": ("emitida", "cobrada", "anulada"),
    "proformas": ("borrador", "enviada", "aceptada", "facturada", "anulada"),
}

# Series que, además del contador, siguen siempre detrás del número más alto
# que ya exista ese año. Las facturas lo necesitan porque al activar la
# numeración ya había facturas con el número puesto a mano y la serie tiene
# que continuar desde ahí sin repetir ninguno. Los presupuestos no: los suyos
# se numeran desde el contador y punto.
CONTINUAN_DETRAS = {"facturas"}


def _mayor_existente(con, serie: str, anio: int) -> int:
    """El número de secuencia más alto entre los documentos de ese año.

    Se leen las cifras finales del número sea cual sea su formato, así que
    vale para F-2026-004, para 2026/007 o para FAC-12. Se ignora un final que
    sea el propio año: un "F-2026" sin secuencia no puede disparar la serie
    hasta el 2026.
    """
    mayor = 0
    filas = con.execute(
        f"SELECT numero FROM {DOCUMENTOS[serie]['tabla']} "
        "WHERE substr(fecha, 1, 4) = ? AND numero IS NOT NULL", (str(anio),))
    for fila in filas:
        cifras = ""
        for ch in reversed(str(fila[0]).strip()):
            if not ch.isdigit():
                break
            cifras = ch + cifras
        if cifras and not (len(cifras) == 4 and int(cifras) == anio):
            mayor = max(mayor, int(cifras))
    return mayor


def siguiente_numero(con, serie: str, anio: int) -> str:
    """Reserva y devuelve el siguiente número de la serie, tipo P-2026-087.

    Se llama dentro de la transacción que crea el documento: en SQLite las
    escrituras se serializan, así que dos altas simultáneas no pueden llevarse
    el mismo número.
    """
    con.execute("INSERT OR IGNORE INTO contadores (serie, anio, ultimo) VALUES (?,?,0)",
                (serie, anio))
    if serie in CONTINUAN_DETRAS:
        con.execute(
            "UPDATE contadores SET ultimo = MAX(ultimo, ?) WHERE serie = ? AND anio = ?",
            (_mayor_existente(con, serie, anio), serie, anio))
    con.execute("UPDATE contadores SET ultimo = ultimo + 1 WHERE serie = ? AND anio = ?",
                (serie, anio))
    n = con.execute("SELECT ultimo FROM contadores WHERE serie = ? AND anio = ?",
                    (serie, anio)).fetchone()[0]
    return f"{SERIES[serie]}-{anio}-{n:03d}"


class Linea(BaseModel):
    concepto: str
    cantidad: float = 1
    unidad: str = "ud"
    precio: float = 0
    iva: float = 21


class Documento(BaseModel):
    cabecera: dict[str, Any] = {}
    lineas: list[Linea] = []


# El PDF firmado son megas de binario y la firma dibujada, una imagen larga:
# ninguno de los dos tiene por qué viajar en cada listado del panel.
PESADOS = ("firma_pdf", "firma_imagen")


def _aligerar(doc: dict) -> dict:
    for campo in PESADOS:
        doc.pop(campo, None)
    return doc


def _doc(tipo: str):
    d = DOCUMENTOS.get(tipo)
    if not d:
        raise HTTPException(404, "Tipo de documento desconocido")
    return d


# Todo lo que se guarda de una firma. Al archivarla se copia entera a la
# tabla `firmas` y se vacía aquí, enlace incluido.
FIRMA_COLUMNAS = ("firmado_el", "firmante_nombre", "firmante_nif", "firma_ip",
                  "firma_agente", "firma_imagen", "firma_huella", "firma_hash_pdf",
                  "firma_inicio_inmediato", "firma_pdf", "firma_token")


def _archivar_firma(con, doc: dict):
    """Guarda la firma que tenía un presupuesto y lo deja sin firmar.

    Se llama al editarlo. Una firma prueba que el cliente aceptó *ese*
    documento: en cuanto cambian las líneas o el precio, ya no prueba lo que
    hay delante y dejarla puesta sería hacerle decir lo que no dijo. Pero
    tampoco se tira: se guarda entera —con su PDF, sus huellas y su fecha—
    por si hay que enseñar qué se firmó aquel día.

    El enlace de firma se anula con ella: apuntaba a un documento que ya no
    dice lo mismo, y el cliente no puede acabar firmando otra cosa por un
    enlace que le mandaron hace un mes.
    """
    con.execute(
        """INSERT INTO firmas (presupuesto_id, numero, firmado_el, firmante_nombre,
               firmante_nif, ip, agente, imagen, huella, hash_pdf,
               inicio_inmediato, pdf)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (doc["id"], doc.get("numero"), doc.get("firmado_el"), doc.get("firmante_nombre"),
         doc.get("firmante_nif"), doc.get("firma_ip"), doc.get("firma_agente"),
         doc.get("firma_imagen"), doc.get("firma_huella"), doc.get("firma_hash_pdf"),
         doc.get("firma_inicio_inmediato"), doc.get("firma_pdf")))
    con.execute(
        "UPDATE presupuestos SET " + ", ".join(c + " = NULL" for c in FIRMA_COLUMNAS) +
        " WHERE id = ?", (doc["id"],))


def _cancelacion(tipo: str, cab: dict, existente: dict | None = None):
    """Reglas de la cancelación de un presupuesto.

    Cancelar sin motivo deja un documento muerto del que nadie se acuerda por
    qué cayó, que es justo lo que interesa saber al cabo de unos meses. La
    fecha se pone sola y no se pisa si ya estaba cancelado.
    """
    actual = {**(existente or {}), **cab}
    if cab.get("estado") and cab["estado"] not in ESTADOS[tipo]:
        raise HTTPException(422, "Estado de documento desconocido.")
    if tipo != "presupuestos":
        return
    if actual.get("estado") == "cancelado":
        if not str(actual.get("motivo_cancelacion") or "").strip():
            raise HTTPException(422, "Di por qué se cancela el presupuesto.")
        if not actual.get("cancelado_el"):
            cab["cancelado_el"] = date.today().isoformat()
    elif actual.get("estado") and (existente or {}).get("estado") == "cancelado":
        # Vuelve a estar vivo: se borra el rastro de la cancelación anterior.
        cab["motivo_cancelacion"] = None
        cab["cancelado_el"] = None


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
        # El ingreso es de quien lleva la factura: así cada uno ve su parte en
        # su contabilidad.
        datos = (f"Factura {f['numero'] or f['id']}", base, iva_pct, f["fecha"],
                 f["numero"], 1 if f["estado"] == "cobrada" else 0,
                 f["obra_id"], f["cliente_id"], f.get("usuario_id"), factura_id)
        if existente:
            con.execute("""UPDATE ingresos SET concepto=?, importe=?, iva=?,
                           fecha=?, factura_ref=?, cobrado=?, obra_id=?,
                           cliente_id=?, usuario_id=? WHERE factura_id=?""", datos)
        else:
            con.execute("""INSERT INTO ingresos
                           (concepto, importe, iva, fecha, factura_ref, cobrado,
                            obra_id, cliente_id, usuario_id, factura_id)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""", datos)


def _firmas_previas(id_: int) -> int:
    """Firmas archivadas de ese presupuesto: las de antes de editarlo."""
    return db.escalar("SELECT COUNT(*) FROM firmas WHERE presupuesto_id = ?", (id_,))


def _visible(tipo: str, u: dict, id_: int) -> dict:
    """El documento si lo puede ver este usuario; si no, 404.

    404 y no 403: a un miembro no se le confirma siquiera que existe un
    documento de otra persona con ese número.
    """
    d = _doc(tipo)
    cond, params = filtro_responsable(u)
    doc = db.fila(f"SELECT * FROM {d['tabla']} WHERE id = ? AND {cond}", (id_, *params))
    if not doc:
        raise HTTPException(404, "No encontrado")
    return doc


@router.get("/documentos/{tipo}")
def listar(tipo: str, u: dict = Depends(sesion_actual)):
    d = _doc(tipo)
    exigir(u, *d.get("lectura", (tipo,)))
    cond, params = filtro_responsable(u, "x")
    docs = db.filas(f"""
        SELECT x.*, c.nombre AS cliente, o.titulo AS obra
        FROM {d['tabla']} x
        LEFT JOIN clientes c ON c.id = x.cliente_id
        LEFT JOIN obras o ON o.id = x.obra_id
        WHERE {cond}
        ORDER BY x.fecha DESC, x.id DESC
    """, params)
    for doc in docs:
        lineas = db.filas(f"SELECT * FROM {d['lineas']} WHERE {d['fk']} = ?",
                          (doc["id"],))
        doc.update(totales(lineas))
        doc["n_lineas"] = len(lineas)
        if tipo == "presupuestos":
            doc["firmas_previas"] = _firmas_previas(doc["id"])
        _aligerar(doc)
    return docs


@router.get("/documentos/{tipo}/{id_}")
def ver(tipo: str, id_: int, u: dict = Depends(sesion_actual)):
    exigir(u, tipo)
    _visible(tipo, u, id_)
    return _ver(tipo, id_)


def _ver(tipo: str, id_: int) -> dict:
    d = _doc(tipo)
    doc = db.fila(f"SELECT * FROM {d['tabla']} WHERE id = ?", (id_,))
    if not doc:
        raise HTTPException(404, "No encontrado")
    doc["lineas"] = db.filas(
        f"SELECT * FROM {d['lineas']} WHERE {d['fk']} = ? ORDER BY orden, id",
        (id_,))
    doc.update(totales(doc["lineas"]))
    if tipo == "presupuestos":
        doc["firmas_previas"] = _firmas_previas(id_)
    return _aligerar(doc)


def _guardar_lineas(con, d, doc_id, lineas):
    for i, l in enumerate(lineas):
        con.execute(
            f"""INSERT INTO {d['lineas']} ({d['fk']}, concepto, cantidad,
                unidad, precio, iva, orden) VALUES (?,?,?,?,?,?,?)""",
            (doc_id, l.concepto, l.cantidad, l.unidad, l.precio, l.iva, i))


@router.post("/documentos/{tipo}", status_code=201)
def crear(tipo: str, doc: Documento, u: dict = Depends(sesion_actual)):
    d = _doc(tipo)
    exigir(u, tipo)
    cab = {k: v for k, v in doc.cabecera.items() if k in d["campos"] and v is not None}
    # El número lo pone la serie, nunca quien manda la petición: un número
    # elegido a mano puede repetir uno ya emitido o dejar huecos, y una
    # numeración de facturas con huecos o repetidos no se sostiene ante
    # Hacienda. El campo ni siquiera está en el formulario.
    cab.pop("numero", None)
    fijar_responsable(u, doc.cabecera, cab, creando=True)
    comprobar_referencias(u, cab)
    _cancelacion(tipo, cab)
    with db.tx() as con:
        if tipo in SERIES:
            anio = int(str(cab.get("fecha") or date.today().isoformat())[:4])
            cab["numero"] = siguiente_numero(con, tipo, anio)
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
    return _ver(tipo, nuevo)


@router.put("/documentos/{tipo}/{id_}")
def actualizar(tipo: str, id_: int, doc: Documento, u: dict = Depends(sesion_actual)):
    d = _doc(tipo)
    exigir(u, tipo)
    existente = _visible(tipo, u, id_)
    cab = {k: v for k, v in doc.cabecera.items() if k in d["campos"]}
    # El número que tiene puesto se queda como está. Renumerar un documento
    # que ya salió por la puerta lo convierte en otro distinto, y los que se
    # numeraron a mano antes de todo esto conservan el suyo.
    cab.pop("numero", None)
    fijar_responsable(u, doc.cabecera, cab, creando=False)
    comprobar_referencias(u, cab, existente)
    # Editar un presupuesto firmado lo devuelve a borrador: lo que hay delante
    # ya no es lo que firmó el cliente, así que hay que volver a mandárselo.
    # Salvo que lo que se esté haciendo sea cancelarlo, que es una decisión
    # aparte y no se le lleva la contraria.
    firmado = tipo == "presupuestos" and bool(existente.get("firmado_el"))
    if firmado and cab.get("estado") != "cancelado":
        cab["estado"] = "borrador"
    _cancelacion(tipo, cab, existente)
    with db.tx() as con:
        if firmado:
            _archivar_firma(con, existente)
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
    return _ver(tipo, id_)


@router.delete("/documentos/{tipo}/{id_}")
def borrar(tipo: str, id_: int, u: dict = Depends(sesion_actual)):
    d = _doc(tipo)
    exigir(u, tipo)
    existente = _visible(tipo, u, id_)
    if tipo == "presupuestos" and existente.get("firmado_el"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este presupuesto está firmado y no se puede borrar. Cancélalo si ya no sigue adelante.")
    with db.tx() as con:
        if tipo == "facturas":
            con.execute("DELETE FROM ingresos WHERE factura_id = ?", (id_,))
        cur = con.execute(f"DELETE FROM {d['tabla']} WHERE id = ?", (id_,))
        if cur.rowcount == 0:
            raise HTTPException(404, "No encontrado")
    return {"ok": True}


class CambioEstado(BaseModel):
    estado: str
    motivo: str | None = None


@router.post("/documentos/{tipo}/{id_}/estado")
def cambiar_estado(tipo: str, id_: int, datos: CambioEstado,
                   u: dict = Depends(sesion_actual)):
    """Acepta o cancela un documento desde el listado, sin abrir la ficha.

    Solo toca la cabecera: si esto reutilizase el PUT de siempre, que sustituye
    las líneas por las que le manden, aceptar un presupuesto desde la lista se
    llevaría por delante todo su detalle.
    """
    d = _doc(tipo)
    exigir(u, tipo)
    existente = _visible(tipo, u, id_)
    cab = {"estado": datos.estado}
    if tipo == "presupuestos" and datos.estado == "cancelado":
        cab["motivo_cancelacion"] = (datos.motivo or "").strip() or None
    _cancelacion(tipo, cab, existente)
    sets = ", ".join(f"{k} = ?" for k in cab)
    with db.tx() as con:
        con.execute(f"UPDATE {d['tabla']} SET {sets} WHERE id = ?", (*cab.values(), id_))
    if tipo == "facturas":
        sincronizar_ingreso(id_)
    return _ver(tipo, id_)


@router.get("/documentos/{tipo}/{id_}/pdf")
def descargar_pdf(tipo: str, id_: int, u: dict = Depends(sesion_actual)):
    """Presupuesto, proforma o factura en PDF, listo para mandar al cliente."""
    exigir(u, tipo)
    existente = _visible(tipo, u, id_)
    # Si está firmado se devuelve el PDF que se firmó, byte a byte, y no uno
    # generado de nuevo: es el documento que acepta el cliente.
    if tipo == "presupuestos" and existente.get("firma_pdf"):
        numero = (existente.get("numero") or f"presupuesto-{id_}").replace("/", "-")
        return Response(
            content=bytes(existente["firma_pdf"]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{numero}-firmado.pdf"'})
    try:
        from .firma import DIAS_DESISTIMIENTO, condiciones
        datos, nombre = pdf.documento_pdf(
            tipo, id_,
            condiciones_texto=condiciones() if tipo == "presupuestos" else None,
            dias_desistimiento=DIAS_DESISTIMIENTO)
    except pdf.DocumentoIncompleto as e:
        raise HTTPException(422, str(e))
    if datos is None:
        raise HTTPException(404, "El documento no existe")
    return Response(
        content=datos,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


def _copiar(origen: str, id_: int, destino: str, estado_origen: str, u: dict) -> int:
    """Crea un documento `destino` con el cliente, la obra y las líneas de otro.

    Sirve para los tres pasos del circuito: presupuesto → proforma,
    presupuesto → factura y proforma → factura. El enlace con el presupuesto
    se conserva a lo largo de la cadena.
    """
    o, d = _doc(origen), _doc(destino)
    doc = _visible(origen, u, id_)
    lineas = db.filas(
        f"SELECT * FROM {o['lineas']} WHERE {o['fk']} = ? ORDER BY orden, id", (id_,))
    if not lineas:
        raise HTTPException(422, "El documento no tiene líneas que copiar")

    etiqueta = "el presupuesto" if origen == "presupuestos" else "la proforma"
    cab = {
        "cliente_id": doc["cliente_id"],
        "obra_id": doc["obra_id"],
        "presupuesto_id": id_ if origen == "presupuestos" else doc.get("presupuesto_id"),
        "notas": f"Generada desde {etiqueta} {doc['numero'] or doc['id']}",
        # La factura o proforma es de quien llevaba el documento de origen.
        "usuario_id": doc.get("usuario_id"),
    }
    with db.tx() as con:
        if destino in SERIES:
            cab["numero"] = siguiente_numero(con, destino, date.today().year)
        cols = ", ".join(cab)
        nuevo = con.execute(
            f"INSERT INTO {d['tabla']} ({cols}) VALUES ({', '.join('?' * len(cab))})",
            tuple(cab.values())).lastrowid
        for i, l in enumerate(lineas):
            con.execute(
                f"""INSERT INTO {d['lineas']} ({d['fk']}, concepto, cantidad,
                    unidad, precio, iva, orden) VALUES (?,?,?,?,?,?,?)""",
                (nuevo, l["concepto"], l["cantidad"], l["unidad"], l["precio"],
                 l["iva"], i))
        con.execute(f"UPDATE {o['tabla']} SET estado = ? WHERE id = ?",
                    (estado_origen, id_))
    return nuevo


@router.get("/documentos/{tipo}/desde-presupuesto/{id_}")
def desde_presupuesto(tipo: str, id_: int, u: dict = Depends(sesion_actual)):
    """Lo que hay que copiar de un presupuesto para facturarlo.

    No crea nada: devuelve el cliente, la obra, las notas y las líneas para
    que el panel rellene con ellas la factura que se está escribiendo. El que
    factura sigue pudiendo cambiarlo todo y añadir líneas aparte antes de
    guardar, que es lo que no deja el botón «Facturar» del listado.

    Pide el módulo del documento que se está haciendo, no el de presupuestos:
    quien factura tiene que poder traerse lo presupuestado aunque no lleve los
    presupuestos. Eso sí, solo los suyos: los de otra persona del equipo no
    existen para él.
    """
    if tipo not in ("facturas", "proformas"):
        raise HTTPException(404, "Solo se rellenan así las facturas y las proformas")
    exigir(u, tipo)
    p = _visible("presupuestos", u, id_)
    lineas = db.filas(
        "SELECT * FROM presupuesto_lineas WHERE presupuesto_id = ? ORDER BY orden, id",
        (id_,))
    if not lineas:
        raise HTTPException(422, "Ese presupuesto no tiene líneas que copiar")
    return {
        "presupuesto": {"id": p["id"], "numero": p["numero"], "estado": p["estado"]},
        "cabecera": {
            "cliente_id": p["cliente_id"],
            "obra_id": p["obra_id"],
            # Las notas del presupuesto son las condiciones que se hablaron con
            # el cliente; si no puso ninguna, al menos queda de dónde sale.
            "notas": p["notas"] or f"Según el presupuesto {p['numero'] or p['id']}",
        },
        "lineas": [{"concepto": l["concepto"], "cantidad": l["cantidad"],
                    "unidad": l["unidad"], "precio": l["precio"], "iva": l["iva"]}
                   for l in lineas],
    }


@router.post("/documentos/{tipo}/{id_}/facturar", status_code=201)
def facturar(tipo: str, id_: int, u: dict = Depends(sesion_actual)):
    """Presupuesto o proforma → factura, copiando sus líneas."""
    if tipo not in ("presupuestos", "proformas"):
        raise HTTPException(404, "Solo se facturan presupuestos y proformas")
    exigir(u, tipo)
    exigir(u, "facturas")
    nueva = _copiar(tipo, id_, "facturas",
                    "aceptado" if tipo == "presupuestos" else "facturada", u)
    sincronizar_ingreso(nueva)
    return _ver("facturas", nueva)


@router.post("/documentos/presupuestos/{id_}/proforma", status_code=201)
def a_proforma(id_: int, u: dict = Depends(sesion_actual)):
    """Presupuesto aceptado → factura proforma, típicamente para pedir la señal."""
    exigir(u, "presupuestos")
    exigir(u, "proformas")
    nueva = _copiar("presupuestos", id_, "proformas", "aceptado", u)
    return _ver("proformas", nueva)
