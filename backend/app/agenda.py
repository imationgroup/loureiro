"""Agenda del panel: citas de los profesionales con los clientes.

Dos partes:

- La API del panel (con sesión): las citas de un rango de fechas con los
  nombres ya resueltos, la dirección que toca y un aviso cuando un profesional
  tiene dos citas a la vez.
- La suscripción para Google Calendar (sin sesión, con un enlace secreto): un
  fichero iCalendar (.ics) que Google vuelve a leer cada pocas horas. Es la
  forma de verla en Google sin conectar la cuenta de Google con permisos, y por
  eso solo va del panel a Google, no al revés.

Las horas se guardan como hora local de Ourense y sin zona ("2026-09-15T10:00"),
que es como las da el campo datetime-local del navegador. En el .ics van con
TZID=Europe/Madrid y su VTIMEZONE, así que Google las coloca bien también en
los cambios de hora de marzo y octubre sin que el servidor tenga que convertir
nada ni depender de la base de zonas horarias del sistema.
"""

import os
import secrets
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from . import db
from .auth import es_admin, exigir, puede, sesion_actual

router = APIRouter(prefix="/api/admin", tags=["agenda"])
publico = APIRouter(prefix="/api", tags=["agenda"])

API_PUBLICA = (os.getenv("API_PUBLICA") or "https://api.loureirosoluciones.es").rstrip("/")
PANEL_URL = "https://loureirosoluciones.es/admin/#agenda"

TIPOS = ("visita", "presupuesto", "obra", "revisión", "otro")
ESTADOS = ("pendiente", "hecha", "cancelada")
FORMATO = "%Y-%m-%dT%H:%M"
DURACION = timedelta(hours=1)


# ── Validación (la usa el CRUD genérico al guardar) ─────────────────────────

def _hora(valor, campo: str) -> datetime:
    try:
        return datetime.strptime(str(valor).strip()[:16], FORMATO)
    except (TypeError, ValueError):
        raise HTTPException(422, f"«{campo}» no es una fecha y hora válida.")


def validar_cita(nuevo: dict, existente: dict | None = None) -> None:
    """Comprueba una cita antes de guardarla.

    Al editar se mezcla con lo que ya está guardado, para que cambiar solo la
    hora de fin siga comprobando que va después del inicio.
    """
    c = {**(existente or {}), **nuevo}
    inicio = _hora(c.get("inicio"), "Empieza")
    if c.get("fin") and _hora(c["fin"], "Termina") <= inicio:
        raise HTTPException(422, "La cita tiene que terminar después de empezar.")
    if c.get("tipo") and c["tipo"] not in TIPOS:
        raise HTTPException(422, "Tipo de cita desconocido.")
    if c.get("estado") and c["estado"] not in ESTADOS:
        raise HTTPException(422, "Estado de cita desconocido.")


# ── Consulta de citas ───────────────────────────────────────────────────────

def _lugar(*partes) -> str:
    """Une las partes de una dirección sin repetir ("Ourense, Ourense")."""
    vistas, limpio = set(), []
    for p in partes:
        p = (p or "").strip()
        if p and p.lower() not in vistas:
            vistas.add(p.lower())
            limpio.append(p)
    return ", ".join(limpio)


def _direccion(c: dict) -> str:
    """La de la cita; si no tiene, la de la obra; si tampoco, la del cliente."""
    if (c.get("direccion") or "").strip():
        return c["direccion"].strip()
    for pre in ("ob", "cl"):
        if (c.get(f"{pre}_dir") or "").strip():
            return _lugar(c[f"{pre}_dir"], c.get(f"{pre}_cp"),
                          c.get(f"{pre}_ciudad"), c.get(f"{pre}_prov"))
    return ""


