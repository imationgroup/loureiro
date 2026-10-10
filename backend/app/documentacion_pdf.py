"""El PDF de un documento de la pestaña Documentación.

Aquí sí se usa platypus (la maquetación por flujo de reportlab) y no el
canvas a pelo como en pdf.py: un informe de varias páginas con tablas,
citas y fichas de prueba se parte solo, y hacerlo a mano sería contar
milímetros en cada párrafo.

El contenido no se escribe aquí: son los bloques del propio documento
(ver guia_pruebas_cuadro.py). Esto solo decide cómo se ven.
"""

import re
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

from .empresa import EMPRESA

INK = colors.HexColor("#1E2533")
AMBER = colors.HexColor("#F2A81C")
GRIS = colors.HexColor("#6B7180")
LINEA = colors.HexColor("#E2E4E8")
SUAVE = colors.HexColor("#F6F7F9")
AVISO = colors.HexColor("#FDF6E6")

MARGEN = 18 * mm
ANCHO, ALTO = A4
UTIL = ANCHO - 2 * MARGEN


def _estilos() -> dict:
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=9.5, leading=14,
                          textColor=INK, alignment=TA_JUSTIFY)
    return {
        "base": base,
        "h1": ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=17,
                             leading=21, alignment=0, spaceAfter=2),
        "sub": ParagraphStyle("sub", parent=base, fontSize=10.5, leading=15,
                              textColor=GRIS, alignment=0, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=12.5,
                             leading=16, alignment=0, spaceBefore=14, spaceAfter=6),
        "h3": ParagraphStyle("h3", parent=base, fontName="Helvetica-Bold", fontSize=10,
                             leading=14, alignment=0, spaceBefore=2, spaceAfter=3),
        "li": ParagraphStyle("li", parent=base, leftIndent=11, bulletIndent=2, spaceAfter=3),
        "cita": ParagraphStyle("cita", parent=base, fontName="Helvetica-Oblique",
                               leftIndent=9, rightIndent=6, textColor=colors.HexColor("#39414F")),
        "pie": ParagraphStyle("pie", parent=base, fontSize=8, leading=11, textColor=GRIS,
                              alignment=0),
        "celda": ParagraphStyle("celda", parent=base, fontSize=8.2, leading=11, alignment=0),
        "celdacab": ParagraphStyle("celdacab", parent=base, fontName="Helvetica-Bold",
                                   fontSize=8.2, leading=11, alignment=0, textColor=INK),
        "ficha": ParagraphStyle("ficha", parent=base, fontSize=9, leading=13),
        "etiqueta": ParagraphStyle("etiqueta", parent=base, fontName="Helvetica-Bold",
                                   fontSize=7.5, leading=10, textColor=GRIS, alignment=0),
    }


def _texto(t: str) -> str:
    """Pasa el **negrita** del contenido a las etiquetas de reportlab.

    Se escapan antes los caracteres de marcado: el texto es nuestro, pero si
    algún día lleva un «<» no tiene que romper el PDF entero.
    """
    t = (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)


