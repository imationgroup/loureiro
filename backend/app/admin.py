"""Endpoints del panel de gestión.

Todo cuelga de /api/admin y exige sesión, salvo el login.

Se generan los CRUD a partir de una descripción de cada tabla en vez de
escribir siete veces las mismas cuatro funciones: menos código que
mantener y ni una diferencia de comportamiento entre módulos por
despiste.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from . import db
from .auth import (ADMIN_EMAIL, ADMIN_PASSWORD_HASH, cerrar_sesion,
                   configurado, crear_sesion, limpiar_intentos,
                   registrar_intento, sesion_actual, verificar_password)

router = APIRouter(prefix="/api/admin", tags=["panel"])

# El CRUD genérico va en su propio router porque /{recurso} es un comodín
# que se tragaría rutas concretas como /dashboard. main.py lo incluye
# DESPUÉS de `router`, así que las rutas específicas ganan siempre.
router_crud = APIRouter(prefix="/api/admin", tags=["panel"])


# ═══ Login ═══════════════════════════════════════════════════════════════

class Credenciales(BaseModel):
    email: str
    password: str


def _ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "desconocida"


@router.get("/estado")
def estado():
    """Permite al panel avisar si aún no se ha configurado la contraseña."""
    return {"configurado": configurado()}


@router.post("/login")
def login(cred: Credenciales, request: Request):
    ip = _ip(request)

    if not configurado():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "El panel no tiene credenciales configuradas todavía.",
        )

    if not registrar_intento(ip):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Demasiados intentos fallidos. Prueba de nuevo en un rato.",
        )

    email_ok = cred.email.strip().lower() == ADMIN_EMAIL
    pass_ok = verificar_password(cred.password, ADMIN_PASSWORD_HASH)
    # Se comprueban ambas aunque el email ya falle, para no revelar por
    # tiempos de respuesta si el usuario existe.
    if not (email_ok and pass_ok):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email o contraseña incorrectos")

    limpiar_intentos(ip)
    token, expira = crear_sesion(ADMIN_EMAIL)
    return {"token": token, "expira": expira, "email": ADMIN_EMAIL}


@router.post("/logout")
def logout(request: Request, _: str = Depends(sesion_actual)):
    cabecera = request.headers.get("authorization", "")
    if cabecera.lower().startswith("bearer "):
        cerrar_sesion(cabecera[7:].strip())
    return {"ok": True}


# ═══ Generador de CRUD ═══════════════════════════════════════════════════

class Tabla:
    def __init__(self, nombre: str, campos: list[str], orden: str = "id DESC",
                 obligatorios: tuple[str, ...] = ()):
        self.nombre = nombre
        self.campos = campos
        self.orden = orden
        self.obligatorios = obligatorios

    def limpiar(self, datos: dict) -> dict:
        """Se queda solo con columnas conocidas: nadie inyecta campos raros."""
        return {k: v for k, v in datos.items() if k in self.campos}


TABLAS = {
    "clientes": Tabla("clientes",
        ["nombre", "nif", "email", "telefono", "direccion", "ciudad", "notas"],
        obligatorios=("nombre",)),
    "profesionales": Tabla("profesionales",
        ["nombre", "categoria", "telefono", "email", "nif", "ciudades",
         "tarifa_hora", "autonomo", "activo", "notas"],
        obligatorios=("nombre", "categoria")),
    "proveedores": Tabla("proveedores",
        ["nombre", "nif", "telefono", "email", "categoria", "notas"],
        obligatorios=("nombre",)),
    "obras": Tabla("obras",
        ["codigo", "titulo", "cliente_id", "direccion", "ciudad", "estado",
         "fecha_inicio", "fecha_fin_prevista", "fecha_fin_real",
         "importe_venta", "notas"],
        obligatorios=("titulo",)),
    "costes": Tabla("costes",
        ["obra_id", "profesional_id", "proveedor_id", "categoria", "concepto",
         "importe", "iva", "fecha", "factura_ref", "pagado", "notas"],
        orden="fecha DESC, id DESC", obligatorios=("concepto",)),
    "ingresos": Tabla("ingresos",
        ["obra_id", "cliente_id", "concepto", "importe", "iva", "fecha",
         "factura_ref", "cobrado", "notas"],
        orden="fecha DESC, id DESC", obligatorios=("concepto",)),
    "stock": Tabla("stock",
        ["referencia", "nombre", "categoria", "unidad", "cantidad", "minimo",
         "precio_unitario", "proveedor_id", "ubicacion"],
        orden="nombre COLLATE NOCASE", obligatorios=("nombre",)),
    "solicitudes": Tabla("solicitudes",
        ["nombre", "email", "telefono", "servicio", "mensaje", "estado", "notas"],
        obligatorios=("nombre",)),
}


def _tabla(recurso: str) -> Tabla:
    t = TABLAS.get(recurso)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso desconocido")
    return t


@router_crud.get("/{recurso}")
def listar(recurso: str, _: str = Depends(sesion_actual)):
    t = _tabla(recurso)
    return db.filas(f"SELECT * FROM {t.nombre} ORDER BY {t.orden}")


@router_crud.post("/{recurso}", status_code=201)
def crear(recurso: str, datos: dict[str, Any], _: str = Depends(sesion_actual)):
    t = _tabla(recurso)
    d = t.limpiar(datos)
    for campo in t.obligatorios:
        if not str(d.get(campo, "")).strip():
            raise HTTPException(422, f"Falta el campo obligatorio: {campo}")
    if not d:
        raise HTTPException(422, "No hay datos que guardar")
    cols = ", ".join(d)
    marcas = ", ".join("?" for _ in d)
    with db.tx() as con:
        cur = con.execute(f"INSERT INTO {t.nombre} ({cols}) VALUES ({marcas})",
                          tuple(d.values()))
        nuevo = cur.lastrowid
    return db.fila(f"SELECT * FROM {t.nombre} WHERE id = ?", (nuevo,))


@router_crud.put("/{recurso}/{id_}")
def actualizar(recurso: str, id_: int, datos: dict[str, Any],
               _: str = Depends(sesion_actual)):
    t = _tabla(recurso)
    d = t.limpiar(datos)
    if not d:
        raise HTTPException(422, "No hay datos que actualizar")
    sets = ", ".join(f"{k} = ?" for k in d)
    with db.tx() as con:
        cur = con.execute(f"UPDATE {t.nombre} SET {sets} WHERE id = ?",
                          (*d.values(), id_))
        if cur.rowcount == 0:
            raise HTTPException(404, "No encontrado")
    return db.fila(f"SELECT * FROM {t.nombre} WHERE id = ?", (id_,))


@router_crud.delete("/{recurso}/{id_}")
def borrar(recurso: str, id_: int, _: str = Depends(sesion_actual)):
    t = _tabla(recurso)
    with db.tx() as con:
        cur = con.execute(f"DELETE FROM {t.nombre} WHERE id = ?", (id_,))
        if cur.rowcount == 0:
            raise HTTPException(404, "No encontrado")
    return {"ok": True}


# ═══ Asignación de profesionales a obras ════════════════════════════════

class Asignacion(BaseModel):
    profesional_id: int
    rol: str | None = None
    desde: str | None = None
    hasta: str | None = None


@router.get("/obras/{obra_id}/profesionales")
def profesionales_de_obra(obra_id: int, _: str = Depends(sesion_actual)):
    return db.filas("""
        SELECT op.id, op.profesional_id, op.rol, op.desde, op.hasta,
               p.nombre, p.categoria, p.telefono, p.tarifa_hora
        FROM obra_profesionales op
        JOIN profesionales p ON p.id = op.profesional_id
        WHERE op.obra_id = ?
        ORDER BY p.nombre COLLATE NOCASE
    """, (obra_id,))


@router.post("/obras/{obra_id}/profesionales", status_code=201)
def asignar_profesional(obra_id: int, a: Asignacion, _: str = Depends(sesion_actual)):
    if not db.fila("SELECT id FROM obras WHERE id = ?", (obra_id,)):
        raise HTTPException(404, "La obra no existe")
    if not db.fila("SELECT id FROM profesionales WHERE id = ?", (a.profesional_id,)):
        raise HTTPException(404, "El profesional no existe")
    try:
        with db.tx() as con:
            con.execute("""INSERT INTO obra_profesionales
                           (obra_id, profesional_id, rol, desde, hasta)
                           VALUES (?,?,?,?,?)""",
                        (obra_id, a.profesional_id, a.rol, a.desde, a.hasta))
    except Exception:
        raise HTTPException(409, "Ese profesional ya está asignado a la obra")
    return {"ok": True}


@router.delete("/obras/{obra_id}/profesionales/{profesional_id}")
def desasignar_profesional(obra_id: int, profesional_id: int,
                           _: str = Depends(sesion_actual)):
    with db.tx() as con:
        con.execute("DELETE FROM obra_profesionales WHERE obra_id=? AND profesional_id=?",
                    (obra_id, profesional_id))
    return {"ok": True}


# ═══ Movimientos de almacén ═════════════════════════════════════════════

class Movimiento(BaseModel):
    tipo: str = Field(pattern="^(entrada|salida)$")
    cantidad: float = Field(gt=0)
    obra_id: int | None = None
    nota: str | None = None
    fecha: str | None = None


@router.get("/stock/{stock_id}/movimientos")
def movimientos(stock_id: int, _: str = Depends(sesion_actual)):
    return db.filas("""
        SELECT m.*, o.titulo AS obra
        FROM movimientos_stock m
        LEFT JOIN obras o ON o.id = m.obra_id
        WHERE m.stock_id = ? ORDER BY m.fecha DESC, m.id DESC
    """, (stock_id,))


@router.post("/stock/{stock_id}/movimientos", status_code=201)
def mover_stock(stock_id: int, m: Movimiento, _: str = Depends(sesion_actual)):
    art = db.fila("SELECT * FROM stock WHERE id = ?", (stock_id,))
    if not art:
        raise HTTPException(404, "El artículo no existe")

    delta = m.cantidad if m.tipo == "entrada" else -m.cantidad
    nueva = (art["cantidad"] or 0) + delta
    if nueva < 0:
        raise HTTPException(
            409,
            f"No hay bastante stock: quedan {art['cantidad']:g} {art['unidad']} "
            f"y se intentan sacar {m.cantidad:g}.",
        )

    with db.tx() as con:
        con.execute("""INSERT INTO movimientos_stock
                       (stock_id, tipo, cantidad, obra_id, fecha, nota)
                       VALUES (?,?,?,?,?,?)""",
                    (stock_id, m.tipo, m.cantidad, m.obra_id,
                     m.fecha or date.today().isoformat(), m.nota))
        con.execute("UPDATE stock SET cantidad = ? WHERE id = ?", (nueva, stock_id))

        # Una salida a una obra es un coste de material de esa obra.
        if m.tipo == "salida" and m.obra_id:
            importe = (art["precio_unitario"] or 0) * m.cantidad
            if importe:
                con.execute("""INSERT INTO costes
                               (obra_id, categoria, concepto, importe, iva, fecha, notas)
                               VALUES (?,?,?,?,?,?,?)""",
                            (m.obra_id, "material",
                             f"Salida de almacén: {art['nombre']} "
                             f"({m.cantidad:g} {art['unidad']})",
                             importe, 21, m.fecha or date.today().isoformat(),
                             "Generado automáticamente desde almacén"))
    return {"ok": True, "cantidad": nueva}


# ═══ Rentabilidad por obra ══════════════════════════════════════════════

@router.get("/informes/obras")
def informe_obras(_: str = Depends(sesion_actual)):
    return db.filas("""
        SELECT o.id, o.codigo, o.titulo, o.estado, o.ciudad, o.importe_venta,
               c.nombre AS cliente,
               COALESCE((SELECT SUM(importe) FROM costes   WHERE obra_id = o.id), 0) AS costes,
               COALESCE((SELECT SUM(importe) FROM ingresos WHERE obra_id = o.id), 0) AS facturado,
               (SELECT COUNT(*) FROM obra_profesionales WHERE obra_id = o.id) AS n_profesionales
        FROM obras o
        LEFT JOIN clientes c ON c.id = o.cliente_id
        ORDER BY o.id DESC
    """)


# ═══ Contabilidad ═══════════════════════════════════════════════════════

@router.get("/informes/contabilidad")
def contabilidad(anio: int | None = None, _: str = Depends(sesion_actual)):
    anio = anio or date.today().year
    a = str(anio)

    meses = db.filas("""
        SELECT mes,
               SUM(ingresos) AS ingresos, SUM(gastos) AS gastos,
               SUM(iva_repercutido) AS iva_repercutido,
               SUM(iva_soportado) AS iva_soportado
        FROM (
          SELECT strftime('%m', fecha) AS mes, importe AS ingresos, 0 AS gastos,
                 importe * iva / 100 AS iva_repercutido, 0 AS iva_soportado
          FROM ingresos WHERE strftime('%Y', fecha) = ?
          UNION ALL
          SELECT strftime('%m', fecha) AS mes, 0, importe,
                 0, importe * iva / 100
          FROM costes WHERE strftime('%Y', fecha) = ?
        )
        GROUP BY mes ORDER BY mes
    """, (a, a))

    por_categoria = db.filas("""
        SELECT categoria, SUM(importe) AS total, COUNT(*) AS n
        FROM costes WHERE strftime('%Y', fecha) = ?
        GROUP BY categoria ORDER BY total DESC
    """, (a,))

    return {
        "anio": anio,
        "meses": meses,
        "gastos_por_categoria": por_categoria,
        "totales": {
            "ingresos": db.escalar("SELECT SUM(importe) FROM ingresos WHERE strftime('%Y',fecha)=?", (a,)),
            "gastos": db.escalar("SELECT SUM(importe) FROM costes WHERE strftime('%Y',fecha)=?", (a,)),
            "iva_repercutido": db.escalar("SELECT SUM(importe*iva/100) FROM ingresos WHERE strftime('%Y',fecha)=?", (a,)),
            "iva_soportado": db.escalar("SELECT SUM(importe*iva/100) FROM costes WHERE strftime('%Y',fecha)=?", (a,)),
            "pendiente_cobro": db.escalar("SELECT SUM(importe) FROM ingresos WHERE cobrado=0"),
            "pendiente_pago": db.escalar("SELECT SUM(importe) FROM costes WHERE pagado=0"),
        },
    }


# ═══ Dashboard ══════════════════════════════════════════════════════════

@router.get("/dashboard")
def dashboard(_: str = Depends(sesion_actual)):
    hoy = date.today()
    mes = hoy.strftime("%Y-%m")

    return {
        "contadores": {
            "obras_activas": db.escalar("SELECT COUNT(*) FROM obras WHERE estado IN ('en curso','pausada')"),
            "obras_total": db.escalar("SELECT COUNT(*) FROM obras"),
            "clientes": db.escalar("SELECT COUNT(*) FROM clientes"),
            "profesionales": db.escalar("SELECT COUNT(*) FROM profesionales WHERE activo=1"),
            "solicitudes_nuevas": db.escalar("SELECT COUNT(*) FROM solicitudes WHERE estado='nueva'"),
            "stock_bajo": db.escalar("SELECT COUNT(*) FROM stock WHERE minimo > 0 AND cantidad <= minimo"),
        },
        "mes": {
            "etiqueta": mes,
            "ingresos": db.escalar("SELECT SUM(importe) FROM ingresos WHERE strftime('%Y-%m',fecha)=?", (mes,)),
            "gastos": db.escalar("SELECT SUM(importe) FROM costes WHERE strftime('%Y-%m',fecha)=?", (mes,)),
        },
        "pendientes": {
            "cobro": db.escalar("SELECT SUM(importe) FROM ingresos WHERE cobrado=0"),
            "pago": db.escalar("SELECT SUM(importe) FROM costes WHERE pagado=0"),
        },
        "evolucion": db.filas("""
            SELECT mes, SUM(ingresos) AS ingresos, SUM(gastos) AS gastos FROM (
              SELECT strftime('%Y-%m', fecha) AS mes, importe AS ingresos, 0 AS gastos FROM ingresos
              UNION ALL
              SELECT strftime('%Y-%m', fecha) AS mes, 0, importe FROM costes
            ) GROUP BY mes ORDER BY mes DESC LIMIT 6
        """),
        "obras_recientes": db.filas("""
            SELECT o.id, o.titulo, o.estado, o.ciudad, o.importe_venta,
                   c.nombre AS cliente,
                   COALESCE((SELECT SUM(importe) FROM costes WHERE obra_id=o.id),0) AS costes
            FROM obras o LEFT JOIN clientes c ON c.id=o.cliente_id
            ORDER BY o.id DESC LIMIT 5
        """),
        "solicitudes_recientes": db.filas("""
            SELECT id, nombre, servicio, estado, creado FROM solicitudes
            ORDER BY id DESC LIMIT 5
        """),
        "avisos_stock": db.filas("""
            SELECT id, nombre, cantidad, minimo, unidad FROM stock
            WHERE minimo > 0 AND cantidad <= minimo ORDER BY cantidad ASC LIMIT 8
        """),
    }