_SQL = """
    SELECT c.*,
           p.nombre AS profesional, p.telefono AS profesional_tel,
           cl.nombre AS cliente, cl.telefono AS cliente_tel,
           cl.direccion AS cl_dir, cl.cp AS cl_cp, cl.ciudad AS cl_ciudad, cl.provincia AS cl_prov,
           o.titulo AS obra,
           o.direccion AS ob_dir, o.cp AS ob_cp, o.ciudad AS ob_ciudad, o.provincia AS ob_prov
    FROM citas c
    LEFT JOIN profesionales p ON p.id = c.profesional_id
    LEFT JOIN clientes cl ON cl.id = c.cliente_id
    LEFT JOIN obras o ON o.id = c.obra_id
    WHERE substr(c.inicio, 1, 10) <= ?
      AND substr(COALESCE(NULLIF(c.fin, ''), c.inicio), 1, 10) >= date(?, '-1 day')
      AND {filtro}
    ORDER BY c.inicio, c.id
"""


def _filtro(u: dict | None) -> tuple[str, tuple]:
    """Las citas de un usuario: las que creó y las suyas como profesional.

    Sin usuario o con el administrador, todas.
    """
    if u is None or es_admin(u):
        return "1=1", ()
    if u.get("profesional_id"):
        return "(c.usuario_id = ? OR c.profesional_id = ?)", (u["id"], u["profesional_id"])
    return "c.usuario_id = ?", (u["id"],)


def _citas(desde: str, hasta: str, u: dict | None = None) -> list[dict]:
    """Citas que ocupan algún momento entre dos días, ambos incluidos.

    No basta con mirar el día de inicio: una obra de varios días que empezó
    antes del rango también tiene que salir en los días que ocupa dentro de él.
    La consulta trae de más (un día de margen, porque una cita sin fin dura una
    hora y puede pasar de medianoche) y aquí se afina con las horas reales.
    """
    tope_ini = datetime.strptime(desde, "%Y-%m-%d")
    tope_fin = datetime.strptime(hasta, "%Y-%m-%d") + timedelta(days=1)
    salida = []
    filtro, params = _filtro(u)
    for c in db.filas(_SQL.format(filtro=filtro), (hasta, desde, *params)):
        ini = _hora(c["inicio"], "Empieza")
        fin = _hora(c["fin"], "Termina") if c.get("fin") else ini + DURACION
        if not (ini < tope_fin and fin > tope_ini):
            continue
        salida.append({
            "id": c["id"], "titulo": c["titulo"], "tipo": c["tipo"], "estado": c["estado"],
            "inicio": c["inicio"][:16], "fin": (c["fin"] or "")[:16] or None,
            "fin_efectivo": fin.strftime(FORMATO),
            "profesional_id": c["profesional_id"], "profesional": c["profesional"],
            "profesional_tel": c["profesional_tel"],
            "cliente_id": c["cliente_id"], "cliente": c["cliente"],
            "cliente_tel": c["cliente_tel"],
            "obra_id": c["obra_id"], "obra": c["obra"],
            "direccion": c["direccion"], "direccion_efectiva": _direccion(c),
            "notas": c["notas"], "solapa": False,
            "_ini": ini, "_fin": fin,
        })
    # Dos citas a la vez del mismo profesional: se marcan las dos. Las
    # canceladas no cuentan, porque ya no ocupan ese hueco.
    activas = [c for c in salida if c["estado"] != "cancelada" and c["profesional_id"]]
    for i, a in enumerate(activas):
        for b in activas[i + 1:]:
            if (a["profesional_id"] == b["profesional_id"]
                    and a["_ini"] < b["_fin"] and b["_ini"] < a["_fin"]):
                a["solapa"] = b["solapa"] = True
    for c in salida:
        del c["_ini"], c["_fin"]
    return salida


def _dia(valor: str, campo: str) -> str:
    try:
        return date.fromisoformat(valor).isoformat()
    except ValueError:
        raise HTTPException(422, f"«{campo}» tiene que ser una fecha AAAA-MM-DD.")


