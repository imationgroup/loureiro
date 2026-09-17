"""Firma del presupuesto por el cliente.

Cómo funciona
-------------
1. Desde el panel se manda el presupuesto a firmar. Se genera un enlace
   privado con un token largo y se envía al correo del cliente.
2. El cliente abre el enlace en el móvil, lee el presupuesto y las
   condiciones, marca las casillas y firma con el dedo.
3. Al firmar se guarda el PDF **tal como lo firmó** junto con las pruebas:
   nombre y NIF que escribió, fecha y hora, IP, navegador, la imagen de la
   firma y la huella del documento. A partir de ahí el presupuesto queda
   bloqueado: se puede cancelar, pero no cambiar.

Validez
-------
La firma electrónica simple es válida (Reglamento eIDAS 910/2014, art. 25).
Lo que decide su peso ante un juez es la prueba que la acompaña, que es
justo lo que se guarda aquí.

Con un cliente particular el contrato firmado fuera del establecimiento o a
distancia lleva **14 días naturales de desistimiento** que no se pueden
quitar por contrato (RDL 1/2007, arts. 102 y ss.). Por eso la página de
firma informa de ese derecho y ofrece la casilla de **solicitud expresa de
inicio inmediato**: si el cliente la marca y luego desiste, debe abonar lo
ya ejecutado y los gastos en que se haya incurrido (art. 108.3). Sin esa
casilla marcada, desistir dentro de plazo no cuesta nada, y por eso se
guarda si la marcó o no.
"""

import hashlib
import logging
import os
import secrets
from datetime import datetime, timezone
from html import escape

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from . import db, empresa, pdf
from .auth import es_admin, exigir, exigir_admin, filtro_responsable, sesion_actual

log = logging.getLogger("loureiro-firma")

router = APIRouter(prefix="/api/admin", tags=["firma"])
publico = APIRouter(prefix="/api", tags=["firma"])

WEB = (os.getenv("WEB_PUBLICA") or "https://loureirosoluciones.es").rstrip("/")
DIAS_DESISTIMIENTO = 14

CLAVE_CONDICIONES = "condiciones_presupuesto"

# Texto de partida. El administrador lo puede cambiar entero desde el panel;
# esto solo evita que el primer presupuesto salga sin condiciones.
CONDICIONES_POR_DEFECTO = """Aceptación del presupuesto
Al firmar este presupuesto el cliente acepta su contenido, el importe y los trabajos descritos, y encarga su ejecución a Loureiro Soluciones.

Forma de pago
Salvo pacto distinto por escrito, se abona el 50 % al inicio de los trabajos y el 50 % restante a su finalización. En obras divididas en hitos, se abona cada hito al completarse.

Cancelación una vez firmado
Si el cliente cancela el encargo después de firmar, abonará los trabajos ya ejecutados y los gastos justificados en que se haya incurrido: materiales pedidos o cortados a medida, jornadas de trabajo reservadas, maquinaria alquilada y gestiones realizadas. Se entregará el detalle de esos gastos con su justificación.

Plazos
Las fechas de inicio y finalización se acuerdan por escrito y pueden verse afectadas por causas ajenas a la empresa: suministros, licencias, climatología o hallazgos no visibles al presupuestar. Cualquier trabajo no incluido en este presupuesto se presupuestará aparte antes de ejecutarlo."""


def _ahora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "desconocida"


# ── Condiciones de contratación ──────────────────────────────────────────

def condiciones() -> str:
    fila = db.fila("SELECT valor FROM ajustes WHERE clave = ?", (CLAVE_CONDICIONES,))
    if fila and (fila["valor"] or "").strip():
        return fila["valor"]
    return CONDICIONES_POR_DEFECTO


class Condiciones(BaseModel):
    texto: str = Field(max_length=20000)


@router.get("/condiciones")
def ver_condiciones(_: dict = Depends(sesion_actual)):
    return {"texto": condiciones(), "por_defecto": CONDICIONES_POR_DEFECTO}


@router.put("/condiciones")
def guardar_condiciones(datos: Condiciones, u: dict = Depends(sesion_actual)):
    exigir_admin(u)
    with db.tx() as con:
        con.execute("INSERT INTO ajustes (clave, valor) VALUES (?, ?) "
                    "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
                    (CLAVE_CONDICIONES, datos.texto.strip()))
    return {"texto": condiciones()}


# ── Enviar a firmar ──────────────────────────────────────────────────────

