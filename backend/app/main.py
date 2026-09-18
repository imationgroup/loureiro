"""Backend del formulario de contacto de loureirosoluciones.es.

Recibe el formulario, valida, aplica rate-limit, guarda la solicitud en la
BD del panel y manda tres correos: la solicitud completa a SUPPORT_EMAIL (con
Reply-To del visitante), un acuse de recibo al visitante y un aviso corto a
AVISO_EMAIL. Además sirve la API del panel de gestión.

Diferencia con el de imationgroup: aquí un fallo de SMTP se devuelve como
error 502 en vez de fingir éxito, para que el front pueda ofrecer el
mailto de respaldo en vez de dejar al visitante creyendo que ha enviado
algo que nunca llegó.
"""

import logging
import os
import smtplib
import time
from collections import deque
from email.message import EmailMessage
from html import escape
from threading import Lock
from typing import Deque, Dict

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

from . import auth, db, empresa
from .admin import router as router_admin, router_crud as router_admin_crud
from .equipo import router as router_equipo
from .estatutos import router as router_estatutos
from .firma import router as router_firma, publico as router_firma_publico
from .documentos import router as router_documentos
from .agenda import router as router_agenda, publico as router_agenda_publico
from .visitas import router as router_visitas
from .listas import router as router_listas

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("loureiro-contact")


def env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


SMTP_HOST = env("SMTP_HOST")
SMTP_PORT = int(env("SMTP_PORT", "587"))
SMTP_USER = env("SMTP_USER")
SMTP_PASSWORD = env("SMTP_PASSWORD")
SMTP_FROM = env("SMTP_FROM", "contacto@loureirosoluciones.es")
SMTP_USE_TLS = env("SMTP_USE_TLS", "true").lower() == "true"
SUPPORT_EMAIL = env("SUPPORT_EMAIL", "contacto@loureirosoluciones.es")

# Direcciones que reciben el aviso corto de "tienes una solicitud pendiente".
# Van en el .env y no aquí porque el repositorio es público, y una dirección
# personal escrita en el código acaba en las listas de spam que rastrean
# GitHub. Admite varias separadas por comas. Vacío = no se avisa.
AVISO_EMAILS = [e.strip() for e in env("AVISO_EMAIL").split(",") if e.strip()]
PANEL_URL = "https://loureirosoluciones.es/admin/#solicitudes"

ALLOWED_ORIGINS = [
    o.strip()
    for o in env(
        "ALLOWED_ORIGINS",
        "https://loureirosoluciones.es,https://www.loureirosoluciones.es,http://localhost:8080",
    ).split(",")
    if o.strip()
]

app = FastAPI(title="Loureiro contact API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    # El panel necesita PUT y DELETE además de POST/GET.
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
def _error_no_previsto(request: Request, exc: Exception):
    """Convierte cualquier excepción en una respuesta JSON.

    Sin esto, una excepción sin capturar sale de la aplicación sin pasar
    por el middleware de CORS, el navegador bloquea la respuesta y el
    panel solo puede decir "Failed to fetch", que no dice nada. Así al
    menos se ve el motivo.
    """
    log.exception("error no previsto en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Error del servidor: {type(exc).__name__}. "
                           "Revisa que los campos obligatorios estén completos."},
    )


@app.exception_handler(RequestValidationError)
async def _datos_no_validos(request: Request, exc: RequestValidationError):
    """Registra qué campo no pasa la validación y responde el 422 de siempre.

    Sin esto, un 422 solo deja en el registro la línea de acceso y no hay forma
    de saber qué falló: pasó con el formulario, que la web tapaba con un error
    genérico. Se registran el campo y el tipo de error, nunca el valor, que es
    lo que ha escrito el visitante.
    """
    fallos = ", ".join(
        f"{'.'.join(str(p) for p in e.get('loc', ())[1:]) or '?'}({e.get('type')})"
        for e in exc.errors())
    log.info("[validación] %s %s: %s", request.method, request.url.path, fallos)
    return await request_validation_exception_handler(request, exc)


@app.on_event("startup")
def _arranque():
    db.inicializar()
    auth.sembrar_admin()
    log.info("base de datos lista en %s", db.RUTA_DB)


# El router del CRUD genérico va DESPUÉS: su /{recurso} es un comodín que
# se tragaría rutas concretas como /api/admin/dashboard.
app.include_router(router_admin)
app.include_router(router_equipo)
app.include_router(router_estatutos)
app.include_router(router_firma)
app.include_router(router_firma_publico)
app.include_router(router_documentos)
# La agenda también antes del CRUD: /api/admin/{recurso} se tragaría
# /api/admin/agenda como si fuese una tabla.
app.include_router(router_agenda)
app.include_router(router_agenda_publico)
app.include_router(router_visitas)
app.include_router(router_listas)
app.include_router(router_admin_crud)