@router.get("/agenda")
def agenda(desde: str = Query(...), hasta: str = Query(...),
           u: dict = Depends(sesion_actual)):
    """Citas entre dos días, ambos incluidos, de las que puede ver el usuario."""
    exigir(u, "agenda")
    return _citas(_dia(desde, "desde"), _dia(hasta, "hasta"), u)


# ── Enlace de suscripción ───────────────────────────────────────────────────
# El enlace lleva un token secreto largo. Se guarda en la base de datos y no
# en el .env para que funcione sin tocar el servidor, y se puede cambiar desde
# el panel si se filtra: el anterior deja de funcionar al momento.
#
# Hay dos clases de enlace. El del administrador es el de siempre (tabla
# ajustes) y trae todas las citas: así no se rompe la suscripción que ya
# estaba puesta en Google antes de que existiera el equipo. Cada miembro
# tiene el suyo en la tabla usuarios, y trae solo su agenda.

def _token_miembro(u: dict, renovar: bool = False) -> str:
    if not renovar:
        fila = db.fila("SELECT agenda_token FROM usuarios WHERE id = ?", (u["id"],))
        if fila and fila["agenda_token"]:
            return fila["agenda_token"]
    nuevo = secrets.token_urlsafe(32)
    with db.tx() as con:
        con.execute("UPDATE usuarios SET agenda_token = ? WHERE id = ?", (nuevo, u["id"]))
    return nuevo


def _token(renovar: bool = False) -> str:
    if not renovar:
        fila = db.fila("SELECT valor FROM ajustes WHERE clave = 'agenda_token'")
        if fila and fila["valor"]:
            return fila["valor"]
    nuevo = secrets.token_urlsafe(32)
    with db.tx() as con:
        con.execute("INSERT INTO ajustes (clave, valor) VALUES ('agenda_token', ?) "
                    "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor", (nuevo,))
    return nuevo


def _url(token: str) -> str:
    return f"{API_PUBLICA}/api/agenda/{token}.ics"


@router.get("/agenda/suscripcion")
def suscripcion(u: dict = Depends(sesion_actual)):
    exigir(u, "agenda")
    return {"url": _url(_token() if es_admin(u) else _token_miembro(u)),
            "completa": es_admin(u)}


@router.post("/agenda/suscripcion/renovar")
def renovar_suscripcion(u: dict = Depends(sesion_actual)):
    exigir(u, "agenda")
    return {"url": _url(_token(renovar=True) if es_admin(u) else _token_miembro(u, renovar=True)),
            "completa": es_admin(u)}


# ── Fichero iCalendar ───────────────────────────────────────────────────────

VTIMEZONE = [
    "BEGIN:VTIMEZONE", "TZID:Europe/Madrid",
    "BEGIN:DAYLIGHT", "TZOFFSETFROM:+0100", "TZOFFSETTO:+0200", "TZNAME:CEST",
    "DTSTART:19700329T020000", "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU", "END:DAYLIGHT",
    "BEGIN:STANDARD", "TZOFFSETFROM:+0200", "TZOFFSETTO:+0100", "TZNAME:CET",
    "DTSTART:19701025T030000", "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU", "END:STANDARD",
    "END:VTIMEZONE",
]


