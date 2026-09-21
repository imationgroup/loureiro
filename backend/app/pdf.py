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

import base64
from datetime import datetime, timedelta, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
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
        # El presupuesto sale sin destinatario: es una oferta de precios que se
        # entrega en mano o se pasa a quien pregunte, y con el nombre y el NIF
        # impresos no vale para nadie más. La factura y la proforma sí lo
        # llevan, que ahí el destinatario es parte del documento.
        "destinatario": False,
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

INK = colors.HexColor("#1E2533")
AMBER = colors.HexColor("#F2A81C")
GRIS = colors.HexColor("#6B7180")
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
    # La marca, la misma que va rotulada en la furgoneta: la L en grafito y
    # el rayo en amarillo. Va en un lienzo de 64 y con la Y al revés, que en
    # un PDF crece hacia arriba.
    u = 11 * mm / 64.0
    x0, y0 = MARGEN, y - 11 * mm
    g = lambda px, py: (x0 + px * u, y0 + (64 - py) * u)

    def forma(puntos, color):
        c.setFillColor(color)
        camino = c.beginPath()
        camino.moveTo(*g(*puntos[0]))
        for punto in puntos[1:]:
            camino.lineTo(*g(*punto))
        camino.close()
        c.drawPath(camino, stroke=0, fill=1)

    forma([(27.8, 2), (20.4, 47.3), (47.8, 48.3), (46.7, 62), (1.5, 62), (8.8, 10.4)], INK)
    forma([(48.8, 7.3), (46.7, 28.3), (56.2, 29.4), (62.5, 50.4), (50.9, 59.9),
           (47.8, 59.9), (46.7, 38.8), (34.1, 37.8), (35.2, 29.4), (38.3, 10.4)], AMBER)

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
    # Hay documentos que no llevan a quién van dirigidos (ver TIPOS). De la
    # obra sí se deja constancia: dice de qué trabajo se está hablando, que no
    # es lo mismo que decir de quién es.
    if not TIPOS[tipo].get("destinatario", True):
        return _bloque_obra(c, y - 4 * mm, obra)
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

    return _bloque_obra(c, y, obra)


def _bloque_obra(c, y, obra):
    if not obra:
        return y
    c.setFillColor(GRIS)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(MARGEN, y - 3 * mm, "OBRA")
    c.setFillColor(INK)
    c.setFont("Helvetica", 8.5)
    # La columna de la obra se llama "titulo"; con "nombre" el PDF reventaba
    # en cuanto el documento tenía una obra asignada.
    c.drawString(MARGEN + 16 * mm, y - 3 * mm,
                 obra.get("titulo") or obra.get("nombre") or "")
    return y - 3 * mm


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


def _titulo_pagina(c, texto):
    """Cabecera sobria para las páginas que van detrás del documento."""
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGEN, ALTO - MARGEN - 4 * mm, texto)
    c.setStrokeColor(AMBER)
    c.setLineWidth(1.6)
    c.line(MARGEN, ALTO - MARGEN - 8 * mm, MARGEN + 26 * mm, ALTO - MARGEN - 8 * mm)
    return ALTO - MARGEN - 18 * mm


def _bloques(texto):
    """Parte el texto en bloques separados por líneas en blanco.

    De cada bloque, la primera línea hace de título y el resto de cuerpo: es
    como escribe cualquiera unas condiciones, sin tener que aprender formato.
    """
    for trozo in (texto or "").replace("\r\n", "\n").split("\n\n"):
        lineas = [l.strip() for l in trozo.split("\n") if l.strip()]
        if lineas:
            yield lineas[0], " ".join(lineas[1:])


def _pagina_condiciones(c, texto, dias_desistimiento=None):
    y = _titulo_pagina(c, "CONDICIONES DE CONTRATACIÓN")
    ancho = ANCHO - 2 * MARGEN
    for titulo, cuerpo in _bloques(texto):
        if y < MARGEN + 40 * mm:
            c.showPage()
            y = _titulo_pagina(c, "CONDICIONES DE CONTRATACIÓN (continuación)")
        p = _parrafo(titulo, 9, INK, negrita=True)
        _, h = p.wrap(ancho, 30 * mm)
        p.drawOn(c, MARGEN, y - h)
        y -= h + 2 * mm
        if cuerpo:
            p = _parrafo(cuerpo, 8.5, GRIS)
            _, h = p.wrap(ancho, 120 * mm)
            p.drawOn(c, MARGEN, y - h)
            y -= h + 5 * mm

    if dias_desistimiento:
        # Con un cliente particular, el derecho de desistimiento no se puede
        # quitar por contrato: lo que se puede es cobrar lo ejecutado si pidió
        # empezar dentro del plazo. Informar de esto es obligatorio, y no
        # hacerlo alarga el plazo del cliente hasta doce meses.
        y -= 4 * mm
        c.setFillColor(SUAVE)
        alto_caja = 34 * mm
        c.rect(MARGEN, y - alto_caja, ANCHO - 2 * MARGEN, alto_caja, stroke=0, fill=1)
        p = _parrafo(
            f"<b>Derecho de desistimiento.</b> Si eres consumidor y firmas fuera de nuestro "
            f"establecimiento o a distancia, dispones de <b>{dias_desistimiento} días naturales</b> "
            "para desistir del contrato sin dar explicaciones, comunicándolo a "
            f"{EMPRESA['email']} o al {EMPRESA['telefono']}. Si pides expresamente que los "
            "trabajos empiecen dentro de ese plazo y después desistes, abonarás la parte "
            "proporcional de lo ya ejecutado y los gastos justificados en que se haya incurrido.",
            8, INK)
        _, h = p.wrap(ANCHO - 2 * MARGEN - 10 * mm, alto_caja)
        p.drawOn(c, MARGEN + 5 * mm, y - 5 * mm - h)
        y -= alto_caja + 4 * mm
    return y


