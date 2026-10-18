"""Si la empresa opera con IVA o sin él.

Con IVA (lo normal): el IVA que se cobra se le debe a Hacienda y el que se
paga se recupera, así que no es de la empresa. Ingresos, gastos y márgenes se
cuentan sin IVA, sobre la base.

Sin IVA: la empresa ni lo cobra aparte ni se lo devuelven. Lo que pone el
tique es lo que de verdad sale de caja, y lo que paga el cliente es lo que
entra. Todo se cuenta por el total: 260 € de gastos con IVA son 260 € de
gasto, y 1.000 € cobrados son 1.000 € de ingreso.

Los datos no cambian al tocar el ajuste: cada apunte sigue guardando su base
y su porcentaje de IVA, y aquí solo se decide qué se suma. Por eso se puede
cambiar en cualquier momento y volver atrás sin perder nada.
"""

from . import db

CLAVE = "opera_con_iva"


def con_iva() -> bool:
    """Por defecto, con IVA: es como ha funcionado siempre el panel."""
    fila = db.fila("SELECT valor FROM ajustes WHERE clave = ?", (CLAVE,))
    return (fila or {}).get("valor") != "0"


def fijar(valor: bool):
    with db.tx() as con:
        con.execute("INSERT INTO ajustes (clave, valor) VALUES (?, ?) "
                    "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
                    (CLAVE, "1" if valor else "0"))


def imp(alias: str = "") -> str:
    """SQL del importe de un gasto o un ingreso tal como cuenta en el resultado."""
    p = f"{alias}." if alias else ""
    return f"{p}importe" if con_iva() else f"({p}importe * (1 + {p}iva / 100.0))"


def linea(alias: str = "l") -> str:
    """SQL del importe de una línea de presupuesto o factura."""
    base = f"{alias}.cantidad * {alias}.precio"
    return base if con_iva() else f"({base} * (1 + {alias}.iva / 100.0))"


def venta(alias: str = "o") -> str:
    """SQL de lo presupuestado en una obra.

    La obra guarda la base de su presupuesto. Sin IVA cuenta el total, que se
    saca de las líneas del presupuesto; las obras sin presupuesto (las de
    antes, con el importe escrito a mano) se quedan con su importe.
    """
    if con_iva():
        return f"{alias}.importe_venta"
    return (f"COALESCE((SELECT SUM(l.cantidad * l.precio * (1 + l.iva / 100.0)) "
            f"FROM presupuesto_lineas l WHERE l.presupuesto_id = {alias}.presupuesto_id), "
            f"{alias}.importe_venta)")