@app.get("/api/empresa")
def datos_empresa():
    """NIF para el aviso legal y la política de privacidad.

    Esas páginas son HTML estático y no pueden leer el .env; lo piden aquí
    para que el dato salga del mismo sitio que en los PDF. Es un dato
    público por ley (art. 10 LSSI-CE), así que no lleva sesión.
    """
    return {"nif": empresa.NIF}


@app.get("/api/health")
def health():
    return {"status": "ok", "smtp_configured": bool(SMTP_HOST)}


# ── Rate limit naïve (1 worker uvicorn es suficiente) ─────────────────────────
_RATE_WINDOW = 60 * 60   # 1 hora
_RATE_MAX = 5            # 5 envíos por IP/hora
_BUCKETS: Dict[str, Deque[float]] = {}
_LOCK = Lock()


def _allow(ip: str) -> bool:
    now = time.time()
    with _LOCK:
        bucket = _BUCKETS.setdefault(ip, deque())
        while bucket and bucket[0] < now - _RATE_WINDOW:
            bucket.popleft()
        if len(bucket) >= _RATE_MAX:
            return False
        bucket.append(now)
        return True


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Límite de acuses por destinatario ─────────────────────────────────────────
# El acuse de recibo va a la dirección que escriba quien rellena el formulario,
# sin verificarla. Sin límite, cualquiera podría usar el formulario para mandar
# correos desde nuestro dominio a una víctima, con el texto que quiera dentro,
# y hundir la reputación del dominio. El límite por IP no basta: se esquiva
# cambiando de IP. Este es por dirección de destino.
_ACUSE_VENTANA = 24 * 60 * 60   # 24 horas
_ACUSE_MAX = 2                  # 2 acuses por dirección y día
_ACUSES: Dict[str, Deque[float]] = {}


def _permitir_acuse(email: str) -> bool:
    now = time.time()
    clave = email.strip().lower()
    with _LOCK:
        cola = _ACUSES.setdefault(clave, deque())
        while cola and cola[0] < now - _ACUSE_VENTANA:
            cola.popleft()
        if len(cola) >= _ACUSE_MAX:
            return False
        cola.append(now)
        return True


def send_email(to: str | list[str], subject: str, body: str,
               reply_to: str | None = None, html: str | None = None,
               cabeceras: dict[str, str] | None = None,
               adjuntos: list[tuple[str, bytes]] | None = None) -> bool:
    if not SMTP_HOST:
        log.warning("SMTP no configurado; correo NO enviado. to=%s subject=%r", to, subject)
        log.info("body: %s", body)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to if isinstance(to, str) else ", ".join(to)
    if reply_to:
        msg["Reply-To"] = reply_to
    for clave, valor in (cabeceras or {}).items():
        msg[clave] = valor
    # Siempre quoted-printable, nunca 8bit. Raiola firma con DKIM al recibir el
    # correo y luego lo reenvía por sus relays; con un cuerpo en 8bit algún
    # salto lo recodifica, la firma deja de cuadrar y Gmail lo rechaza
    # ("DKIM = did not pass"). Pasaba con el aviso, que es texto corto con
    # tildes y Python lo mandaba en 8bit, y no con el acuse, que ya salía en
    # quoted-printable por tener líneas largas. En quoted-printable el cuerpo
    # es ASCII puro y nadie tiene motivo para tocarlo.
    msg.set_content(body, cte="quoted-printable")
    if html:
        # Texto plano y HTML a la vez: el cliente de correo elige. Hay quien
        # lee sin HTML, y un correo solo HTML puntúa peor en los filtros.
        msg.add_alternative(html, subtype="html", cte="quoted-printable")

    # Adjuntos (hoy solo el presupuesto firmado en PDF).
    for nombre, datos in (adjuntos or []):
        msg.add_attachment(datos, maintype="application", subtype="pdf", filename=nombre)

    try:
        if SMTP_USE_TLS:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
                s.starttls()
                if SMTP_USER:
                    s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg)
        else:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as s:
                if SMTP_USER:
                    s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg)
        log.info("email enviado to=%s subject=%r", to, subject)
        return True
    except Exception as e:  # noqa: BLE001
        log.exception("error enviando correo a %s: %s", to, e)
        return False


# ── Correos que salen tras una solicitud ──────────────────────────────────────

