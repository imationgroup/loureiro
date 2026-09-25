"""Genera las imágenes de redes sociales (Open Graph) con la marca de la casa.

Son las tarjetas que salen al pegar un enlace en WhatsApp, Facebook o LinkedIn:
la portada y una por cada página de servicio. Se dibujan aquí en vez de a mano
para que cambiar un color o un texto sea volver a ejecutar esto.

    python scripts/generar-og.py

Necesita Pillow para dibujar y fonttools + brotli para leer las tipografías de
la web, que están en woff2 y son variables: de cada una se saca una versión
estática del grosor que hace falta, en una carpeta temporal.

    pip install pillow fonttools brotli
"""

import os
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTES = os.path.join(RAIZ, "assets", "fonts")

# ── Los colores de la marca ───────────────────────────────────────────────
GRAFITO = (30, 37, 51)        # #1E2533, el fondo
AMARILLO = (242, 168, 28)     # #F2A81C, el acento
BLANCO = (255, 255, 255)
APAGADO = (154, 162, 177)     # #9AA2B1

ANCHO, ALTO = 1200, 630

# El logotipo, en un lienzo de 40: el tejado de una casa y, dentro, la puerta.
# Son trazos, no siluetas: el grosor va proporcional al tamaño que se pida.
CASA = [(6, 30), (6, 10), (20, 4), (34, 10), (34, 30)]
PUERTA = [(14, 30), (14, 20), (26, 20), (26, 30)]

# Cada tarjeta: fichero, las dos líneas del titular y el renglón de debajo.
TARJETAS = [
    ("og-image.jpg", "Tu reforma entera,", "con una sola llamada.",
     "Reformas integrales y servicios para el hogar en Ourense."),
    # La de ofertas es la que más se comparte por WhatsApp: lleva el precio
    # en el titular, que es lo que se ve en la miniatura del chat.
    ("og/ofertas.jpg", "Tiramos la casa", "por la ventana.",
     "Aire 1.000 € · Ducha 700 € · Eléctrica 2.700 € · Sin IVA"),

    ("og/reformas-integrales-ourense.jpg", "Reformas integrales", "en Ourense",
     "Demolición, instalaciones, acabados y limpieza final"),
    ("og/electricista-ourense.jpg", "Electricista", "en Ourense",
     "Cuadros, averías, iluminación y boletines"),
    ("og/albanileria-ourense.jpg", "Albañilería", "en Ourense",
     "Baños, cocinas, tabiquería y fachadas"),
    ("og/aire-acondicionado-ourense.jpg", "Aire acondicionado", "en Ourense",
     "Split, multisplit, conductos y aerotermia"),
    ("og/estufas-de-pellets-ourense.jpg", "Estufas de pellets", "en Ourense",
     "Instalación, salida de humos y mantenimiento"),
    ("og/pintores-ourense.jpg", "Pintores", "en Ourense",
     "Interior, exterior, alisado de gotelé y antihumedad"),
    ("og/limpieza-fin-de-obra-ourense.jpg", "Limpieza de fin de obra", "en Ourense",
     "Pisos y locales listos para entrar"),
]

# Las ofertas van con la otra tarjeta: fichero, titular, precio, el renglón de
# debajo y qué icono se dibuja en la cuña.
OFERTAS = [
    ("og/oferta-aire.jpg", "Aire frío y calor", "1.000 €",
     "Máquina e instalación · Ourense", "aire"),
    ("og/oferta-ducha.jpg", "Bañera por ducha", "700 €",
     "En dos días · Escombros incluidos", "ducha"),
    ("og/oferta-electrica.jpg", "Reforma eléctrica", "2.700 €",
     "Cuadro y cableado nuevos · Boletín", "rayo"),
]


def estatica(woff2: str, peso: int, carpeta: str) -> str:
    """Saca de la fuente variable una versión de un solo grosor, para Pillow."""
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    destino = os.path.join(carpeta, "%s-%d.ttf" % (os.path.basename(woff2)[:-6], peso))
    if not os.path.exists(destino):
        f = TTFont(os.path.join(FUENTES, woff2))
        instancer.instantiateVariableFont(f, {"wght": peso}, inplace=True)
        f.flavor = None
        f.save(destino)
    return destino


def dibujar_marca(lienzo, x, y, lado, color_casa, color_puerta, grosor=3.0):
    """El logotipo en su sitio, escalado desde el lienzo de 40."""
    d = ImageDraw.Draw(lienzo, "RGBA")
    u = lado / 40.0
    for puntos, color in ((CASA, color_casa), (PUERTA, color_puerta)):
        d.line([(x + px * u, y + py * u) for px, py in puntos],
               fill=color, width=max(1, round(grosor * u)), joint="curve")


