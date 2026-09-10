"""Datos de la empresa: una sola fuente para los PDF y las páginas legales.

El NIF viene del .env (EMPRESA_NIF) y no del código. Así el mismo valor sale
en presupuestos, proformas, facturas, aviso legal y política de privacidad,
y cambiarlo es tocar el servidor y recrear el contenedor, sin desplegar.
"""

import os

NIF = (os.getenv("EMPRESA_NIF") or "").strip().upper()

EMPRESA = {
    "nombre": "Loureiro Soluciones, S.L.",
    "marca": "Loureiro soluciones",
    "nif": NIF,
    "direccion": "OU-0517, 32910 San Ciprián de Viñas, Ourense",
    "telefono": "603 905 128",
    "email": "contacto@loureirosoluciones.es",
    "web": "loureirosoluciones.es",
}
