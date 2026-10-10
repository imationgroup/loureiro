"""El certificado de instalación eléctrica, escrito sobre el impreso oficial.

No se dibuja un documento parecido: se escribe encima del **impreso IN614C de
la Xunta de Galicia**, el mismo que hay que presentar. El PDF que sale es el
formulario oficial con los datos puestos y aplanado, así que no depende de
que el visor sepa rellenar formularios.

Las coordenadas no están inventadas: salen de los 89 campos del propio
impreso, leyendo el rectángulo de cada uno. Si algún día la Xunta cambia el
formulario, se vuelven a leer con:

    python -c "import pypdf; r=pypdf.PdfReader('app/plantillas/cie-in614c.pdf'); \
               [print(a.get_object().get('/T'), a.get_object()['/Rect']) \
                for a in r.pages[0]['/Annots']]"

El impreso es un formulario de LiveCycle (XFA). Rellenar sus campos no sirve:
la mayoría de los visores no los pintan. Por eso se escribe encima.
"""

import io
import os

from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

PLANTILLA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "plantillas", "cie-in614c.pdf")

TIPO_LETRA = "Helvetica"
TAMANO = 9

# Dónde va cada dato: (x0, y0, x1, y1) en puntos, con el origen abajo a la
# izquierda, que es como mide el PDF.
CASILLAS = {
    "titular":            (38, 700, 291, 716),
    "titular_nif":        (298, 700, 379, 716),
    "emplazamiento":      (38, 671, 291, 687),
    "numero_via":         (299, 671, 336, 687),
    "piso":               (343, 671, 379, 687),
    "provincia":          (38, 642, 176, 658),
    "ayuntamiento":       (185, 642, 379, 658),
    "distribuidora":      (38, 613, 379, 629),
    "uso":                (38, 584, 379, 600),
    "superficie":         (38, 555, 151, 571),
    "grado":              (37, 520, 379, 536),
    "di_longitud":        (38, 480, 204, 495),
    "di_seccion":         (213, 480, 379, 495),
    "di_tension":         (38, 451, 204, 466),
    "di_potencia":        (213, 451, 379, 466),
    "prot_iga":           (38, 380, 165, 394),
    "prot_dif1_int":      (168, 380, 236, 394),
    "prot_dif1_sens":     (239, 380, 307, 394),
    "prot_iga2":          (38, 363, 165, 377),
    "prot_dif2_int":      (168, 363, 236, 377),
    "prot_dif2_sens":     (239, 363, 307, 377),
    "prot_resistencia":   (310, 363, 365, 377),
    "organismo_control":  (38, 79, 379, 95),
    "acta_numero":        (38, 50, 379, 66),
    "empresa_nif":        (403, 734, 558, 750),
    "instalador":         (396, 687, 566, 702),
    "instalador_nif":     (429, 667, 557, 683),
    "fecha":              (420, 561, 502, 577),
}

OBSERVACIONES = (38, 128, 379, 169)

# Las seis casillas de «tipo de instalación», en el orden del impreso.
TIPOS = {
    "nueva":            (157, 563),
    "reforma":          (235, 563),
    "cambio_tension":   (289, 563),
    "cambio_titular":   (157, 554),
    "ampliacion":       (235, 554),
    "otras":            (289, 554),
}

# Las ocho filas de circuitos: la y de cada una y la x de cada columna.
FILAS_CIRCUITO = (303, 286, 269, 252, 235, 218, 201, 184)
COLUMNAS_CIRCUITO = {
    "numero":      (38, 64),
    "designacion": (67, 250),
    "seccion":     (253, 307),
    "interruptor": (310, 378),
}
ALTO_FILA = 14


def _fecha(valor) -> str:
    """La fecha como se pone a mano en el impreso: 03/10/2026."""
    texto = ("" if valor is None else str(valor)).strip()
    if len(texto) >= 10 and texto[4] == "-" and texto[7] == "-":
        return "%s/%s/%s" % (texto[8:10], texto[5:7], texto[:4])
    return texto