def texto_espaciado(d, xy, texto, fuente, color, espacio):
    """Pillow no sabe de interletraje: se escribe letra a letra."""
    x, y = xy
    for letra in texto:
        d.text((x, y), letra, font=fuente, fill=color)
        x += d.textlength(letra, font=fuente) + espacio
    return x


def fondo() -> Image.Image:
    im = Image.new("RGB", (ANCHO, ALTO), GRAFITO)
    d = ImageDraw.Draw(im, "RGBA")
    # Rejilla muy tenue, como la de la web.
    for x in range(0, ANCHO, 74):
        d.line([(x, 0), (x, ALTO)], fill=(255, 255, 255, 12))
    for y in range(0, ALTO, 74):
        d.line([(0, y), (ANCHO, y)], fill=(255, 255, 255, 12))

    # Resplandor dorado arriba a la derecha, en anillos que se van apagando.
    brillo = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    db = ImageDraw.Draw(brillo)
    cx, cy, r = 1010, 130, 340
    for i in range(r, 0, -8):
        alfa = int(30 * (1 - i / r) ** 2)
        db.ellipse([cx - i, cy - i, cx + i, cy + i], fill=AMARILLO + (alfa,))
    im = Image.alpha_composite(im.convert("RGBA"), brillo).convert("RGB")

    # El logotipo, enorme y casi transparente, de marca de agua.
    agua = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    dibujar_marca(agua, 850, 250, 300, (255, 255, 255, 14), AMARILLO + (30,))
    return Image.alpha_composite(im.convert("RGBA"), agua).convert("RGB")


def tarjeta(linea1: str, linea2: str, pie: str, tipos: dict) -> Image.Image:
    im = fondo()
    d = ImageDraw.Draw(im, "RGBA")

    # Marca arriba a la izquierda.
    dibujar_marca(im, 80, 74, 52, BLANCO, AMARILLO)
    d.text((150, 78), "Loureiro", font=tipos["marca"], fill=BLANCO)
    ancho_marca = d.textlength("Loureiro", font=tipos["marca"])
    d.text((150 + ancho_marca, 78), "soluciones", font=tipos["marca_sub"], fill=APAGADO)

    # Antetítulo con su rayita, como los de la web.
    d.line([(80, 218), (106, 218)], fill=AMARILLO, width=3)
    texto_espaciado(d, (120, 207), "OURENSE Y PROVINCIA", tipos["antetitulo"], AMARILLO, 3.2)

    d.text((78, 248), linea1, font=tipos["titular"], fill=BLANCO)
    d.text((78, 338), linea2, font=tipos["titular"], fill=AMARILLO)
    d.text((80, 448), pie, font=tipos["pie"], fill=APAGADO)

    # Renglón de abajo: dónde estamos y el teléfono.
    d.text((80, 530), "loureirosoluciones.es", font=tipos["web"], fill=BLANCO)
    ancho_web = d.textlength("loureirosoluciones.es", font=tipos["web"])
    d.text((80 + ancho_web + 22, 530), "·", font=tipos["web"], fill=APAGADO)
    d.text((80 + ancho_web + 46, 530), "603 905 128", font=tipos["web"], fill=APAGADO)

    d.rectangle([0, ALTO - 14, ANCHO, ALTO], fill=AMARILLO)
    return im


def icono(d, clase, cx, cy, lado, color):
    """Un dibujo simple, de trazo grueso, que se reconozca en miniatura."""
    u = lado / 100.0
    g = max(3, round(7 * u))

    def r(x0, y0, x1, y1, radio=0):
        caja = [cx + x0 * u, cy + y0 * u, cx + x1 * u, cy + y1 * u]
        if radio:
            d.rounded_rectangle(caja, radius=radio * u, outline=color, width=g)
        else:
            d.rectangle(caja, outline=color, width=g)

    def l(x0, y0, x1, y1):
        d.line([cx + x0 * u, cy + y0 * u, cx + x1 * u, cy + y1 * u], fill=color, width=g)

    if clase == "aire":
        # Split de pared y el aire saliendo.
        r(-50, -46, 50, -6, 10)
        l(-36, -20, 36, -20)
        for i, x in enumerate((-30, 0, 30)):
            l(x, 6, x - 10, 30)
            l(x - 10, 30, x, 52)
    elif clase == "ducha":
        # Alcachofa, chorro y plato.
        l(-4, -52, -4, -30)
        d.ellipse([cx - 30 * u, cy - 34 * u, cx + 22 * u, cy - 18 * u], outline=color, width=g)
        for x in (-22, -8, 6):
            l(x, -10, x - 6, 26)
        r(-52, 34, 52, 50, 6)
    else:
        # Rayo.
        d.polygon([(cx + 14 * u, cy - 54 * u), (cx - 34 * u, cy + 6 * u),
                   (cx - 4 * u, cy + 6 * u), (cx - 16 * u, cy + 54 * u),
                   (cx + 34 * u, cy - 8 * u), (cx + 2 * u, cy - 8 * u)], fill=color)


