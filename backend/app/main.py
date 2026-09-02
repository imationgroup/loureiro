"""Backend del formulario de contacto de loureirosoluciones.com.

Mismo patrón que imationgroup/web: FastAPI + SMTP via smtplib. Sin BD y sin
auth — recibe el formulario, valida, aplica rate-limit y manda un correo a
SUPPORT_EMAIL con Reply-To del visitante.

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
from threading import Lock
from typing import Deque, Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("loureiro-contact")


def env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


SMTP_HOST = env("SMTP_HOST")
SMTP_PORT = int(env("SMTP_PORT", "587"))
SMTP_USER = env("SMTP_USER")
SMTP_PASSWORD = env("SMTP_PASSWORD")
SMTP_FROM = env("SMTP_FROM", "info@loureirosoluciones.com")
SMTP_USE_TLS = env("SMTP_USE_TLS", "true").lower() == "true"
SUPPORT_EMAIL = env("SUPPORT_EMAIL", "info@loureirosoluciones.com")

ALLOWED_ORIGINS = [
    o.strip()
    for o in env(
        "ALLOWED_ORIGINS",
        "https://loureirosoluciones.com,https://www.loureirosoluciones.com,http://localhost:8080",
    ).split(",")
    if o.strip()
]

app = FastAPI(title="Loureiro contact API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


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


def send_email(to: str, subject: str, body: str, reply_to: str | None = None) -> bool:
    if not SMTP_HOST:
        log.warning("SMTP no configurado; correo NO enviado. to=%s subject=%r", to, subject)
        log.info("body: %s", body)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)

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
def contact(payload: ContactPayload, request: Request):
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
        "Nueva solicitud desde el formulario de loureirosoluciones.com\n\n"
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

    ok = send_email(to=SUPPORT_EMAIL, subject=subject, body=body, reply_to=sender_email)
    if not ok:
        # No fingimos éxito: el front enseña el mailto de respaldo.
        log.error("[contact] send_email falló (ip=%s, from=%s)", ip, sender_email)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "No se ha podido enviar el mensaje. Escríbenos directamente por correo.",
        )

    return ContactResponse(sent=True)