def _presupuesto(id_: int, u: dict) -> dict:
    cond, params = filtro_responsable(u)
    doc = db.fila(f"SELECT * FROM presupuestos WHERE id = ? AND {cond}", (id_, *params))
    if not doc:
        raise HTTPException(404, "No encontrado")
    return doc


def _enlace(token: str) -> str:
    return f"{WEB}/firmar/#{token}"


def _correo_firma(doc: dict, cliente: dict, enlace: str) -> bool:
    from .main import send_email   # import tardío: main importa este módulo

    numero = doc["numero"] or f"#{doc['id']}"
    nombre = (cliente.get("nombre") or "").split(" ")[0] if cliente else ""
    texto = (f"Hola{(' ' + nombre) if nombre else ''},\n\n"
             f"Te enviamos el presupuesto {numero} de Loureiro Soluciones para que lo revises.\n\n"
             "Puedes leerlo y, si estás de acuerdo, firmarlo desde el móvil en este enlace:\n"
             f"{enlace}\n\n"
             "El enlace es personal: no lo compartas. Si prefieres comentarlo antes, "
             "responde a este correo o llámanos al 603 905 128.\n\n"
             "Un saludo,\nLoureiro Soluciones\n")
    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Presupuesto {escape(numero)}</title></head><body style="margin:0;padding:0;background:#F4F5F7">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F4F5F7;padding:24px 12px"><tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#FFFFFF;border-radius:12px;overflow:hidden;font-family:Arial,Helvetica,sans-serif;color:#22252B">
  <tr><td style="background:#14161A;padding:20px 28px"><span style="font-size:19px;font-weight:bold;color:#FFFFFF">Loureiro</span><span style="font-size:19px;color:#9AA0AA">soluciones</span></td></tr>
  <tr><td style="padding:28px">
    <p style="margin:0 0 14px;font-size:20px;font-weight:bold;color:#14161A">Hola{(' ' + escape(nombre)) if nombre else ''},</p>
    <p style="margin:0 0 14px;font-size:15px;line-height:1.6">Aquí tienes el presupuesto <b>{escape(numero)}</b>. Puedes leerlo entero y, si estás de acuerdo, firmarlo desde el móvil.</p>
    <p style="margin:24px 0"><a href="{escape(enlace)}" style="display:inline-block;background:#F97316;color:#FFFFFF;font-weight:bold;font-size:15px;text-decoration:none;padding:13px 24px;border-radius:999px">Ver y firmar el presupuesto</a></p>
    <p style="margin:0;font-size:13px;line-height:1.6;color:#6C7079">El enlace es personal, no lo compartas. ¿Dudas? Responde a este correo o llámanos al 603 905 128.</p>
  </td></tr>
