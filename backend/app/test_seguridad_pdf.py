"""El informe del test de seguridad, para entregar al cliente.

Va en el orden en que lo lee quien no es electricista: primero la nota y qué
significa, después los defectos de más a menos grave con lo que hay que hacer
y por qué, y al final la lista entera de lo comprobado, para quien quiera el
detalle.

Se maqueta con las mismas piezas que los documentos de la pestaña
Documentación (documentacion_pdf.py), para que los dos salgan con la misma
cara.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

from . import test_seguridad_puntos as puntos
from .documentacion_pdf import (ALTO, AMBER, ANCHO, AVISO, GRIS, INK, LINEA, MARGEN, SUAVE,
                                UTIL, _caja, _estilos, _fecha, _texto)
from .empresa import EMPRESA

ROJO = colors.HexColor("#C62828")
NARANJA = colors.HexColor("#D9730D")
VERDE = colors.HexColor("#2E7D32")

COLOR_NIVEL = {"peligro": ROJO, "deficiente": NARANJA, "mejorable": AMBER,
               "correcta": VERDE, "sin_datos": GRIS}
# En hexadecimal y no como color de reportlab: van dentro del texto de un párrafo.
HEX_GRAVEDAD = {puntos.MUY_GRAVE: "#C62828", puntos.GRAVE: "#D9730D", puntos.LEVE: "#6B7180"}
COLOR_GRAVEDAD = {k: colors.HexColor(v) for k, v in HEX_GRAVEDAD.items()}
TITULO_GRAVEDAD = {puntos.MUY_GRAVE: "Defectos muy graves", puntos.GRAVE: "Defectos graves",
                   puntos.LEVE: "Defectos leves"}
QUE_ES = {
    puntos.MUY_GRAVE: "Peligro inmediato para las personas o los bienes. Hay que corregirlos ya.",
    puntos.GRAVE: "No son un peligro inmediato, pero pueden serlo en cuanto se produzca un fallo.",
    puntos.LEVE: "No suponen peligro ni impiden el uso normal de la instalación.",
}
RESULTADO = {puntos.OK: "Correcto", puntos.FALLO: "DEFECTO", puntos.NA: "No aplica"}


def _nota(resultado: dict, est: dict) -> Table:
    """El recuadro de arriba: la nota en grande y lo que quiere decir."""
    color = COLOR_NIVEL[resultado["nivel"]]
    nota = "—" if resultado["puntuacion"] is None else str(resultado["puntuacion"])
    grande = ParagraphStyle("nota", parent=est["base"], fontName="Helvetica-Bold", fontSize=34,
                            leading=36, alignment=1, textColor=color)
    sobre = ParagraphStyle("sobre", parent=est["pie"], alignment=1)
    veredicto = ParagraphStyle("veredicto", parent=est["h2"], spaceBefore=0, spaceAfter=3,
                               textColor=color)
    n = resultado["n"]
    recuento = "Muy graves: %d · Graves: %d · Leves: %d" % (
        n[puntos.MUY_GRAVE], n[puntos.GRAVE], n[puntos.LEVE])
    hechas = "%d de %d puntos comprobados" % (resultado["hechas"], resultado["total"])
    t = Table([[
        [Paragraph(nota, grande), Paragraph("sobre 100", sobre)],
        [Paragraph(_texto(resultado["veredicto"]), veredicto),
         Paragraph(_texto(resultado["porque"]), est["ficha"]),
         Spacer(1, 4),
         Paragraph("<b>%s</b> · %s" % (recuento, hechas), est["pie"])],
    ]], colWidths=[34 * mm, UTIL - 34 * mm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SUAVE),
        ("BOX", (0, 0), (-1, -1), 0.6, LINEA),
        ("LINEBEFORE", (0, 0), (0, -1), 3, color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def _datos(test: dict, est: dict) -> Table:
    filas = [("Titular", test.get("titular")), ("Dirección", test.get("direccion")),
             ("Fecha de la revisión", _fecha(test.get("fecha"))),
             ("Revisado por", test.get("instalador"))]
    t = Table([[Paragraph(_texto(k), est["celdacab"]), Paragraph(_texto(v or "—"), est["celda"])]
               for k, v in filas], colWidths=[40 * mm, UTIL - 40 * mm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINEA),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _defecto(d: dict, est: dict) -> list:
    """Un defecto: qué pasa, qué hay que hacer y por qué."""
    color = COLOR_GRAVEDAD[d["gravedad"]]
    titulo = "%s · %s" % (_texto(d["numero"]), _texto(d["defecto"]))
    if d.get("detalle"):
        titulo += " <font color='#6B7180'>(%s)</font>" % _texto(d["detalle"])
    dentro = [
        Paragraph(titulo, est["h3"]),
        Paragraph("<b>Qué hacer:</b> " + _texto(d["recomendacion"]), est["ficha"]),
        Spacer(1, 2),
        Paragraph("<b>Por qué:</b> " + _texto(d["porque"]), est["ficha"]),
        Spacer(1, 3),
        Paragraph(_texto(d["fuente"]), est["pie"]),
    ]
    t = Table([[dentro]], colWidths=[UTIL], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, LINEA),
        ("LINEBEFORE", (0, 0), (0, -1), 3, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return [KeepTogether([t, Spacer(1, 6)])]


def _detalle(respuestas: dict, resultado: dict, est: dict) -> list:
    """La lista entera, punto por punto, con lo que salió en cada uno."""
    salida = []
    for clave, titulo in puntos.BLOQUES:
        filas = [[Paragraph(_texto(c), est["celdacab"]) for c in ("", "Comprobación", "Resultado")]]
        for g in puntos.GRUPOS:
            if g["bloque"] != clave:
                continue
            for p in g["puntos"]:
                estado = resultado["estados"].get(p["clave"])
                texto = _texto(p["texto"])
                # Lo medido: la cuenta ya hecha si el punto sale de ella; si no, el valor.
                medido = resultado["detalles"].get(p["clave"]) or ", ".join(
                    ("%s %s" % (respuestas["valores"][m["clave"]], m["unidad"])).strip()
                    for m in p["medidas"] if respuestas["valores"].get(m["clave"]))
                if medido:
                    texto += " <font color='#6B7180'>· %s</font>" % _texto(medido)
                sale = RESULTADO.get(estado, "Sin comprobar")
                if estado == puntos.FALLO:
                    sale = "<font color='%s'><b>%s</b></font>" % (HEX_GRAVEDAD[p["gravedad"]], sale)
                filas.append([Paragraph(_texto(g["numero"]), est["celda"]),
                              Paragraph(texto, est["celda"]),
                              Paragraph(sale, est["celda"])])
        t = Table(filas, colWidths=[11 * mm, UTIL - 39 * mm, 28 * mm], repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SUAVE),
            ("GRID", (0, 0), (-1, -1), 0.4, LINEA),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        salida += [Paragraph(_texto(titulo), est["h3"]), t, Spacer(1, 10)]
    return salida


def _marco(c, doc):
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
    c.drawString(MARGEN, 10 * mm, " · ".join(
        x for x in (EMPRESA["nombre"], EMPRESA["telefono"], EMPRESA["web"]) if x))
    c.drawRightString(ANCHO - MARGEN, 10 * mm, "Página %d" % c.getPageNumber())
    c.restoreState()


def generar(test: dict, respuestas: dict, resultado: dict) -> bytes:
    est = _estilos()
    buffer = BytesIO()
    titulo = "Test de seguridad eléctrica"
    numero = test.get("numero") or ""
    plantilla = BaseDocTemplate(buffer, pagesize=A4,
                                leftMargin=MARGEN, rightMargin=MARGEN,
                                topMargin=20 * mm, bottomMargin=18 * mm,
                                title=("%s %s" % (titulo, numero)).strip(),
                                author=EMPRESA["nombre"])
    plantilla.tituloDoc = ("%s · %s" % (titulo, numero)) if numero else titulo
    marco = Frame(MARGEN, 18 * mm, UTIL, ALTO - 38 * mm, id="cuerpo",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    plantilla.addPageTemplates([PageTemplate(id="normal", frames=[marco], onPage=_marco)])

    hist = [Paragraph(titulo, est["h1"]),
            Paragraph("Revisión del cuadro y de la instalación de la vivienda" +
                      (" · " + _texto(numero) if numero else ""), est["sub"]),
            _datos(test, est), Spacer(1, 10),
            _nota(resultado, est), Spacer(1, 4)]

    if resultado["pendientes"]:
        hist += [Spacer(1, 4), Paragraph(
            "Quedan %d puntos sin comprobar: la puntuación solo cuenta lo que se ha revisado."
            % resultado["pendientes"], est["pie"])]

    hay = any(resultado["defectos"].values())
    hist.append(Paragraph("Defectos encontrados y qué hacer" if hay else "Defectos encontrados",
                          est["h2"]))
    if not hay:
        hist += [Paragraph("Ninguno en los puntos comprobados.", est["base"]), Spacer(1, 6)]
    for gravedad in (puntos.MUY_GRAVE, puntos.GRAVE, puntos.LEVE):
        lista = resultado["defectos"][gravedad]
        if not lista:
            continue
        hist.append(Paragraph(
            "<font color='%s'>%s (%d)</font>" % (HEX_GRAVEDAD[gravedad], TITULO_GRAVEDAD[gravedad],
                                                 len(lista)), est["h3"]))
        hist += [Paragraph(QUE_ES[gravedad], est["pie"]), Spacer(1, 5)]
        for d in lista:
            hist += _defecto(d, est)

    hist.append(Paragraph("Recomendaciones", est["h2"]))
    orden = [d for g in (puntos.MUY_GRAVE, puntos.GRAVE, puntos.LEVE)
             for d in resultado["defectos"][g]]
    if orden:
        hist.append(Paragraph("Por orden de urgencia:", est["base"]))
        hist.append(Spacer(1, 3))
    recomendaciones = [d["recomendacion"] for d in orden] + [resultado["siempre"]]
    for i, r in enumerate(recomendaciones, 1):
        hist.append(Paragraph(_texto(r), est["li"], bulletText="%d." % i))
    hist.append(Spacer(1, 6))

    if (test.get("observaciones") or "").strip():
        hist.append(Paragraph("Observaciones", est["h2"]))
        for linea in test["observaciones"].splitlines():
            if linea.strip():
                hist += [Paragraph(_texto(linea), est["base"]), Spacer(1, 4)]

    hist.append(Paragraph("Detalle de las comprobaciones", est["h2"]))
    hist += _detalle(respuestas, resultado, est)

    hist.append(Paragraph("Alcance de esta revisión", est["h2"]))
    hist += [_caja([Paragraph(_texto(resultado["alcance"]), est["ficha"])], AVISO, AMBER, est),
             Spacer(1, 6),
             Paragraph("La clasificación de los defectos en muy graves, graves y leves sigue la del "
                       "REBT, ITC-BT-05, apartado 6.", est["pie"])]

    plantilla.build(hist)
    return buffer.getvalue()