def _tabla(bloque: dict, est: dict) -> list:
    cabecera = [Paragraph(_texto(c), est["celdacab"]) for c in bloque["cabecera"]]
    filas = [[Paragraph(_texto(c), est["celda"]) for c in fila] for fila in bloque["filas"]]
    columnas = len(bloque["cabecera"])
    # La primera columna manda (es el nombre de la cosa) y el resto se reparte.
    primera = UTIL * (0.34 if columnas > 2 else 0.5)
    anchos = [primera] + [(UTIL - primera) / (columnas - 1)] * (columnas - 1)
    t = Table([cabecera] + filas, colWidths=anchos, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SUAVE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, LINEA),
        ("GRID", (0, 0), (-1, -1), 0.4, LINEA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    salida = []
    if bloque.get("titulo"):
        salida.append(Paragraph(_texto(bloque["titulo"]), est["h3"]))
    salida += [t, Spacer(1, 8)]
    return salida


def _caja(contenido: list, fondo, borde, est: dict) -> Table:
    """Un recuadro de color con párrafos dentro, para avisos y fichas."""
    t = Table([[contenido]], colWidths=[UTIL], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fondo),
        ("BOX", (0, 0), (-1, -1), 0.6, borde),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def _prueba(b: dict, est: dict) -> list:
    """La ficha de una prueba: qué se mide, cómo, qué vale y de dónde sale."""
    dentro = [Paragraph("%s · %s" % (_texto(b["numero"]), _texto(b["titulo"])), est["h3"])]
    dentro.append(Paragraph(_texto(b["mide"]), est["ficha"]))
    dentro.append(Spacer(1, 5))
    dentro.append(Paragraph("CÓMO SE HACE", est["etiqueta"]))
    for i, paso in enumerate(b["pasos"], 1):
        dentro.append(Paragraph(_texto(paso), est["li"], bulletText="%d." % i))
    dentro.append(Spacer(1, 4))
    dentro.append(Paragraph("QUÉ VALOR VALE", est["etiqueta"]))
    dentro.append(Paragraph(_texto(b["criterio"]), est["ficha"]))
    if b.get("limite"):
        dentro.append(Spacer(1, 4))
        dentro.append(Paragraph("LÍMITE DE ESTE EQUIPO", est["etiqueta"]))
        dentro.append(Paragraph(_texto(b["limite"]), est["ficha"]))
    if b.get("aviso"):
        dentro.append(Spacer(1, 4))
        dentro.append(Paragraph(_texto(b["aviso"]), est["cita"]))
    dentro.append(Spacer(1, 4))
    dentro.append(Paragraph("Fuente: " + _texto(b["fuente"]), est["pie"]))
    return [KeepTogether([_caja(dentro, colors.white, LINEA, est), Spacer(1, 8)])]


def _bloque(b: dict, est: dict) -> list:
    tipo = b.get("tipo")
    if tipo == "p":
        return [Paragraph(_texto(b["texto"]), est["base"]), Spacer(1, 7)]
    if tipo == "lista":
        return [Paragraph(_texto(p), est["li"], bulletText="•") for p in b["puntos"]] + [Spacer(1, 7)]
    if tipo == "pasos":
        return ([Paragraph(_texto(p), est["li"], bulletText="%d." % i)
                 for i, p in enumerate(b["puntos"], 1)] + [Spacer(1, 7)])
    if tipo == "tabla":
        return _tabla(b, est)
    if tipo == "cita":
        dentro = [Paragraph("«" + _texto(b["texto"]) + "»", est["cita"]),
                  Spacer(1, 3),
                  Paragraph(_texto(b["fuente"]), est["pie"])]
        return [_caja(dentro, SUAVE, LINEA, est), Spacer(1, 8)]
    if tipo == "aviso":
        return [_caja([Paragraph(_texto(b["texto"]), est["ficha"])], AVISO, AMBER, est),
                Spacer(1, 8)]
    if tipo == "fuente":
        return [Paragraph("Fuente: " + _texto(b["texto"]), est["pie"]), Spacer(1, 7)]
    if tipo == "prueba":
        return _prueba(b, est)
    return []


def _marco(c, doc):
    """Cabecera y pie de cada página, con el número y el total."""
    c.saveState()
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(AMBER)
    c.drawString(MARGEN, ALTO - 12 * mm, EMPRESA["marca"].upper())
    c.setFont("Helvetica", 8)
    c.setFillColor(GRIS)
    c.drawRightString(ANCHO - MARGEN, ALTO - 12 * mm, doc.tituloDoc)
    c.setStrokeColor(LINEA)
    c.setLineWidth(0.6)
    c.line(MARGEN, ALTO - 14.5 * mm, ANCHO - MARGEN, ALTO - 14.5 * mm)

    c.line(MARGEN, 14 * mm, ANCHO - MARGEN, 14 * mm)
    c.setFont("Helvetica", 7.5)
    c.drawString(MARGEN, 10 * mm, "Documento interno · " + EMPRESA["nombre"] +
                 " · actualizado " + doc.fechaDoc)
    c.drawRightString(ANCHO - MARGEN, 10 * mm, "Página %d" % c.getPageNumber())
    c.restoreState()


def generar(doc: dict) -> bytes:
    est = _estilos()
    buffer = BytesIO()
    plantilla = BaseDocTemplate(buffer, pagesize=A4,
                                leftMargin=MARGEN, rightMargin=MARGEN,
                                topMargin=20 * mm, bottomMargin=18 * mm,
                                title=doc["titulo"], author=EMPRESA["nombre"])
    plantilla.tituloDoc = doc["titulo"]
    plantilla.fechaDoc = _fecha(doc.get("actualizado"))
    marco = Frame(MARGEN, 18 * mm, UTIL, ALTO - 38 * mm, id="cuerpo",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    plantilla.addPageTemplates([PageTemplate(id="normal", frames=[marco], onPage=_marco)])

    hist = [Paragraph(_texto(doc["titulo"]), est["h1"])]
    if doc.get("subtitulo"):
        hist.append(Paragraph(_texto(doc["subtitulo"]), est["sub"]))
    if doc.get("resumen"):
        hist.append(Paragraph(_texto(doc["resumen"]), est["base"]))
        hist.append(Spacer(1, 8))
    if doc.get("equipo"):
        hist += _tabla({"titulo": "Con qué se hace", "cabecera": ["Aparato", "Qué se mide con él"],
                        "filas": [[n, q] for n, q in doc["equipo"]]}, est)

    for seccion in doc["secciones"]:
        hist.append(Paragraph(_texto(seccion["titulo"]), est["h2"]))
        for bloque in seccion["bloques"]:
            hist += _bloque(bloque, est)

    hist.append(PageBreak())
    hist.append(Paragraph("Fuentes", est["h2"]))
    for f in doc.get("fuentes", []):
        hist.append(Paragraph("<b>" + _texto(f["titulo"]) + "</b>", est["ficha"]))
        hist.append(Paragraph(_texto(f["detalle"]), est["base"]))
        if f.get("url"):
            hist.append(Paragraph(_texto(f["url"]), est["pie"]))
        hist.append(Spacer(1, 8))
    if doc.get("aviso"):
        hist += _bloque({"tipo": "aviso", "texto": doc["aviso"]}, est)

    plantilla.build(hist)
    return buffer.getvalue()


def _fecha(iso) -> str:
    if not iso:
        return "—"
    p = str(iso)[:10].split("-")
    return "%s/%s/%s" % (p[2], p[1], p[0]) if len(p) == 3 else str(iso)
