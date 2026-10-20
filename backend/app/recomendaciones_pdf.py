"""La hoja de recomendaciones, para entregar al cliente.

Va en el orden en que la lee quien no es electricista: arriba cuántas cosas
hay y de qué urgencia, después lo que se vio en general y luego cada
recomendación, de la más urgente a la que puede esperar, con lo que se vio,
qué se recomienda y por qué.

Se maqueta con las mismas piezas que el test de seguridad, para que los
documentos de Certificados salgan con la misma cara.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

from .documentacion_pdf import ALTO, LINEA, MARGEN, SUAVE, UTIL, _estilos, _fecha, _texto
from .empresa import EMPRESA
from .test_seguridad_pdf import _marco

# Mismos colores que la gravedad de los defectos del test de seguridad.
HEX = {"urgente": "#C62828", "recomendada": "#D9730D", "mejora": "#2E7D32"}
COLOR = {k: colors.HexColor(v) for k, v in HEX.items()}
NOMBRE = {"urgente": "Urgente", "recomendada": "Recomendable", "mejora": "Mejora"}
PLURAL = {"urgente": ("urgente", "urgentes"), "recomendada": ("recomendable", "recomendables"),
          "mejora": ("mejora", "mejoras")}
QUE_ES = {
    "urgente": "Hay riesgo para las personas o la instalación. Conviene hacerlo cuanto antes.",
    "recomendada": "No es un peligro inmediato, pero conviene hacerlo en los próximos meses.",
    "mejora": "Gana en comodidad, ahorro o seguridad. Sin prisa, cuando le venga bien.",
}
ORDEN = ("urgente", "recomendada", "mejora")


def _datos(hoja: dict, est: dict) -> Table:
    filas = [("Cliente", hoja.get("titular")), ("Dirección", hoja.get("direccion")),
             ("Fecha", _fecha(hoja.get("fecha"))), ("Electricista", hoja.get("autor"))]
    t = Table([[Paragraph(_texto(k), est["celdacab"]), Paragraph(_texto(v or "—"), est["celda"])]
               for k, v in filas], colWidths=[32 * mm, UTIL - 32 * mm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINEA),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _resumen(puntos: list[dict], est: dict) -> Table:
    """Tres casillas con el recuento por prioridad y qué significa cada una."""
    num = ParagraphStyle("num", parent=est["base"], fontName="Helvetica-Bold", fontSize=22,
                         leading=24, alignment=1)
    nombre = ParagraphStyle("nombre", parent=est["base"], fontName="Helvetica-Bold", fontSize=9,
                            leading=11, alignment=1)
    nota = ParagraphStyle("nota", parent=est["pie"], alignment=1)
    celdas = []
    for k in ORDEN:
        n = sum(1 for p in puntos if p["prioridad"] == k)
        celdas.append([
            Paragraph("<font color='%s'>%d</font>" % (HEX[k], n), num),
            Paragraph("<font color='%s'>%s</font>" % (HEX[k], PLURAL[k][n != 1].capitalize()), nombre),
            Spacer(1, 3),
            Paragraph(_texto(QUE_ES[k]), nota),
        ])
    ancho = UTIL / 3
    t = Table([celdas], colWidths=[ancho] * 3, hAlign="LEFT")
    estilo = [
        ("BACKGROUND", (0, 0), (-1, -1), SUAVE),
        ("BOX", (0, 0), (-1, -1), 0.6, LINEA),
        ("LINEAFTER", (0, 0), (1, 0), 0.6, LINEA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]
    for i, k in enumerate(ORDEN):
        estilo.append(("LINEABOVE", (i, 0), (i, 0), 3, COLOR[k]))
    t.setStyle(TableStyle(estilo))
    return t


def _parrafos(texto: str, estilo) -> list:
    salida = []
    for linea in (texto or "").splitlines():
        if linea.strip():
            salida += [Paragraph(_texto(linea), estilo), Spacer(1, 3)]
    return salida


def _punto(i: int, p: dict, est: dict) -> list:
    """Una recomendación: qué se vio, qué hacer y por qué."""
    k = p["prioridad"]
    chip = ParagraphStyle("chip", parent=est["pie"], fontName="Helvetica-Bold", textColor=COLOR[k])
    titulo = ParagraphStyle("tit", parent=est["h3"], fontSize=11, leading=14, spaceBefore=1, spaceAfter=4)
    dentro = [Paragraph("%d · %s" % (i, NOMBRE[k].upper()), chip),
              Paragraph(_texto(p["titulo"]), titulo)]
    for etiqueta, clave in (("Lo que hemos visto", "visto"),
                            ("Por qué se lo recomendamos", "porque")):
        if p.get(clave):
            lineas = [l for l in p[clave].splitlines() if l.strip()]
            dentro.append(Paragraph("<b>%s:</b> %s" % (etiqueta, _texto(lineas[0])), est["ficha"]))
            dentro += [Paragraph(_texto(l), est["ficha"]) for l in lineas[1:]]
            dentro.append(Spacer(1, 3))
    if p.get("coste"):
        dentro.append(Paragraph("<b>Coste orientativo:</b> " + _texto(p["coste"]), est["ficha"]))
    t = Table([[dentro]], colWidths=[UTIL], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, LINEA),
        ("LINEBEFORE", (0, 0), (0, -1), 3, COLOR[k]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return [KeepTogether([t, Spacer(1, 7)])]


def generar(hoja: dict, puntos: list[dict]) -> bytes:
    est = _estilos()
    buffer = BytesIO()
    titulo = "Hoja de recomendaciones"
    numero = hoja.get("numero") or ""
    plantilla = BaseDocTemplate(buffer, pagesize=A4,
                                leftMargin=MARGEN, rightMargin=MARGEN,
                                topMargin=20 * mm, bottomMargin=18 * mm,
                                title=("%s %s" % (titulo, numero)).strip(),
                                author=EMPRESA["nombre"])
    plantilla.tituloDoc = ("%s · %s" % (titulo, numero)) if numero else titulo
    marco = Frame(MARGEN, 18 * mm, UTIL, ALTO - 38 * mm, id="cuerpo",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    plantilla.addPageTemplates([PageTemplate(id="normal", frames=[marco], onPage=_marco)])

    # De más a menos urgente; dentro de cada prioridad, en el orden en que se escribieron.
    puntos = sorted(puntos, key=lambda p: ORDEN.index(p.get("prioridad", "recomendada")))

    hist = [Paragraph(titulo, est["h1"]),
            Paragraph("Lo que hemos visto en su instalación y lo que le recomendamos" +
                      (" · " + _texto(numero) if numero else ""), est["sub"]),
            _datos(hoja, est), Spacer(1, 12)]

    if puntos:
        hist += [_resumen(puntos, est), Spacer(1, 4)]

    if (hoja.get("visto") or "").strip():
        hist.append(Paragraph("Lo que hemos visto", est["h2"]))
        hist += _parrafos(hoja["visto"], est["base"])

    hist.append(Paragraph("Nuestras recomendaciones", est["h2"]))
    if puntos:
        hist += [Paragraph("Ordenadas de la más urgente a la que puede esperar.", est["pie"]),
                 Spacer(1, 6)]
        for i, p in enumerate(puntos, 1):
            hist += _punto(i, p, est)
    else:
        hist += [Paragraph("Ninguna: no hemos visto nada que haga falta cambiar.", est["base"]),
                 Spacer(1, 6)]

    # El cierre va junto, para que el aviso final no se quede solo en una página.
    cierre = []
    if (hoja.get("conclusion") or "").strip():
        cierre.append(Paragraph("En resumen", est["h2"]))
        cierre += _parrafos(hoja["conclusion"], est["base"])
    cierre += [Spacer(1, 6), Paragraph(
        "Estas recomendaciones se basan en lo que se pudo ver y comprobar el día de la visita. "
        "No son un presupuesto: si quiere que hagamos alguno de estos trabajos, se lo "
        "presupuestamos sin compromiso%s." % (
            " llamando al " + _texto(EMPRESA["telefono"]) if EMPRESA.get("telefono") else ""),
        est["pie"])]
    hist.append(KeepTogether(cierre))

    plantilla.build(hist)
    return buffer.getvalue()