def _pagina_firma(c, doc, firma, dias_desistimiento=None):
    """Hoja de la firma: quién firmó, qué firmó y con qué pruebas."""
    y = _titulo_pagina(c, "ACEPTACIÓN Y FIRMA DEL CLIENTE")
    ancho = ANCHO - 2 * MARGEN

    numero = doc.get("numero") or f"#{doc['id']}"
    cuando = firma.get("firmado_el") or ""
    try:
        local = (datetime.strptime(cuando, "%Y-%m-%d %H:%M:%S")
                 .replace(tzinfo=timezone.utc) + timedelta(hours=2)).strftime("%d/%m/%Y a las %H:%M")
    except ValueError:
        local = cuando

    p = _parrafo(
        f"<b>{escape_basico(firma.get('firmante_nombre'))}</b>"
        + (f", con NIF {escape_basico(firma.get('firmante_nif'))}," if firma.get("firmante_nif") else "")
        + f" ha firmado electrónicamente el presupuesto <b>{numero}</b> el {local} "
        "(hora peninsular), aceptando su contenido y las condiciones de contratación "
        "que se recogen en este documento.", 9, INK)
    _, h = p.wrap(ancho, 40 * mm)
    p.drawOn(c, MARGEN, y - h)
    y -= h + 8 * mm

    if firma.get("firma_inicio_inmediato"):
        p = _parrafo(
            "El cliente <b>solicita expresamente</b> que los trabajos comiencen antes de que "
            f"termine el plazo de desistimiento de {dias_desistimiento or 14} días naturales, "
            "sabiendo que, si desiste después, deberá abonar la parte proporcional de lo ya "
            "ejecutado y los gastos justificados en que se haya incurrido.", 8.5, GRIS)
        _, h = p.wrap(ancho, 30 * mm)
        p.drawOn(c, MARGEN, y - h)
        y -= h + 8 * mm

    # La firma dibujada
    imagen = firma.get("firma_imagen") or ""
    if imagen.startswith("data:image/png;base64,"):
        try:
            datos = base64.b64decode(imagen.split(",", 1)[1])
            c.drawImage(ImageReader(BytesIO(datos)), MARGEN, y - 34 * mm,
                        width=70 * mm, height=32 * mm, mask="auto",
                        preserveAspectRatio=True, anchor="sw")
        except Exception:      # noqa: BLE001
            pass
    c.setStrokeColor(LINEA)
    c.setLineWidth(0.8)
    c.line(MARGEN, y - 36 * mm, MARGEN + 70 * mm, y - 36 * mm)
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 7.5)
    c.drawString(MARGEN, y - 40 * mm, "Firma del cliente")
    y -= 50 * mm

    # Las pruebas
    pruebas = [
        ("Fecha y hora de la firma (UTC)", cuando),
        ("Dirección IP desde la que se firmó", firma.get("firma_ip") or ""),
        ("Navegador", (firma.get("firma_agente") or "")[:80]),
        ("Huella del documento firmado (SHA-256)", firma.get("firma_huella") or ""),
        ("Inicio inmediato solicitado", "Sí" if firma.get("firma_inicio_inmediato") else "No"),
    ]
    tabla = Table([[_parrafo(k, 7.5, GRIS), _parrafo(v, 7.5, INK)] for k, v in pruebas],
                  colWidths=[62 * mm, ancho - 62 * mm])
    tabla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINEA),
    ]))
    _, h = tabla.wrap(ancho, 60 * mm)
    tabla.drawOn(c, MARGEN, y - h)
    y -= h + 6 * mm

    p = _parrafo(
        "Documento firmado electrónicamente conforme al Reglamento (UE) 910/2014 (eIDAS). "
        "Loureiro Soluciones conserva este documento, la firma y los datos de conexión "
        "como prueba de la aceptación. " + _identidad(), 7.5, GRIS)
    _, h = p.wrap(ancho, 30 * mm)
    p.drawOn(c, MARGEN, y - h)


def escape_basico(txt):
    """Los datos del firmante van dentro de un Paragraph, que interpreta HTML."""
    return (str(txt or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


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


def documento_pdf(tipo: str, id_: int, firma: dict | None = None,
                  condiciones_texto: str | None = None,
                  dias_desistimiento: int | None = 14) -> tuple[bytes | None, str | None]:
    """Devuelve (bytes del PDF, nombre de fichero sugerido).

    Con `condiciones_texto` se añade la hoja de condiciones, y con `firma` la
    hoja de aceptación con las pruebas. Es lo que se guarda tal cual el día
    que el cliente firma.
    """
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

    if condiciones_texto:
        _pagina_condiciones(c, condiciones_texto, dias_desistimiento)
        c.showPage()
    if firma:
        _pagina_firma(c, doc, firma, dias_desistimiento)
        c.showPage()
    c.save()

    numero = (doc["numero"] or f"{t['uno']}-{doc['id']}").replace("/", "-")
    sufijo = "-firmado" if firma else ""
    return buf.getvalue(), f"{numero}{sufijo}.pdf"