def _escribir(c, caja, texto, tamano=TAMANO, centrado=False):
    """Un dato dentro de su casilla, encogiendo la letra si no cabe.

    Antes que salirse de la casilla o pisar la de al lado, se baja el cuerpo
    hasta 6 puntos; por debajo de eso se recorta, que es preferible a un PDF
    con el texto montado.
    """
    texto = ("" if texto is None else str(texto)).strip()
    if not texto:
        return
    x0, y0, x1, y1 = caja
    ancho = x1 - x0 - 4
    while tamano > 6 and c.stringWidth(texto, TIPO_LETRA, tamano) > ancho:
        tamano -= 0.5
    while texto and c.stringWidth(texto, TIPO_LETRA, tamano) > ancho:
        texto = texto[:-1]
    c.setFont(TIPO_LETRA, tamano)
    base = y0 + (y1 - y0 - tamano) / 2 + 1.5
    if centrado:
        c.drawCentredString((x0 + x1) / 2, base, texto)
    else:
        c.drawString(x0 + 2, base, texto)


def _parrafo(c, caja, texto, tamano=8):
    """Las observaciones, que son varias líneas dentro de su recuadro."""
    texto = ("" if texto is None else str(texto)).strip()
    if not texto:
        return
    x0, y0, x1, y1 = caja
    c.setFont(TIPO_LETRA, tamano)
    lineas = []
    for parrafo in texto.splitlines():
        lineas.extend(simpleSplit(parrafo, TIPO_LETRA, tamano, x1 - x0 - 6) or [""])
    alto = tamano + 2
    y = y1 - alto
    for linea in lineas:
        if y < y0:
            break           # lo que no cabe en el recuadro no se pinta encima
        c.drawString(x0 + 3, y, linea)
        y -= alto


def generar(datos: dict, circuitos: list) -> bytes:
    """Devuelve el impreso oficial relleno, en PDF y aplanado."""
    import pypdf

    plantilla = pypdf.PdfReader(PLANTILLA)
    pagina = plantilla.pages[0]
    ancho = float(pagina.mediabox.width)
    alto = float(pagina.mediabox.height)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(ancho, alto))

    for campo, caja in CASILLAS.items():
        valor = datos.get(campo)
        if campo == "fecha":
            valor = _fecha(valor)
        _escribir(c, caja, valor)

    # La equis del tipo de instalación.
    marca = TIPOS.get((datos.get("tipo_instalacion") or "").strip())
    if marca:
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(marca[0] + 3.5, marca[1] - 0.5, "X")

    for i, circuito in enumerate(circuitos[:len(FILAS_CIRCUITO)]):
        y = FILAS_CIRCUITO[i]
        caja = lambda col: (COLUMNAS_CIRCUITO[col][0], y, COLUMNAS_CIRCUITO[col][1], y + ALTO_FILA)
        _escribir(c, caja("numero"), circuito.get("numero") or (i + 1), 8.5, centrado=True)
        _escribir(c, caja("designacion"), circuito.get("designacion"), 8.5)
        _escribir(c, caja("seccion"), circuito.get("seccion"), 8.5, centrado=True)
        _escribir(c, caja("interruptor"), circuito.get("interruptor"), 8.5, centrado=True)

    _parrafo(c, OBSERVACIONES, datos.get("observaciones"))

    c.save()
    buffer.seek(0)

    encima = pypdf.PdfReader(buffer).pages[0]
    pagina.merge_page(encima)
    salida = pypdf.PdfWriter()
    salida.add_page(pagina)
    # Fuera el formulario: lo que se entrega es un documento, no algo que el
    # que lo reciba pueda seguir editando.
    if "/AcroForm" in salida._root_object:
        del salida._root_object["/AcroForm"]
    fuera = io.BytesIO()
    salida.write(fuera)
    return fuera.getvalue()


def nombre_fichero(datos: dict) -> str:
    """Cómo se llama el fichero que se descarga."""
    partes = ["CIE"]
    if datos.get("numero"):
        partes.append(str(datos["numero"]))
    titular = (datos.get("titular") or "").strip()
    if titular:
        limpio = "".join(ch if ch.isalnum() or ch in " -" else "" for ch in titular)
        partes.append("-".join(limpio.split()[:3]))
    return "-".join(partes).replace("/", "-") + ".pdf"