</table></td></tr></table></body></html>"""
    return send_email(to=cliente["email"], subject=f"Tu presupuesto {numero} · Loureiro Soluciones",
                      body=texto, html=html)


@router.post("/documentos/presupuestos/{id_}/enviar-firma")
def enviar_a_firmar(id_: int, u: dict = Depends(sesion_actual)):
    """Genera el enlace de firma y se lo manda al cliente por correo."""
    exigir(u, "presupuestos")
    doc = _presupuesto(id_, u)
    if doc.get("firmado_el"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Este presupuesto ya está firmado.")
    if not db.escalar("SELECT COUNT(*) FROM presupuesto_lineas WHERE presupuesto_id = ?", (id_,)):
        raise HTTPException(422, "El presupuesto no tiene líneas: no hay nada que firmar.")

    token = doc.get("firma_token") or secrets.token_urlsafe(32)
    with db.tx() as con:
        con.execute("UPDATE presupuestos SET firma_token = ?, estado = CASE WHEN estado = 'borrador' "
                    "THEN 'enviado' ELSE estado END WHERE id = ?", (token, id_))
    enlace = _enlace(token)

    cliente = db.fila("SELECT * FROM clientes WHERE id = ?", (doc["cliente_id"],)) \
        if doc["cliente_id"] else None
    if not (cliente and (cliente.get("email") or "").strip()):
        # Sin correo no se puede mandar, pero el enlace vale igual por WhatsApp.
        return {"enviado": False, "enlace": enlace,
                "motivo": "El cliente no tiene correo en su ficha."}
    enviado = _correo_firma(doc, cliente, enlace)
    return {"enviado": enviado, "enlace": None if enviado else enlace,
            "motivo": None if enviado else "No se ha podido enviar el correo.",
            "email": cliente["email"]}


@router.get("/documentos/presupuestos/{id_}/firma")
def ver_firma(id_: int, u: dict = Depends(sesion_actual)):
    """Las pruebas de la firma, para enseñarlas en el panel."""
    exigir(u, "presupuestos")
    doc = _presupuesto(id_, u)
    return {
        "firmado_el": doc.get("firmado_el"),
        "firmante_nombre": doc.get("firmante_nombre"),
        "firmante_nif": doc.get("firmante_nif"),
        "ip": doc.get("firma_ip"),
        "agente": doc.get("firma_agente"),
        "imagen": doc.get("firma_imagen"),
        "huella": doc.get("firma_huella"),
        "hash_pdf": doc.get("firma_hash_pdf"),
        "inicio_inmediato": bool(doc.get("firma_inicio_inmediato")),
        "enlace": _enlace(doc["firma_token"]) if doc.get("firma_token") else None,
        # Las de antes de editarlo. Se quedan guardadas para poder enseñar qué
        # aceptó el cliente en su día, aunque el presupuesto ya diga otra cosa.
        "anteriores": db.filas(
            """SELECT id, numero, firmado_el, firmante_nombre, firmante_nif,
                      huella, hash_pdf, inicio_inmediato, anulada_el
               FROM firmas WHERE presupuesto_id = ? ORDER BY id DESC""", (id_,)),
    }


@router.get("/documentos/presupuestos/{id_}/firmas/{firma_id}/pdf")
def pdf_firma_archivada(id_: int, firma_id: int, u: dict = Depends(sesion_actual)):
    """El PDF de una firma que dejó de valer, tal como se firmó."""
    exigir(u, "presupuestos")
    _presupuesto(id_, u)
    f = db.fila("SELECT numero, pdf FROM firmas WHERE id = ? AND presupuesto_id = ?",
                (firma_id, id_))
    if not (f and f["pdf"]):
        raise HTTPException(404, "No hay PDF guardado de esa firma")
    nombre = (f["numero"] or f"presupuesto-{id_}").replace("/", "-")
    return Response(
        content=bytes(f["pdf"]), media_type="application/pdf",
        headers={"Content-Disposition":
                 f'attachment; filename="{nombre}-firmado-{firma_id}.pdf"'})


# ── Lo que ve y hace el cliente (sin sesión, lo protege el token) ────────

class Token(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class Firma(Token):
    nombre: str = Field(min_length=3, max_length=120)
    nif: str = Field(default="", max_length=20)
    imagen: str = Field(min_length=100, max_length=400000)   # data URL del PNG
    acepta: bool = False
    inicio_inmediato: bool = False


def _por_token(token: str) -> dict:
    doc = db.fila("SELECT * FROM presupuestos WHERE firma_token = ?", (token,)) if token else None
    if not doc:
        raise HTTPException(404, "Este enlace no es válido. Pide uno nuevo.")
    return doc


def _huella(doc: dict, lineas: list[dict]) -> str:
    """Huella del contenido firmado: si algo cambiase, deja de cuadrar."""
    partes = [str(doc.get("numero") or doc["id"]), str(doc.get("fecha") or ""),
              str(doc.get("cliente_id") or "")]
    for l in lineas:
        partes.append(f"{l['concepto']}|{l['cantidad']}|{l['unidad']}|{l['precio']}|{l['iva']}")
    partes.append(condiciones())
    return hashlib.sha256("\n".join(partes).encode("utf-8")).hexdigest()


def _datos_publicos(doc: dict) -> dict:
    lineas = db.filas("SELECT * FROM presupuesto_lineas WHERE presupuesto_id = ? ORDER BY orden, id",
                      (doc["id"],))
    cliente = db.fila("SELECT nombre, nif, direccion, cp, ciudad, provincia FROM clientes WHERE id = ?",
                      (doc["cliente_id"],)) if doc["cliente_id"] else None
    from .documentos import totales
    return {
        "numero": doc.get("numero") or f"#{doc['id']}",
        "fecha": doc.get("fecha"),
        "validez": doc.get("validez"),
        "notas": doc.get("notas"),
        "estado": doc.get("estado"),
        "cliente": cliente,
        "lineas": [{"concepto": l["concepto"], "cantidad": l["cantidad"], "unidad": l["unidad"],
                    "precio": l["precio"], "iva": l["iva"]} for l in lineas],
        "totales": totales(lineas),
        "condiciones": condiciones(),
        "dias_desistimiento": DIAS_DESISTIMIENTO,
        "empresa": {k: empresa.EMPRESA[k] for k in ("nombre", "nif", "direccion", "telefono", "email")},
        "firmado_el": doc.get("firmado_el"),
        "firmante_nombre": doc.get("firmante_nombre"),
    }


@publico.post("/firma/ver")
def ver(datos: Token):
    """El presupuesto que hay detrás del enlace. POST para que el token no
    quede escrito en los registros del servidor web."""
    return _datos_publicos(_por_token(datos.token))


@publico.post("/firma")
def firmar(datos: Firma, request: Request):
    doc = _por_token(datos.token)
    if doc.get("firmado_el"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Este presupuesto ya está firmado.")
    if doc.get("estado") == "cancelado":
        raise HTTPException(status.HTTP_409_CONFLICT, "Este presupuesto está cancelado.")
    if not datos.acepta:
        raise HTTPException(422, "Hay que aceptar el presupuesto y las condiciones para firmar.")
    if not datos.imagen.startswith("data:image/png;base64,"):
        raise HTTPException(422, "La firma no se ha recogido bien. Vuelve a intentarlo.")

    lineas = db.filas("SELECT * FROM presupuesto_lineas WHERE presupuesto_id = ? ORDER BY orden, id",
                      (doc["id"],))
    if not lineas:
        raise HTTPException(422, "El presupuesto no tiene líneas.")

    firma = {
        "firmado_el": _ahora(),
        "firmante_nombre": datos.nombre.strip(),
        "firmante_nif": datos.nif.strip() or None,
        "firma_ip": _ip(request),
        "firma_agente": (request.headers.get("user-agent") or "")[:300],
        "firma_imagen": datos.imagen,
        "firma_huella": _huella(doc, lineas),
        "firma_inicio_inmediato": 1 if datos.inicio_inmediato else 0,
    }
    datos_pdf, _ = pdf.documento_pdf("presupuestos", doc["id"], firma=firma,
                                     condiciones_texto=condiciones())
    firma["firma_pdf"] = datos_pdf
    firma["firma_hash_pdf"] = hashlib.sha256(datos_pdf).hexdigest()

    sets = ", ".join(f"{k} = ?" for k in firma)
    with db.tx() as con:
        con.execute(f"UPDATE presupuestos SET {sets}, estado = 'firmado' WHERE id = ?",
                    (*firma.values(), doc["id"]))
    log.info("[firma] presupuesto %s firmado por %s desde %s",
             doc.get("numero") or doc["id"], firma["firmante_nombre"], firma["firma_ip"])

    _avisar_firmado(doc, firma, datos_pdf)
    return {"ok": True, "numero": doc.get("numero") or f"#{doc['id']}"}


def _avisar_firmado(doc: dict, firma: dict, datos_pdf: bytes):
    """Copia al cliente y aviso a la empresa. Si falla, la firma ya está hecha."""
    from .main import AVISO_EMAILS, SUPPORT_EMAIL, send_email

    numero = doc.get("numero") or f"#{doc['id']}"
    cliente = db.fila("SELECT nombre, email FROM clientes WHERE id = ?", (doc["cliente_id"],)) \
        if doc["cliente_id"] else None
    try:
        if cliente and (cliente.get("email") or "").strip():
            send_email(
                to=cliente["email"],
                subject=f"Presupuesto {numero} firmado · Loureiro Soluciones",
                body=("Gracias por firmar el presupuesto " + numero + ".\n\n"
                      "Guardamos una copia firmada con la fecha y hora de la firma. "
                      "Nos pondremos en contacto para concretar las fechas de los trabajos.\n\n"
                      "Si tienes cualquier duda, responde a este correo o llámanos al 603 905 128.\n\n"
                      "Un saludo,\nLoureiro Soluciones\n"),
                adjuntos=[(f"{numero}-firmado.pdf", datos_pdf)])
        destinos = AVISO_EMAILS or [SUPPORT_EMAIL]
        send_email(to=destinos, subject=f"Presupuesto {numero} firmado",
                   body=(f"El presupuesto {numero} acaba de firmarse.\n\n"
                         f"Firmante: {firma['firmante_nombre']}\n"
                         f"Fecha (UTC): {firma['firmado_el']}\n\n"
                         f"Panel: {WEB}/admin/#presupuestos\n"))
    except Exception:       # noqa: BLE001
        log.exception("[firma] fallo al avisar de la firma del presupuesto %s", numero)