def _acuse(nombre: str, telefono: str, servicio: str, mensaje: str) -> tuple[str, str, str]:
    """Acuse de recibo para quien rellena el formulario: (asunto, texto, html).

    Todo lo que escribió el visitante se escapa antes de meterlo en el HTML:
    si no, un mensaje con etiquetas se pintaría como parte del correo.
    """
    asunto = "Hemos recibido tu solicitud · Loureiro Soluciones"
    citado = "\n".join("> " + l for l in mensaje.splitlines()) or "> (sin mensaje)"
    texto = (
        f"Hola {nombre},\n\n"
        "Gracias por escribirnos. Hemos recibido tu solicitud y la atenderemos "
        "lo antes posible.\n\n"
        "Esto es lo que nos has enviado:\n\n"
        f"Servicio: {servicio}\n"
        f"Teléfono: {telefono}\n\n"
        f"{citado}\n\n"
        "Si quieres añadir algo, responde a este correo o llámanos al 603 905 128.\n\n"
        "Un saludo,\n"
        "Loureiro Soluciones\n"
        "Reformas y mantenimiento del hogar en Ourense\n"
        "https://loureirosoluciones.es\n"
    )
    n, s, t = escape(nombre), escape(servicio), escape(telefono)
    m = escape(mensaje).replace("\n", "<br>")
    # Maquetación con tablas y estilos en línea: es lo único que respetan
    # Gmail, Outlook y compañía. Sin imágenes, que muchos clientes bloquean.
    # El charset va también dentro del HTML: la cabecera MIME ya lo declara,
    # pero hay webmails y reenvíos que la pierden y los acentos salen rotos.
    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Hemos recibido tu solicitud</title></head><body style="margin:0;padding:0;background:#F4F5F7">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F4F5F7;padding:24px 12px">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#FFFFFF;border-radius:12px;overflow:hidden;font-family:Arial,Helvetica,sans-serif;color:#22252B">
  <tr><td style="background:#14161A;padding:20px 28px">
    <span style="font-size:19px;font-weight:bold;color:#FFFFFF">Loureiro</span><span style="font-size:19px;color:#9AA0AA">soluciones</span>
  </td></tr>
  <tr><td style="padding:28px 28px 8px">
    <p style="margin:0 0 14px;font-size:21px;font-weight:bold;color:#14161A">Hola {n},</p>
    <p style="margin:0 0 14px;font-size:15px;line-height:1.6">Gracias por escribirnos. Hemos recibido tu solicitud y <b>la atenderemos lo antes posible</b>.</p>
    <p style="margin:24px 0 8px;font-size:12px;font-weight:bold;letter-spacing:.06em;text-transform:uppercase;color:#6C7079">Esto es lo que nos has enviado</p>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F6F7F9;border-left:3px solid #F97316;border-radius:6px">
      <tr><td style="padding:14px 16px;font-size:14px;line-height:1.6;color:#22252B">
        <b>Servicio:</b> {s}<br>
        <b>Teléfono:</b> {t}<br><br>
        {m}
      </td></tr>
    </table>
    <p style="margin:24px 0 0;font-size:15px;line-height:1.6">Si quieres añadir algo, responde a este correo o llámanos al <a href="tel:+34603905128" style="color:#F97316;font-weight:bold;text-decoration:none">603&nbsp;905&nbsp;128</a>.</p>
    <p style="margin:22px 0 20px;font-size:15px;line-height:1.6">Un saludo,<br><b>Loureiro Soluciones</b></p>
  </td></tr>
  <tr><td style="padding:16px 28px;border-top:1px solid #E2E4E8;font-size:12px;color:#6C7079;line-height:1.5">
    Reformas y mantenimiento del hogar en Ourense · <a href="https://loureirosoluciones.es" style="color:#6C7079">loureirosoluciones.es</a><br>
    Recibes este correo porque has enviado una solicitud desde nuestra web.
  </td></tr>