def tarjeta_oferta(titular, precio, pie, clase, tipos):
    """La que se comparte: precio enorme, cuña amarilla y teléfono."""
    im = fondo()
    d = ImageDraw.Draw(im, "RGBA")

    # Cuña amarilla a la derecha, con el icono dentro.
    d.polygon([(842, 0), (ANCHO, 0), (ANCHO, ALTO), (722, ALTO)], fill=AMARILLO)
    icono(d, clase, 992, 300, 260, GRAFITO)

    # Marca arriba.
    dibujar_marca(im, 80, 60, 44, BLANCO, AMARILLO)
    d.text((138, 62), "Loureiro", font=tipos["marca_of"], fill=BLANCO)
    ancho_marca = d.textlength("Loureiro", font=tipos["marca_of"])
    d.text((138 + ancho_marca, 62), "soluciones", font=tipos["marca_of_sub"], fill=APAGADO)

    # Etiqueta de oferta.
    texto = "OFERTA"
    ancho_texto = d.textlength(texto, font=tipos["pill"]) + 6 * 5.5
    d.rounded_rectangle([80, 148, 80 + ancho_texto + 44, 196], radius=24, fill=AMARILLO)
    texto_espaciado(d, (102, 158), texto, tipos["pill"], GRAFITO, 5.5)

    d.text((78, 214), titular, font=tipos["titular_of"], fill=BLANCO)
    d.text((80, 300), "desde", font=tipos["desde"], fill=APAGADO)
    d.text((78, 330), precio, font=tipos["precio"], fill=AMARILLO)
    d.text((80, 492), pie, font=tipos["pie_of"], fill=(201, 205, 212))

    # Franja de abajo con el teléfono, en amarillo para que se lea de lejos.
    d.rectangle([0, ALTO - 62, ANCHO, ALTO], fill=AMARILLO)
    d.text((80, ALTO - 50), "603 905 128", font=tipos["tel"], fill=GRAFITO)
    ancho_tel = d.textlength("603 905 128", font=tipos["tel"])
    d.text((80 + ancho_tel + 20, ALTO - 48), "· loureirosoluciones.es",
           font=tipos["tel_sub"], fill=GRAFITO)
    return im


def main():
    with tempfile.TemporaryDirectory() as tmp:
        archivo800 = estatica("archivo-var-latin.woff2", 800, tmp)
        archivo600 = estatica("archivo-var-latin.woff2", 600, tmp)
        archivo500 = estatica("archivo-var-latin.woff2", 500, tmp)
        inter400 = estatica("inter-var-latin.woff2", 400, tmp)
        tipos = {
            "marca": ImageFont.truetype(archivo800, 30),
            "marca_sub": ImageFont.truetype(archivo500, 30),
            "antetitulo": ImageFont.truetype(archivo600, 19),
            "titular": ImageFont.truetype(archivo800, 74),
            "pie": ImageFont.truetype(inter400, 27),
            "web": ImageFont.truetype(archivo600, 22),
            # Las de la tarjeta de oferta.
            "marca_of": ImageFont.truetype(archivo800, 24),
            "marca_of_sub": ImageFont.truetype(archivo500, 24),
            "pill": ImageFont.truetype(archivo800, 22),
            "titular_of": ImageFont.truetype(archivo800, 66),
            "desde": ImageFont.truetype(inter400, 30),
            "precio": ImageFont.truetype(archivo800, 148),
            "pie_of": ImageFont.truetype(inter400, 28),
            "tel": ImageFont.truetype(archivo800, 26),
            "tel_sub": ImageFont.truetype(archivo600, 22),
        }
        for nombre, l1, l2, pie in TARJETAS:
            destino = os.path.join(RAIZ, "assets", "img", *nombre.split("/"))
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            im = tarjeta(l1, l2, pie, tipos)
            im.save(destino, "JPEG", quality=88, optimize=True, progressive=True)
            print("  %-46s %5.0f KB" % (nombre, os.path.getsize(destino) / 1024))

        for nombre, titular, precio, pie, clase in OFERTAS:
            destino = os.path.join(RAIZ, "assets", "img", *nombre.split("/"))
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            im = tarjeta_oferta(titular, precio, pie, clase, tipos)
            im.save(destino, "JPEG", quality=88, optimize=True, progressive=True)
            print("  %-46s %5.0f KB" % (nombre, os.path.getsize(destino) / 1024))
    print("Tarjetas listas.")


if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        sys.exit("Falta una dependencia (%s). Instala: pip install pillow fonttools brotli" % e.name)
