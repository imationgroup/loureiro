"""Presupuesto en PDF.

Se genera en el servidor y no en el navegador a propósito: el PDF que se le
manda a un cliente es un documento de la empresa, y tiene que salir igual
desde el portátil, desde el móvil o desde un correo automático. Dejarlo en
manos de la maquetación del navegador de turno es pedir que un día llegue
descuadrado.

Se usa reportlab porque es Python puro con ruedas precompiladas: no hace
falta cairo, pango ni ninguna librería del sistema en la imagen de Docker.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from . import db

# ── Identidad ────────────────────────────────────────────────────────────
# Los mismos datos que el aviso legal del sitio. Si se constituye la S.L. y
# hay CIF, se cambia aquí y sale en todos los presupuestos a la vez.
EMPRESA = {
    "nombre": "Loureiro Soluciones, S.L. en constitución",
    "marca": "Loureiro soluciones",
    "nif": "NIF: en trámite",
    "direccion": "OU-0517, 32910 San Ciprián de Viñas, Ourense",
    "telefono": "603 905 128",
    "email": "contacto@loureirosoluciones.es",
    "web": "loureirosoluciones.es",
}

INK = colors.HexColor("#14161A")
AMBER = colors.HexColor("#F97316")
GRIS = colors.HexColor("#6C7079")
LINEA = colors.HexColor("#E2E4E8")
SUAVE = colors.HexColor("#F6F7F9")

MARGEN = 18 * mm
ANCHO, ALTO = A4


def _eur(n: float) -> str:
    """Formato español: miles con punto y decimales con coma."""
    s = f"{n:,.2f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".") + " €"


def _fecha(iso: str | None) -> str:
    if not iso:
        return "—"
    p = str(iso)[:10].split("-")
    return f"{p[2]}/{p[1]}/{p[0]}" if len(p) == 3 else str(iso)


def _localidad(cliente) -> str | None:
    """CP, ciudad y provincia en una línea, sin repetir.

    En Ourense capital la ciudad y la provincia se llaman igual, y la línea
    salía como "32003 Ourense Ourense".
    """
    ciudad = (cliente.get("ciudad") or "").strip()
    provincia = (cliente.get("provincia") or "").strip()
    partes = [(cliente.get("cp") or "").strip(), ciudad]
    if provincia and provincia.lower() != ciudad.lower():
        partes.append(f"({provincia})")
    linea = " ".join(x for x in partes if x)
    return linea or None


def _parrafo(txt, tam=8.5, color=INK, alineacion=0, negrita=False):
    return Paragraph(txt, ParagraphStyle(
        "c", fontName="Helvetica-Bold" if negrita else "Helvetica",
        fontSize=tam, leading=tam * 1.35, textColor=color, alignment=alineacion))


def _cabecera(c, p):
    y = ALTO - MARGEN

    # Isotipo: la misma casa de trazo del sitio, dibujada a mano porque son
    # cuatro líneas y así no hay que arrastrar un fichero de imagen.
    u = 11 * mm / 40.0
    x0, y0 = MARGEN, y - 11 * mm
    g = lambda px, py: (x0 + px * u, y0 + (40 - py) * u)
    c.setLineWidth(3 * u)
    c.setLineJoin(1)
    c.setStrokeColor(INK)
    c.lines([(*g(6, 30), *g(6, 10)), (*g(6, 10), *g(20, 4)),
             (*g(20, 4), *g(34, 10)), (*g(34, 10), *g(34, 30))])
    c.setStrokeColor(AMBER)
    c.lines([(*g(14, 30), *g(14, 20)), (*g(14, 20), *g(26, 20)),
             (*g(26, 20), *g(26, 30))])

    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(MARGEN + 14 * mm, y - 6 * mm, EMPRESA["marca"])
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 7.5)
    for i, l in enumerate([EMPRESA["nombre"], EMPRESA["nif"], EMPRESA["direccion"],
                           f"{EMPRESA['telefono']} · {EMPRESA['email']}"]):
        c.drawString(MARGEN + 14 * mm, y - 10.5 * mm - i * 3.6 * mm, l)

    # Bloque del documento, arriba a la derecha
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 20)
    c.drawRightString(ANCHO - MARGEN, y - 5 * mm, "PRESUPUESTO")
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(AMBER)
    c.drawRightString(ANCHO - MARGEN, y - 11 * mm, p["numero"] or f"#{p['id']}")
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 8)
    c.drawRightString(ANCHO - MARGEN, y - 16 * mm, f"Fecha: {_fecha(p['fecha'])}")
    c.drawRightString(ANCHO - MARGEN, y - 20 * mm,
                      f"Validez: {p['validez'] or 30} días")

    c.setStrokeColor(LINEA)
    c.setLineWidth(0.8)
    c.line(MARGEN, y - 27 * mm, ANCHO - MARGEN, y - 27 * mm)
    return y - 27 * mm


def _bloque_cliente(c, y, cliente, obra):
    y -= 9 * mm
    c.setFillColor(GRIS)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(MARGEN, y, "PRESUPUESTO PARA")
    y -= 5 * mm
    c.setFillColor(INK)
    if not cliente:
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(MARGEN, y, "Sin cliente asignado")
        return y - 4 * mm
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(MARGEN, y, cliente["nombre"])
    c.setFont("Helvetica", 8.5)
    c.setFillColor(GRIS)
    lineas = [x for x in [
        cliente.get("nif"),
        cliente.get("direccion"),
        _localidad(cliente),
        " · ".join(x for x in [cliente.get("telefono"), cliente.get("email")] if x) or None,
    ] if x]
    for i, l in enumerate(lineas):
        c.drawString(MARGEN, y - 4.6 * mm - i * 4 * mm, l)
    y -= 4.6 * mm + len(lineas) * 4 * mm

    if obra:
        c.setFillColor(GRIS)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(MARGEN, y - 3 * mm, "OBRA")
        c.setFillColor(INK)
        c.setFont("Helvetica", 8.5)
        c.drawString(MARGEN + 16 * mm, y - 3 * mm, obra["nombre"])
        y -= 3 * mm
    return y


def _tabla(lineas):
    cab = ["Concepto", "Cant.", "Ud.", "Precio", "IVA", "Importe"]
    datos = [[_parrafo(f"<b>{x}</b>", 8, colors.white) if i == 0 else
              _parrafo(f"<b>{x}</b>", 8, colors.white, TA_RIGHT)
              for i, x in enumerate(cab)]]
    for l in lineas:
        importe = (l["cantidad"] or 0) * (l["precio"] or 0)
        datos.append([
            _parrafo(l["concepto"] or ""),
            _parrafo(f"{l['cantidad']:g}", alineacion=TA_RIGHT),
            _parrafo(l["unidad"] or "ud", alineacion=TA_RIGHT),
            _parrafo(_eur(l["precio"] or 0), alineacion=TA_RIGHT),
            _parrafo(f"{l['iva']:g} %", alineacion=TA_RIGHT),
            _parrafo(_eur(importe), alineacion=TA_RIGHT, negrita=True),
        ])
    t = Table(datos, colWidths=[None, 15 * mm, 12 * mm, 24 * mm, 15 * mm, 26 * mm],
              repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SUAVE]),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINEA),
    ]))
    return t


def _totales(c, y, lineas):
    base = sum((l["cantidad"] or 0) * (l["precio"] or 0) for l in lineas)
    iva = sum((l["cantidad"] or 0) * (l["precio"] or 0) * (l["iva"] or 0) / 100
              for l in lineas)
    x = ANCHO - MARGEN
    c.setFont("Helvetica", 9)
    c.setFillColor(GRIS)
    c.drawRightString(x - 30 * mm, y, "Base imponible")
    c.setFillColor(INK)
    c.drawRightString(x, y, _eur(base))
    c.setFillColor(GRIS)
    c.drawRightString(x - 30 * mm, y - 5.5 * mm, "IVA")
    c.setFillColor(INK)
    c.drawRightString(x, y - 5.5 * mm, _eur(iva))

    # 20 mm, no 14: la caja del TOTAL mide 11 mm hacia arriba y con 14
    # se subia por encima de la linea del IVA y la tapaba.
    y -= 20 * mm
    c.setFillColor(AMBER)
    c.rect(x - 68 * mm, y - 2 * mm, 68 * mm, 11 * mm, stroke=0, fill=1)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x - 64 * mm, y + 1.6 * mm, "TOTAL")
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(x - 4 * mm, y + 1.2 * mm, _eur(base + iva))
    return y - 6 * mm


def _pie(c, p):
    y = MARGEN + 16 * mm
    c.setStrokeColor(LINEA)
    c.setLineWidth(0.8)
    c.line(MARGEN, y, ANCHO - MARGEN, y)
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 7)
    avisos = [
        f"Presupuesto válido {p['validez'] or 30} días desde la fecha de emisión. "
        "Los precios incluyen mano de obra y materiales salvo indicación expresa.",
        "Este documento no supone contrato hasta su aceptación por escrito. "
        f"{EMPRESA['nombre']} · {EMPRESA['nif']} · {EMPRESA['web']}",
    ]
    for i, l in enumerate(avisos):
        c.drawString(MARGEN, y - 5 * mm - i * 3.6 * mm, l)


def presupuesto_pdf(id_: int) -> tuple[bytes, str]:
    """Devuelve (bytes del PDF, nombre de fichero sugerido)."""
    p = db.fila("SELECT * FROM presupuestos WHERE id = ?", (id_,))
    if not p:
        return None, None
    lineas = db.filas(
        "SELECT * FROM presupuesto_lineas WHERE presupuesto_id = ? ORDER BY orden, id",
        (id_,))
    cliente = db.fila("SELECT * FROM clientes WHERE id = ?",
                      (p["cliente_id"],)) if p["cliente_id"] else None
    obra = db.fila("SELECT * FROM obras WHERE id = ?",
                   (p["obra_id"],)) if p["obra_id"] else None

    buf = BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Presupuesto {p['numero'] or p['id']}")

    y = _cabecera(c, p)
    y = _bloque_cliente(c, y, cliente, obra)

    tabla = _tabla(lineas)
    ancho_util = ANCHO - 2 * MARGEN
    # El alto se mide antes de dibujar para saber si cabe; si no, se parte en
    # páginas y se repite la fila de cabecera (repeatRows=1).
    partes = tabla.split(ancho_util, y - MARGEN - 46 * mm)
    y -= 8 * mm
    if not partes:
        partes = [tabla]
    for i, parte in enumerate(partes):
        if i:
            c.showPage()
            y = ALTO - MARGEN
        w, h = parte.wrap(ancho_util, y)
        parte.drawOn(c, MARGEN, y - h)
        y = y - h

    y = _totales(c, y - 10 * mm, lineas)

    if p.get("notas"):
        c.setFillColor(GRIS)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(MARGEN, y, "NOTAS")
        parrafo = _parrafo(p["notas"].replace(chr(10), "<br/>"), 8, GRIS)
        w, h = parrafo.wrap(ANCHO - 2 * MARGEN, 40 * mm)
        parrafo.drawOn(c, MARGEN, y - 4 * mm - h)

    _pie(c, p)
    c.showPage()
    c.save()

    numero = (p["numero"] or f"presupuesto-{p['id']}").replace("/", "-")
    return buf.getvalue(), f"{numero}.pdf"