</table>
</td></tr></table>
</body></html>"""
    return asunto, texto, html


def _aviso(servicio: str, pendientes: int, solicitud_id: int | None = None) -> tuple[str, str]:
    """Aviso corto para el dueño: que hay trabajo, sin los datos del cliente.

    No lleva nombre, teléfono ni mensaje a propósito: va a una cuenta personal
    fuera del correo de la empresa, y la política de privacidad no contempla
    ceder ahí los datos de los clientes. Para verlos está el enlace al panel.
    """
    if pendientes <= 1:
        estado = "Es la única pendiente de atender."
    else:
        estado = f"Ahora mismo tienes {pendientes} solicitudes pendientes de atender."
    # Asunto distinto en cada aviso. Con uno fijo, Gmail mete todos en la misma
    # conversación y el nuevo pasa desapercibido dentro del hilo de los viejos:
    # parecía que no llegaba. El número de solicitud lo hace único sin meter
    # datos del cliente.
    if solicitud_id:
        asunto = f"Solicitud pendiente #{solicitud_id} en Loureiro: {servicio}"
    else:
        asunto = ("Tienes una solicitud pendiente en Loureiro" if pendientes <= 1
                  else f"Tienes {pendientes} solicitudes pendientes en Loureiro")
    texto = (
        f"Ha llegado una solicitud nueva desde la web: {servicio}.\n\n"
        f"{estado}\n\n"
        f"Atiéndela en el panel: {PANEL_URL}\n"
    )
    return asunto, texto


def _correos_tras_solicitud(nombre: str, email: str, telefono: str, servicio: str,
                            mensaje: str, guardada: bool,
                            solicitud_id: int | None = None) -> None:
    """Acuse al visitante y aviso al dueño.

    Se ejecuta en segundo plano, después de contestar al formulario: cada envío
    SMTP tarda uno o dos segundos y el visitante no tiene por qué esperarlos.
    Si alguno falla se registra y ya está: la solicitud está guardada y el
    correo principal ya ha salido.
    """
    if _permitir_acuse(email):
        asunto, texto, html = _acuse(nombre, telefono, servicio, mensaje)
        send_email(to=email, subject=asunto, body=texto, html=html,
                   reply_to=SUPPORT_EMAIL,
                   # RFC 3834: marca el correo como respuesta automática, para
                   # que el contestador automático del otro lado (un «estoy de
                   # vacaciones») no responda y se forme un bucle.
                   cabeceras={"Auto-Submitted": "auto-replied"})
    else:
        log.warning("[contact] acuse NO enviado a %s: límite diario alcanzado", email)

    # Solo si la solicitud quedó guardada: el aviso dice que está en el panel.
    if AVISO_EMAILS and guardada:
        pendientes = db.escalar("SELECT COUNT(*) FROM solicitudes WHERE estado = 'pendiente'")
        asunto, texto = _aviso(servicio, pendientes, solicitud_id)
        send_email(to=AVISO_EMAILS, subject=asunto, body=texto)


class ContactPayload(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    message: str = Field(min_length=4, max_length=4000)
    phone: str | None = Field(default=None, max_length=30)
    service: str | None = Field(default=None, max_length=80)
    # Honeypot — humanos no rellenan, los bots sí.
    website: str | None = None


class ContactResponse(BaseModel):
    sent: bool


@app.post("/api/contact", response_model=ContactResponse)
def contact(payload: ContactPayload, request: Request, tareas: BackgroundTasks):
    ip = _client_ip(request)

    if payload.website:
        log.info("[contact] honeypot rellenado, ignorando (ip=%s)", ip)
        return ContactResponse(sent=True)

    if not _allow(ip):
        log.warning("[contact] rate-limit alcanzado para ip=%s", ip)
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Has enviado demasiados mensajes. Inténtalo más tarde.",
        )

    name = payload.name.strip()
    sender_email = payload.email.strip()
    service = (payload.service or "Sin especificar").strip()
    phone = (payload.phone or "").strip() or "No facilitado"

    body = (
        "Nueva solicitud desde el formulario de loureirosoluciones.es\n\n"
        f"Nombre:   {name}\n"
        f"Email:    {sender_email}\n"
        f"Teléfono: {phone}\n"
        f"Servicio: {service}\n"
        f"IP:       {ip}\n\n"
        "Mensaje:\n"
        "---------\n"
        f"{payload.message.strip()}\n"
    )
    subject = f"[Presupuesto] {service} — {name}"

    # Se guarda antes de enviar: si el correo falla, el aviso no se pierde
    # y queda en el panel para atenderlo igualmente.
    guardada = False
    solicitud_id = None
    try:
        with db.tx() as con:
            solicitud_id = con.execute(
                # El estado va explícito: en la base de producción la columna se
                # creó con DEFAULT 'nueva', y SQLite no deja cambiar un valor por
                # defecto sin rehacer la tabla entera.
                """INSERT INTO solicitudes (nombre, email, telefono, servicio, mensaje, ip, estado)
                   VALUES (?,?,?,?,?,?,'pendiente')""",
                (name, sender_email, phone if phone != "No facilitado" else None,
                 service, payload.message.strip(), ip),
            ).lastrowid
        guardada = True
    except Exception:  # noqa: BLE001
        log.exception("[contact] no se pudo guardar la solicitud en la BD")

    ok = send_email(to=SUPPORT_EMAIL, subject=subject, body=body, reply_to=sender_email)
    if not ok:
        # No fingimos éxito: el front enseña el mailto de respaldo.
        log.error("[contact] send_email falló (ip=%s, from=%s)", ip, sender_email)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "No se ha podido enviar el mensaje. Escríbenos directamente por correo.",
        )

    # Acuse al visitante y aviso al dueño, después de responder. Solo si el
    # correo principal ha salido: si no, al visitante se le acaba de decir que
    # escriba por correo, y un acuse de recibo lo confundiría.
    tareas.add_task(_correos_tras_solicitud, name, sender_email, phone, service,
                    payload.message.strip(), guardada, solicitud_id)
    return ContactResponse(sent=True)
