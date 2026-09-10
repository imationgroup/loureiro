"""Presupuestos, proformas y facturas en PDF.

Se genera en el servidor y no en el navegador a propósito: el PDF que se le
manda a un cliente es un documento de la empresa, y tiene que salir igual
desde el portátil, desde el móvil o desde un correo automático. Dejarlo en
manos de la maquetación del navegador de turno es pedir que un día llegue
descuadrado.

Los tres tipos comparten maquetación; solo cambian el título, la etiqueta
del cliente, los datos de la esquina (validez o vencimiento) y el pie.

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
from .empresa import EMPRESA


class DocumentoIncompleto(Exception):
    """Falta un dato sin el cual el documento no debe salir."""


TIPOS = {
    "presupuestos": {
        "tabla": "presupuestos", "lineas": "presupuesto_lineas", "fk": "presupuesto_id",
        "titulo": "PRESUPUESTO", "para": "PRESUPUESTO PARA", "uno": "presupuesto",
    },
    "proformas": {
        "tabla": "proformas", "lineas": "proforma_lineas", "fk": "proforma_id",
        "titulo": "FACTURA PROFORMA", "para": "PROFORMA PARA", "uno": "proforma",
    },
    "facturas": {
        "tabla": "facturas", "lineas": "factura_lineas", "fk": "factura_id",
        "titulo": "FACTURA", "para": "FACTURAR A", "uno": "factura",
    },
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


def _identidad() -> str:
    """Razón social · NIF · web, sin dejar un hueco si el NIF no está puesto."""
    nif = f"NIF {EMPRESA['nif']}" if EMPRESA["nif"] else None
    return " · ".join(x for x in [EMPRESA["nombre"], nif, EMPRESA["web"]] if x)


def _parrafo(txt, tam=8.5, color=INK, alineacion=0, negrita=False):
    return Paragraph(txt, ParagraphStyle(
        "c", fontName="Helvetica-Bold" if negrita else "Helvetica",
        fontSize=tam, leading=tam * 1.35, textColor=color, alignment=alineacion))


def _cabecera(c, tipo, p):
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
    datos = [EMPRESA["nombre"],
             f"NIF: {EMPRESA['nif']}" if EMPRESA["nif"] else None,
             EMPRESA["direccion"],
             f"{EMPRESA['telefono']} · {EMPRESA['email']}"]
    for i, l in enumerate(x for x in datos if x):
        c.drawString(MARGEN + 14 * mm, y - 10.5 * mm - i * 3.6 * mm, l)

    # Bloque del documento, arriba a la derecha. "FACTURA PROFORMA" es largo:
    # el cuerpo se reduce hasta que cabe sin pisar los datos de la empresa.
    titulo, tam = TIPOS[tipo]["titulo"], 20
    while c.stringWidth(titulo, "Helvetica-Bold", tam) > 80 * mm and tam > 12:
        tam -= 1
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", tam)
    c.drawRightString(ANCHO - MARGEN, y - 5 * mm, titulo)
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(AMBER)
    c.drawRightString(ANCHO - MARGEN, y - 11 * mm, p["numero"] or f"#{p['id']}")
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 8)
    c.drawRightString(ANCHO - MARGEN, y - 16 * mm, f"Fecha: {_fecha(p['fecha'])}")
    if tipo == "facturas":
        if p.get("vencimiento"):
            c.drawRightString(ANCHO - MARGEN, y - 20 * mm,
                              f"Vencimiento: {_fecha(p['vencimiento'])}")
    else:
        c.drawRightString(ANCHO - MARGEN, y - 20 * mm,
                          f"Validez: {p.get('validez') or 30} días")

    c.setStrokeColor(LINEA)
    c.setLineWidth(0.8)
    c.line(MARGEN, y - 27 * mm, ANCHO - MARGEN, y - 27 * mm)
    return y - 27 * mm


def _bloque_cliente(c, y, tipo, cliente, obra):
    y -= 9 * mm
    c.setFillColor(GRIS)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(MARGEN, y, TIPOS[tipo]["para"])
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
        # La columna de la obra se llama "titulo"; con "nombre" el PDF
        # reventaba en cuanto el documento tenía una obra asignada.
        c.drawString(MARGEN + 16 * mm, y - 3 * mm,
                     obra.get("titulo") or obra.get("nombre") or "")
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


def _filas_totales(lineas):
    """Filas del bloque de totales, con el IVA desglosado por tipo.

    En reformas de vivienda conviven el 21 % y el 10 %, y en una factura el
    desglose por tipo impositivo (base y cuota de cada uno) es obligatorio:
    una sola línea de "IVA" con la suma no vale.
    """
    grupos = {}
    for l in lineas:
        base = (l["cantidad"] or 0) * (l["precio"] or 0)
        g = grupos.setdefault(l["iva"] or 0, [0.0, 0.0])
        g[0] += base
        g[1] += base * (l["iva"] or 0) / 100
    total = sum(b + i for b, i in grupos.values())
    if len(grupos) > 1:
        filas = []
        for tipo in sorted(grupos):
            filas += [(f"Base al {tipo:g} %", grupos[tipo][0]),
                      (f"IVA {tipo:g} %", grupos[tipo][1])]
    else:
        tipo = next(iter(grupos), 21)
        base, iva = grupos.get(tipo, [0.0, 0.0])
        filas = [("Base imponible", base), (f"IVA {tipo:g} %", iva)]
    return filas, total


def _totales(c, y, lineas):
    filas, total = _filas_totales(lineas)
    x = ANCHO - MARGEN
    c.setFont("Helvetica", 9)
    for i, (etiqueta, valor) in enumerate(filas):
        c.setFillColor(GRIS)
        c.drawRightString(x - 30 * mm, y - i * 5.5 * mm, etiqueta)
        c.setFillColor(INK)
        c.drawRightString(x, y - i * 5.5 * mm, _eur(valor))

    # 14,5 mm por debajo de la última fila: la caja del TOTAL mide 11 mm hacia
    # arriba y con menos se subía por encima de la línea del IVA y la tapaba.
    y -= (len(filas) - 1) * 5.5 * mm + 14.5 * mm
    c.setFillColor(AMBER)
    c.rect(x - 68 * mm, y - 2 * mm, 68 * mm, 11 * mm, stroke=0, fill=1)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x - 64 * mm, y + 1.6 * mm, "TOTAL")
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(x - 4 * mm, y + 1.2 * mm, _eur(total))
    return y - 6 * mm


def _pie(c, tipo, p):
    y = MARGEN + 16 * mm
    c.setStrokeColor(LINEA)
    c.setLineWidth(0.8)
    c.line(MARGEN, y, ANCHO - MARGEN, y)
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 7)
    validez = p.get("validez") or 30
    if tipo == "presupuestos":
        avisos = [
            f"Presupuesto válido {validez} días desde la fecha de emisión. "
            "Los precios incluyen mano de obra y materiales salvo indicación expresa.",
            "Este documento no supone contrato hasta su aceptación por escrito. " + _identidad(),
        ]
    elif tipo == "proformas":
        # Una proforma tiene que decir que no es una factura: si no, el
        # cliente puede tomarla como tal y contabilizarla.
        avisos = [
            "Factura proforma: documento sin validez fiscal. No sustituye a la factura, "
            "que se emitirá al realizar el trabajo o recibir el pago.",
            f"Válida {validez} días desde la fecha de emisión. " + _identidad(),
        ]
    else:
        avisos = [_identidad() + " · " + EMPRESA["direccion"]]
    for i, l in enumerate(avisos):
        c.drawString(MARGEN, y - 5 * mm - i * 3.6 * mm, l)


def _comprobar(tipo, doc):
    """Una factura sin número o sin el NIF del emisor no es válida: no sale.

    Presupuestos y proformas no tienen valor fiscal y se dejan descargar igual.
    """
    if tipo != "facturas":
        return
    faltan = []
    if not (doc.get("numero") or "").strip():
        faltan.append("ponerle número")
    if not EMPRESA["nif"]:
        faltan.append("configurar el NIF de la empresa (EMPRESA_NIF en el .env del servidor)")
    if faltan:
        raise DocumentoIncompleto(
            "Para descargar la factura hay que " + " y ".join(faltan) +
            ". Una factura sin esos datos no es válida.")


def documento_pdf(tipo: str, id_: int) -> tuple[bytes | None, str | None]:
    """Devuelve (bytes del PDF, nombre de fichero sugerido)."""
    t = TIPOS[tipo]
    doc = db.fila(f"SELECT * FROM {t['tabla']} WHERE id = ?", (id_,))
    if not doc:
        return None, None
    _comprobar(tipo, doc)

    lineas = db.filas(
        f"SELECT * FROM {t['lineas']} WHERE {t['fk']} = ? ORDER BY orden, id", (id_,))
    cliente = db.fila("SELECT * FROM clientes WHERE id = ?",
                      (doc["cliente_id"],)) if doc["cliente_id"] else None
    obra = db.fila("SELECT * FROM obras WHERE id = ?",
                   (doc["obra_id"],)) if doc["obra_id"] else None

    buf = BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"{t['titulo'].capitalize()} {doc['numero'] or doc['id']}")

    y = _cabecera(c, tipo, doc)
    y = _bloque_cliente(c, y, tipo, cliente, obra)
    y -= 8 * mm

    # Hueco que se deja libre al pie de cada página para los totales y el
    # pie. Crece con el número de filas de IVA.
    reserva = 44 * mm + len(_filas_totales(lineas)[0]) * 5.5 * mm
    ancho_util = ANCHO - 2 * MARGEN

    # La tabla se va partiendo página a página. split() solo corta en dos, y
    # el resto puede no caber tampoco en una página entera: por eso es un
    # bucle y no un único corte.
    restante = _tabla(lineas)
    while True:
        disponible = y - MARGEN - reserva
        partes = restante.split(ancho_util, disponible)
        if not partes:
            if y >= ALTO - MARGEN - 1:       # ni en una página vacía: se pinta tal cual
                partes = [restante]
            else:
                c.showPage()
                y = ALTO - MARGEN
                continue
        _, h = partes[0].wrap(ancho_util, disponible)
        partes[0].drawOn(c, MARGEN, y - h)
        y -= h
        if len(partes) == 1:
            break
        restante = partes[1]
        c.showPage()
        y = ALTO - MARGEN

    y = _totales(c, y - 10 * mm, lineas)

    if doc.get("notas"):
        c.setFillColor(GRIS)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(MARGEN, y, "NOTAS")
        parrafo = _parrafo(doc["notas"].replace(chr(10), "<br/>"), 8, GRIS)
        _, h = parrafo.wrap(ANCHO - 2 * MARGEN, 40 * mm)
        parrafo.drawOn(c, MARGEN, y - 4 * mm - h)

    _pie(c, tipo, doc)
    c.showPage()
    c.save()

    numero = (doc["numero"] or f"{t['uno']}-{doc['id']}").replace("/", "-")
    return buf.getvalue(), f"{numero}.pdf"