def _esc(texto) -> str:
    """Escapado de valores de texto de iCalendar (RFC 5545, 3.3.11)."""
    return (str(texto).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n"))


def _plegar(linea: str) -> str:
    """Parte las líneas en trozos de 75 octetos como mucho (RFC 5545, 3.1).

    Las de continuación empiezan por un espacio. Se cuenta en octetos UTF-8 y
    se corta entre caracteres, nunca en medio de una tilde.
    """
    if len(linea.encode("utf-8")) <= 75:
        return linea
    trozos, actual = [], ""
    for ch in linea:
        limite = 75 if not trozos else 74
        if len((actual + ch).encode("utf-8")) > limite:
            trozos.append(actual)
            actual = ""
        actual += ch
    trozos.append(actual)
    return "\r\n ".join(trozos)


def _ics(citas: list[dict], nombre: str = "Loureiro · Agenda") -> str:
    sello = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lineas = ["BEGIN:VCALENDAR", "VERSION:2.0",
              "PRODID:-//Loureiro Soluciones//Agenda//ES",
              "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
              "X-WR-CALNAME:" + _esc(nombre), "X-WR-TIMEZONE:Europe/Madrid",
              "REFRESH-INTERVAL;VALUE=DURATION:PT1H", "X-PUBLISHED-TTL:PT1H",
              *VTIMEZONE]
    for c in citas:
        # Las canceladas no van: al volver a leer el enlace, Google borra de
        # su lado las citas que ya no aparecen.
        if c["estado"] == "cancelada":
            continue
        ini = datetime.strptime(c["inicio"], FORMATO)
        fin = datetime.strptime(c["fin_efectivo"], FORMATO)
        resumen = c["titulo"]
        if c["cliente"]:
            resumen += f" · {c['cliente']}"
        if c["profesional"]:
            resumen += f" ({c['profesional']})"
        if c["estado"] == "hecha":
            resumen = "✓ " + resumen
        desc = [f"Tipo: {c['tipo']}"]
        if c["cliente"]:
            desc.append(f"Cliente: {c['cliente']}"
                        + (f" · {c['cliente_tel']}" if c["cliente_tel"] else ""))
        if c["profesional"]:
            desc.append(f"Profesional: {c['profesional']}"
                        + (f" · {c['profesional_tel']}" if c["profesional_tel"] else ""))
        if c["obra"]:
            desc.append(f"Obra: {c['obra']}")
        if c["notas"]:
            desc += ["", c["notas"]]
        desc += ["", f"Panel: {PANEL_URL}"]
        lineas += [
            "BEGIN:VEVENT",
            f"UID:cita-{c['id']}@loureirosoluciones.es",
            f"DTSTAMP:{sello}",
            f"DTSTART;TZID=Europe/Madrid:{ini:%Y%m%dT%H%M%S}",
            f"DTEND;TZID=Europe/Madrid:{fin:%Y%m%dT%H%M%S}",
            "SUMMARY:" + _esc(resumen),
            "DESCRIPTION:" + _esc("\n".join(desc)),
            "STATUS:CONFIRMED",
        ]
        if c["direccion_efectiva"]:
            # En Google Calendar la ubicación se abre en Maps con un toque.
            lineas.append("LOCATION:" + _esc(c["direccion_efectiva"]))
        lineas.append("END:VEVENT")
    lineas.append("END:VCALENDAR")
    return "\r\n".join(_plegar(l) for l in lineas) + "\r\n"


@publico.get("/agenda/{token}.ics")
def agenda_ics(token: str):
    """La agenda para Google Calendar. Sin sesión: la protege el token."""
    fila = db.fila("SELECT valor FROM ajustes WHERE clave = 'agenda_token'")
    usuario, nombre = None, "Loureiro · Agenda"
    if not (fila and fila["valor"] and secrets.compare_digest(
            token.encode(), fila["valor"].encode())):
        # No es el enlace general: ¿es el de alguien del equipo? Un miembro de
        # baja o sin el módulo de agenda deja de ver sus citas al momento.
        m = db.fila("SELECT * FROM usuarios WHERE agenda_token = ? AND activo = 1", (token,))             if token else None
        if not m:
            raise HTTPException(404, "No encontrado")
        from .auth import usuario_por_id
        usuario = usuario_por_id(m["id"])
        if not puede(usuario, "agenda"):
            raise HTTPException(404, "No encontrado")
        nombre = f"Loureiro · {usuario.get('nombre') or usuario['email']}"
    hoy = date.today()
    citas = _citas((hoy - timedelta(days=90)).isoformat(),
                   (hoy + timedelta(days=400)).isoformat(), usuario)
    return Response(
        content=_ics(citas, nombre),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'inline; filename="loureiro-agenda.ics"',
                 "Cache-Control": "no-cache"})
