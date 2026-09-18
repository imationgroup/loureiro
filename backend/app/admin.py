"""Endpoints del panel de gestión.

Todo cuelga de /api/admin y exige sesión, salvo el login.

Se generan los CRUD a partir de una descripción de cada tabla en vez de
escribir siete veces las mismas cuatro funciones: menos código que
mantener y ni una diferencia de comportamiento entre módulos por
despiste.

Cada petición llega con el usuario de la sesión. Con él se decide a qué
módulos entra (ver auth.puede) y, en las tablas con responsable, qué filas
ve: el administrador todas, un miembro solo las suyas. Una fila de otra
persona responde 404 y no 403, para no confirmar siquiera que existe.
"""

from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from . import db
from .agenda import validar_cita
from .documentos import totales
from .auth import (HASH_FALSO, comprobar_referencias, configurado, crear_sesion,
                   cerrar_sesion, es_admin, exigir, filtro_responsable, fijar_responsable,
                   limpiar_intentos, publico, puede, registrar_intento, sesion_actual,
                   usuario_por_email, verificar_password)

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

    u = usuario_por_email(cred.email)
    # Se calcula el hash aunque el correo no exista, contra uno que nadie
    # conoce, para no revelar por tiempos de respuesta si el usuario existe.
    pass_ok = verificar_password(cred.password, (u or {}).get("password_hash") or HASH_FALSO)
    if not (u and u["activo"] and u.get("password_hash") and pass_ok):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email o contraseña incorrectos")

    limpiar_intentos(ip)
    token, expira = crear_sesion(u)
    return {"token": token, "expira": expira, "email": u["email"], "usuario": publico(u)}


@router.post("/logout")
def logout(request: Request, _: dict = Depends(sesion_actual)):
    cabecera = request.headers.get("authorization", "")
    if cabecera.lower().startswith("bearer "):
        cerrar_sesion(cabecera[7:].strip())
    return {"ok": True}


# ═══ Generador de CRUD ═══════════════════════════════════════════════════

class Tabla:
    def __init__(self, nombre: str, campos: list[str], orden: str = "id DESC",
                 obligatorios: tuple[str, ...] = (), validar=None,
                 modulo: str = "", lectura: tuple[str, ...] = (),
                 responsable: bool = False, defectos: dict | None = None,
                 presentes: tuple[str, ...] = ()):
        self.nombre = nombre
        self.campos = campos
        self.orden = orden
        self.obligatorios = obligatorios
        # Comprobaciones propias de la tabla, además de los obligatorios.
        # Recibe (datos nuevos, registro guardado o None al crear).
        self.validar = validar
        # Módulo que hace falta para crear, editar o borrar.
        self.modulo = modulo
        # Módulos con los que se puede leer la lista. Es más amplio que el de
        # escritura porque otros módulos la necesitan para sus desplegables:
        # quien hace presupuestos tiene que poder elegir entre sus clientes
        # aunque no tenga la pestaña Clientes.
        self.lectura = lectura or (modulo,)
        # Si cada fila tiene responsable (usuario_id) y un miembro solo ve las suyas.
        self.responsable = responsable
        # Qué poner en columnas NOT NULL que la base no rellena sola. El
        # formulario de la web siempre manda correo y mensaje; una solicitud
        # apuntada a mano en el panel puede no tenerlos, y sin esto el INSERT
        # revienta contra la restricción en vez de guardarse a medias.
        self.defectos = defectos or {}
        # Campos que el alta tiene que traer, aunque sea vacíos a propósito. Un
        # gasto dice a qué obra va o que no va a ninguna (gasto de empresa);
        # lo que no vale es que no diga nada.
        self.presentes = presentes

    def limpiar(self, datos: dict, creando: bool = False) -> dict:
        """Se queda solo con columnas conocidas: nadie inyecta campos raros.

        Al crear se descartan además los valores nulos. Varias columnas son
        NOT NULL con valor por defecto (iva 21, fecha de hoy, importe 0…):
        mandar NULL explícito revienta la restricción en vez de dejar que
        el valor por defecto haga su trabajo. Al editar sí se conservan,
        para poder vaciar un campo a propósito.
        """
        d = {k: v for k, v in datos.items() if k in self.campos}
        if creando:
            d = {k: v for k, v in d.items() if v is not None and v != ""}
        return d


# Quién necesita leer cada lista para sus desplegables.
_LEE_CLIENTES = ("clientes", "obras", "agenda", "presupuestos", "proformas", "facturas",
                 "costes", "solicitudes", "visitas")
_LEE_OBRAS = ("obras", "agenda", "presupuestos", "proformas", "facturas", "costes", "stock",
              "notas")

TABLAS = {
    "clientes": Tabla("clientes",
        ["nombre", "nif", "email", "telefono", "direccion", "cp", "ciudad",
         "provincia", "notas"],
        obligatorios=("nombre",),
        modulo="clientes", lectura=_LEE_CLIENTES, responsable=True),
    "profesionales": Tabla("profesionales",
        ["nombre", "categoria", "telefono", "email", "nif", "ciudades",
         "provincia", "tarifa_hora", "autonomo", "activo", "notas"],
        obligatorios=("nombre", "categoria"),
        modulo="profesionales", lectura=("profesionales", "agenda", "obras", "costes")),
    "proveedores": Tabla("proveedores",
        ["nombre", "nif", "telefono", "email", "categoria", "notas"],
        obligatorios=("nombre",),
        modulo="proveedores", lectura=("proveedores", "stock", "costes")),
    "obras": Tabla("obras",
        ["codigo", "titulo", "cliente_id", "presupuesto_id", "direccion", "cp",
         "ciudad", "provincia", "estado", "fecha_inicio", "fecha_fin_prevista",
         "fecha_fin_real", "importe_venta", "notas"],
        obligatorios=("titulo",),
        modulo="obras", lectura=_LEE_OBRAS, responsable=True),
    "costes": Tabla("costes",
        ["obra_id", "profesional_id", "proveedor_id", "categoria", "concepto",
         "importe", "iva", "fecha", "factura_ref", "pagado", "notas"],
        orden="fecha DESC, id DESC", obligatorios=("concepto",), presentes=("obra_id",),
        modulo="costes", responsable=True),
    "ingresos": Tabla("ingresos",
        ["obra_id", "cliente_id", "concepto", "importe", "iva", "fecha",
         "factura_ref", "cobrado", "notas"],
        orden="fecha DESC, id DESC", obligatorios=("concepto",),
        modulo="facturas", lectura=("facturas", "contabilidad"), responsable=True),
    "stock": Tabla("stock",
        ["referencia", "nombre", "categoria", "unidad", "cantidad", "minimo",
         "precio_unitario", "proveedor_id", "ubicacion"],
        orden="nombre COLLATE NOCASE", obligatorios=("nombre",),
        modulo="stock"),
    "solicitudes": Tabla("solicitudes",
        ["nombre", "email", "telefono", "servicio", "mensaje", "estado",
         "notas", "cliente_id"],
        obligatorios=("nombre",), defectos={"email": "", "mensaje": ""},
        modulo="solicitudes", responsable=True),
    "citas": Tabla("citas",
        ["titulo", "tipo", "inicio", "fin", "profesional_id", "cliente_id",
         "obra_id", "direccion", "estado", "notas",
         "cancelada_por", "motivo_cancelacion"],
        orden="inicio DESC", obligatorios=("titulo", "inicio"),
        validar=validar_cita,
        modulo="agenda", responsable=True),
    # La lista, el borrado y las fotos van en visitas.py; aquí solo el alta y
    # la edición. Sin cliente no hay visita: es a casa de alguien.
    "visitas": Tabla("visitas",
        ["titulo", "cliente_id", "fecha", "direccion", "notas"],
        orden="fecha DESC, id DESC", obligatorios=("cliente_id",),
        validar=lambda d, _: _con_cliente(d),
        modulo="visitas", lectura=("visitas", "presupuestos"), responsable=True),
    # Lo último que se ha tocado, arriba: una nota vieja que se retoca vuelve
    # a estar al día.
    "notas": Tabla("notas",
        ["titulo", "contenido", "obra_id"],
        orden="COALESCE(actualizado, creado) DESC, id DESC", obligatorios=("contenido",),
        validar=lambda d, _: _sellar_nota(d),
        modulo="notas", responsable=True),
}


def _sellar_nota(d: dict):
    """Una nota vacía no es una nota; y cada cambio deja la hora."""
    if "contenido" in d and not str(d["contenido"] or "").strip():
        raise HTTPException(422, "La nota está vacía.")
    d["actualizado"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _con_cliente(d: dict):
    """Al editar una visita tampoco se le puede quitar el cliente."""
    if "cliente_id" in d and not d["cliente_id"]:
        raise HTTPException(422, "Una visita tiene que ser de un cliente.")


def _importe_de_obra(d: dict):
    """El importe de una obra lo pone el presupuesto, no quien teclea.

    En el panel no hay casilla que escribir: se elige el presupuesto y el
    importe sale de sus líneas. Aquí se vuelve a calcular en vez de fiarse
    del número que llegue, porque si el presupuesto se retoca luego, lo que
    vale es lo que pone el presupuesto y no lo que se guardó aquel día.

    Quitar el presupuesto no pone la obra a cero: se queda con el importe que
    tuviera. Las obras de antes de esto llevan el suyo escrito a mano y
    borrarlo por un descuido sería perder el dato.
    """
    if "presupuesto_id" not in d:
        return
    if not d["presupuesto_id"]:
        d.pop("importe_venta", None)
        return
    lineas = db.filas("SELECT * FROM presupuesto_lineas WHERE presupuesto_id = ?",
                      (d["presupuesto_id"],))
    d["importe_venta"] = totales(lineas)["total"]


def _tabla(recurso: str) -> Tabla:
    t = TABLAS.get(recurso)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso desconocido")
    return t


def _visibles(t: Tabla, u: dict) -> tuple[str, tuple]:
    """Condición WHERE con las filas de esa tabla que puede ver el usuario.

    Las citas son la excepción: un miembro vinculado a una ficha de
    profesional ve también las citas donde figura como profesional, aunque
    las haya creado otra persona. Es su agenda.
    """
    if not t.responsable:
        return "1=1", ()
    if t.nombre == "citas" and not es_admin(u) and u.get("profesional_id"):
        return "(usuario_id = ? OR profesional_id = ?)", (u["id"], u["profesional_id"])
    return filtro_responsable(u)


def _fila_visible(t: Tabla, u: dict, id_: int) -> dict:
    cond, params = _visibles(t, u)
    fila = db.fila(f"SELECT * FROM {t.nombre} WHERE id = ? AND {cond}", (id_, *params))
    if not fila:
        raise HTTPException(404, "No encontrado")
    return fila


@router_crud.get("/{recurso}")
def listar(recurso: str, u: dict = Depends(sesion_actual)):
    t = _tabla(recurso)
    exigir(u, *t.lectura)
    cond, params = _visibles(t, u)
    return db.filas(f"SELECT * FROM {t.nombre} WHERE {cond} ORDER BY {t.orden}", params)


@router_crud.post("/{recurso}", status_code=201)
def crear(recurso: str, datos: dict[str, Any], u: dict = Depends(sesion_actual)):
    t = _tabla(recurso)
    exigir(u, t.modulo)
    d = t.limpiar(datos, creando=True)
    for campo in t.presentes:
        if campo not in datos:
            raise HTTPException(422, f"Falta el campo obligatorio: {campo}")
    for campo in t.obligatorios:
        if not str(d.get(campo, "")).strip():
            raise HTTPException(422, f"Falta el campo obligatorio: {campo}")
    if not d:
        raise HTTPException(422, "No hay datos que guardar")
    for col, porDefecto in t.defectos.items():
        d.setdefault(col, porDefecto)
    if t.responsable:
        fijar_responsable(u, datos, d, creando=True)
    # Una cita nueva de un miembro vinculado a un profesional es suya como
    # profesional si no dice otra cosa: si no, no le saldría en su calendario.
    if t.nombre == "citas" and not es_admin(u) and u.get("profesional_id") \
            and not d.get("profesional_id"):
        d["profesional_id"] = u["profesional_id"]
    comprobar_referencias(u, d)
    if t.nombre == "obras":
        _importe_de_obra(d)
    if t.validar:
        t.validar(d, None)
    cols = ", ".join(d)
    marcas = ", ".join("?" for _ in d)
    with db.tx() as con:
        cur = con.execute(f"INSERT INTO {t.nombre} ({cols}) VALUES ({marcas})",
                          tuple(d.values()))
        nuevo = cur.lastrowid
    return db.fila(f"SELECT * FROM {t.nombre} WHERE id = ?", (nuevo,))


@router_crud.put("/{recurso}/{id_}")
def actualizar(recurso: str, id_: int, datos: dict[str, Any],
               u: dict = Depends(sesion_actual)):
    t = _tabla(recurso)
    exigir(u, t.modulo)
    existente = _fila_visible(t, u, id_)
    d = t.limpiar(datos)
    if t.responsable:
        fijar_responsable(u, datos, d, creando=False)
    if not d:
        raise HTTPException(422, "No hay datos que actualizar")
    comprobar_referencias(u, d, existente)
    if t.nombre == "obras":
        _importe_de_obra(d)
    if t.validar:
        t.validar(d, existente)
    sets = ", ".join(f"{k} = ?" for k in d)
    with db.tx() as con:
        cur = con.execute(f"UPDATE {t.nombre} SET {sets} WHERE id = ?",
                          (*d.values(), id_))
        if cur.rowcount == 0:
            raise HTTPException(404, "No encontrado")
    return db.fila(f"SELECT * FROM {t.nombre} WHERE id = ?", (id_,))


@router_crud.delete("/{recurso}/{id_}")
def borrar(recurso: str, id_: int, u: dict = Depends(sesion_actual)):
    t = _tabla(recurso)
    exigir(u, t.modulo)
    _fila_visible(t, u, id_)
    with db.tx() as con:
        cur = con.execute(f"DELETE FROM {t.nombre} WHERE id = ?", (id_,))
        if cur.rowcount == 0:
            raise HTTPException(404, "No encontrado")
    return {"ok": True}


# ═══ Notificaciones (la campanita del panel) ════════════════════════════

@router.get("/notificaciones")
def notificaciones(u: dict = Depends(sesion_actual)):
    """Lo que está pendiente de atender.

    Por ahora solo las solicitudes pendientes: todas para el administrador y
    las que tiene asignadas para un miembro. La respuesta es genérica
    (tipo, título, detalle, fecha y vista a la que lleva) para poder añadir
    más avisos —facturas vencidas, stock bajo mínimo— sin tocar el panel.
    Tiene que ir en el router de rutas concretas: en el genérico, /{recurso}
    se la tragaría como si "notificaciones" fuese una tabla.
    """
    if not puede(u, "solicitudes"):
        return {"total": 0, "items": []}
    cond, params = filtro_responsable(u)
    pendientes = db.filas(
        f"""SELECT id, nombre, servicio, creado FROM solicitudes
            WHERE estado = 'pendiente' AND {cond} ORDER BY creado DESC, id DESC""", params)
    items = [{
        "tipo": "solicitud",
        "id": s["id"],
        "titulo": s["nombre"],
        "detalle": s["servicio"] or "Sin especificar",
        "fecha": s["creado"],
        "vista": "solicitudes",
    } for s in pendientes[:20]]
    return {"total": len(pendientes), "items": items}


SALTO = chr(10)   # separador dentro de las notas del cliente


# ═══ Solicitud → cliente ════════════════════════════════════════════════

def _cliente_que_encaja(u: dict, email: str, nombre: str,
                        por_nombre: bool) -> tuple[dict | None, str]:
    """Busca si esa persona ya está fichada, entre los clientes que ve u.

    Por correo siempre: es el dato que no se repite. Por nombre exacto solo
    en las altas hechas a mano, donde el nombre se escribe contra el
    desplegable de clientes y teclear el de uno que ya está es querer ese.
    Desde la web no se mira el nombre: dos tocayos no son la misma persona y
    fusionarlos mezclaría los datos de dos desconocidos.

    Un miembro solo busca entre sus propios clientes: si mirase los de todos,
    acabaría enlazado con la ficha de un compañero.
    """
    cond, params = filtro_responsable(u)
    email = (email or "").strip()
    if email:
        ya = db.fila(
            f"SELECT * FROM clientes WHERE lower(trim(email)) = lower(?) AND {cond}",
            (email, *params))
        if ya:
            return ya, "email"
    nombre = (nombre or "").strip()
    if por_nombre and nombre:
        ya = db.fila(
            f"SELECT * FROM clientes WHERE lower(trim(nombre)) = lower(?) AND {cond}",
            (nombre, *params))
        if ya:
            return ya, "nombre"
    return None, ""


def _enlazar_con_cliente(s: dict, u: dict, origen: str = "una solicitud de la web",
                         por_nombre: bool = False, atender: bool = True) -> dict:
    """Deja la solicitud colgando de un cliente: el que ya hay, o uno nuevo.

    No crea un cliente a ciegas. Si esa solicitud ya se convirtió, devuelve el
    cliente que salió de ella; y si ya existe uno que encaje —lo normal cuando
    alguien rellena el formulario dos veces, o cuando un cliente de siempre
    pide otra cosa— se enlaza con el que hay en vez de duplicarlo. Un fichero
    de clientes con la misma persona tres veces es justo lo que hace inútil el
    listado.
    """
    cond, params = filtro_responsable(u)
    if s.get("cliente_id"):
        ya = db.fila(f"SELECT * FROM clientes WHERE id = ? AND {cond}",
                     (s["cliente_id"], *params))
        if ya:
            return {"cliente": ya, "creado": False, "motivo": "ya_convertida"}

    email = (s.get("email") or "").strip()
    existente, como = _cliente_que_encaja(u, email, s.get("nombre") or "", por_nombre)

    # El cliente nuevo es de quien lleva la solicitud.
    responsable = s.get("usuario_id") if es_admin(u) else u["id"]

    with db.tx() as con:
        if existente:
            cliente_id, creado = existente["id"], False
        else:
            # El mensaje se guarda en las notas: es el contexto de por qué esta
            # persona está en la ficha, y si no se copia aquí se queda solo en
            # la solicitud.
            notas = "Alta desde " + origen
            if s.get("servicio"):
                notas += f" ({s['servicio']})"
            if s.get("mensaje"):
                notas += "." + SALTO + SALTO + s["mensaje"]
            cur = con.execute(
                """INSERT INTO clientes (nombre, email, telefono, notas, usuario_id)
                   VALUES (?,?,?,?,?)""",
                (s["nombre"], email or None, s.get("telefono"), notas, responsable))
            cliente_id, creado = cur.lastrowid, True

        con.execute("UPDATE solicitudes SET cliente_id = ? WHERE id = ?",
                    (cliente_id, s["id"]))
        # Si seguía pendiente, pasa a atendida: convertirla en cliente ya es
        # haberla atendido, y dejarla pendiente falsea la campanita del panel.
        # Las que se apuntan a mano no: se apuntan justo porque están por hacer.
        if atender and s.get("estado") == "pendiente":
            con.execute("UPDATE solicitudes SET estado = 'atendida' WHERE id = ?",
                        (s["id"],))

    return {"cliente": db.fila("SELECT * FROM clientes WHERE id = ?", (cliente_id,)),
            "creado": creado,
            "motivo": "nuevo" if creado else (como + "_existente")}


@router.post("/solicitudes/{id_}/convertir", status_code=201)
def convertir_en_cliente(id_: int, u: dict = Depends(sesion_actual)):
    """Da de alta como cliente a quien ha mandado una solicitud."""
    exigir(u, "solicitudes")
    return _enlazar_con_cliente(_fila_visible(TABLAS["solicitudes"], u, id_), u)


@router.post("/solicitudes", status_code=201)
def alta_solicitud(datos: dict[str, Any], u: dict = Depends(sesion_actual)):
    """Apunta una solicitud desde el panel, ya con su cliente detrás.

    Las de la web traen un nombre suelto y ya se verá luego quién es. Las que
    se apuntan aquí son llamadas de teléfono o encargos de boca, y ahí el
    nombre se escribe contra el desplegable de clientes: si se elige uno, llega
    su `cliente_id`; si se escribe un nombre que no está, se le abre ficha con
    lo que se haya puesto. Así la visita que se agende después ya tiene a quién
    colgarse, sin pasar por «Pasar a cliente».

    Se guarda primero la solicitud y luego el cliente, y no al revés: si algo
    falla por el camino queda una solicitud sin cliente, que se arregla con un
    botón, y no un cliente suelto que nadie sabe de dónde salió.

    Tiene que ir en el router de rutas concretas para ganarle al CRUD
    genérico, al que se le pasa el trabajo de guardar.
    """
    exigir(u, "solicitudes")
    elegido = datos.get("cliente_id")
    if elegido not in (None, ""):
        # El desplegable solo ofrece clientes que esta persona ve, pero lo que
        # llega es un número cualquiera: si apunta a una ficha que no existe,
        # la solicitud se quedaría colgada de la nada y la lista enseñaría un
        # "#412" que no se puede abrir.
        try:
            elegido = int(elegido)
        except (TypeError, ValueError):
            raise HTTPException(422, "Cliente no válido.")
        _fila_visible(TABLAS["clientes"], u, elegido)
        datos["cliente_id"] = elegido
    fila = crear("solicitudes", datos, u)
    if fila.get("cliente_id"):
        return fila
    _enlazar_con_cliente(fila, u, origen="una solicitud apuntada en el panel",
                         por_nombre=True, atender=False)
    return db.fila("SELECT * FROM solicitudes WHERE id = ?", (fila["id"],))


# ═══ Asignación de profesionales a obras ════════════════════════════════

class Asignacion(BaseModel):
    profesional_id: int
    rol: str | None = None
    desde: str | None = None
    hasta: str | None = None


def _obra_visible(u: dict, obra_id: int) -> dict:
    return _fila_visible(TABLAS["obras"], u, obra_id)


@router.get("/obras/{obra_id}/profesionales")
def profesionales_de_obra(obra_id: int, u: dict = Depends(sesion_actual)):
    exigir(u, "obras")
    _obra_visible(u, obra_id)
    return db.filas("""
        SELECT op.id, op.profesional_id, op.rol, op.desde, op.hasta,
               p.nombre, p.categoria, p.telefono, p.tarifa_hora
        FROM obra_profesionales op
        JOIN profesionales p ON p.id = op.profesional_id
        WHERE op.obra_id = ?
        ORDER BY p.nombre COLLATE NOCASE
    """, (obra_id,))


@router.post("/obras/{obra_id}/profesionales", status_code=201)
def asignar_profesional(obra_id: int, a: Asignacion, u: dict = Depends(sesion_actual)):
    exigir(u, "obras")
    _obra_visible(u, obra_id)
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
                           u: dict = Depends(sesion_actual)):
    exigir(u, "obras")
    _obra_visible(u, obra_id)
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
def movimientos(stock_id: int, u: dict = Depends(sesion_actual)):
    exigir(u, "stock")
    # El almacén es de todos, pero el nombre de la obra a la que fue el
    # material solo se enseña si la obra es de quien mira.
    visible = "1" if es_admin(u) else "o.usuario_id = ?"
    params = () if es_admin(u) else (u["id"],)
    return db.filas(f"""
        SELECT m.*, CASE WHEN {visible} THEN o.titulo END AS obra
        FROM movimientos_stock m
        LEFT JOIN obras o ON o.id = m.obra_id
        WHERE m.stock_id = ? ORDER BY m.fecha DESC, m.id DESC
    """, (*params, stock_id))


@router.post("/stock/{stock_id}/movimientos", status_code=201)
def mover_stock(stock_id: int, m: Movimiento, u: dict = Depends(sesion_actual)):
    exigir(u, "stock")
    art = db.fila("SELECT * FROM stock WHERE id = ?", (stock_id,))
    if not art:
        raise HTTPException(404, "El artículo no existe")
    obra = _obra_visible(u, m.obra_id) if m.obra_id else None

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

        # Una salida a una obra es un coste de material de esa obra, y lo
        # lleva quien lleva la obra.
        if m.tipo == "salida" and obra:
            importe = (art["precio_unitario"] or 0) * m.cantidad
            if importe:
                con.execute("""INSERT INTO costes
                               (obra_id, categoria, concepto, importe, iva, fecha, notas, usuario_id)
                               VALUES (?,?,?,?,?,?,?,?)""",
                            (m.obra_id, "material",
                             f"Salida de almacén: {art['nombre']} "
                             f"({m.cantidad:g} {art['unidad']})",
                             importe, 21, m.fecha or date.today().isoformat(),
                             "Generado automáticamente desde almacén", obra.get("usuario_id")))
    return {"ok": True, "cantidad": nueva}


# ═══ Rentabilidad por obra ══════════════════════════════════════════════

@router.get("/informes/obras")
def informe_obras(u: dict = Depends(sesion_actual)):
    exigir(u, "obras")
    cond, params = filtro_responsable(u, "o")
    return db.filas(f"""
        SELECT o.id, o.codigo, o.titulo, o.estado, o.ciudad, o.importe_venta, o.usuario_id,
               c.nombre AS cliente,
               COALESCE((SELECT SUM(importe) FROM costes   WHERE obra_id = o.id), 0) AS costes,
               COALESCE((SELECT SUM(importe) FROM ingresos WHERE obra_id = o.id), 0) AS facturado,
               (SELECT COUNT(*) FROM obra_profesionales WHERE obra_id = o.id) AS n_profesionales
        FROM obras o
        LEFT JOIN clientes c ON c.id = o.cliente_id
        WHERE {cond}
        ORDER BY o.id DESC
    """, params)


# ═══ Contabilidad ═══════════════════════════════════════════════════════

@router.get("/informes/contabilidad")
def contabilidad(anio: int | None = None, u: dict = Depends(sesion_actual)):
    """Resultado, IVA y pendientes. Un miembro ve la de lo que lleva él."""
    exigir(u, "contabilidad")
    anio = anio or date.today().year
    a = str(anio)
    f, p = filtro_responsable(u)

    meses = db.filas(f"""
        SELECT mes,
               SUM(ingresos) AS ingresos, SUM(gastos) AS gastos,
               SUM(iva_repercutido) AS iva_repercutido,
               SUM(iva_soportado) AS iva_soportado
        FROM (
          SELECT strftime('%m', fecha) AS mes, importe AS ingresos, 0 AS gastos,
                 importe * iva / 100 AS iva_repercutido, 0 AS iva_soportado
          FROM ingresos WHERE strftime('%Y', fecha) = ? AND {f}
          UNION ALL
          SELECT strftime('%m', fecha) AS mes, 0, importe,
                 0, importe * iva / 100
          FROM costes WHERE strftime('%Y', fecha) = ? AND {f}
        )
        GROUP BY mes ORDER BY mes
    """, (a, *p, a, *p))

    por_categoria = db.filas(f"""
        SELECT categoria, SUM(importe) AS total, COUNT(*) AS n
        FROM costes WHERE strftime('%Y', fecha) = ? AND {f}
        GROUP BY categoria ORDER BY total DESC
    """, (a, *p))

    return {
        "anio": anio,
        "meses": meses,
        "gastos_por_categoria": por_categoria,
        "totales": {
            "ingresos": db.escalar(f"SELECT SUM(importe) FROM ingresos WHERE strftime('%Y',fecha)=? AND {f}", (a, *p)),
            "gastos": db.escalar(f"SELECT SUM(importe) FROM costes WHERE strftime('%Y',fecha)=? AND {f}", (a, *p)),
            "iva_repercutido": db.escalar(f"SELECT SUM(importe*iva/100) FROM ingresos WHERE strftime('%Y',fecha)=? AND {f}", (a, *p)),
            "iva_soportado": db.escalar(f"SELECT SUM(importe*iva/100) FROM costes WHERE strftime('%Y',fecha)=? AND {f}", (a, *p)),
            "pendiente_cobro": db.escalar(f"SELECT SUM(importe) FROM ingresos WHERE cobrado=0 AND {f}", p),
            "pendiente_pago": db.escalar(f"SELECT SUM(importe) FROM costes WHERE pagado=0 AND {f}", p),
        },
    }


# ═══ Dashboard ══════════════════════════════════════════════════════════

@router.get("/dashboard")
def dashboard(u: dict = Depends(sesion_actual)):
    """El resumen. Lo tiene todo el mundo, cada uno con sus números."""
    hoy = date.today()
    mes = hoy.strftime("%Y-%m")
    f, p = filtro_responsable(u)
    fo, po = filtro_responsable(u, "o")
    ve_solicitudes = puede(u, "solicitudes")
    ve_stock = puede(u, "stock")

    return {
        "contadores": {
            "obras_activas": db.escalar(f"SELECT COUNT(*) FROM obras WHERE estado IN ('en curso','pausada') AND {f}", p),
            "obras_total": db.escalar(f"SELECT COUNT(*) FROM obras WHERE {f}", p),
            "clientes": db.escalar(f"SELECT COUNT(*) FROM clientes WHERE {f}", p),
            "profesionales": db.escalar("SELECT COUNT(*) FROM profesionales WHERE activo=1"),
            "solicitudes_nuevas": db.escalar(f"SELECT COUNT(*) FROM solicitudes WHERE estado='pendiente' AND {f}", p)
                                  if ve_solicitudes else None,
            "stock_bajo": db.escalar("SELECT COUNT(*) FROM stock WHERE minimo > 0 AND cantidad <= minimo")
                          if ve_stock else None,
        },
        "mes": {
            "etiqueta": mes,
            "ingresos": db.escalar(f"SELECT SUM(importe) FROM ingresos WHERE strftime('%Y-%m',fecha)=? AND {f}", (mes, *p)),
            "gastos": db.escalar(f"SELECT SUM(importe) FROM costes WHERE strftime('%Y-%m',fecha)=? AND {f}", (mes, *p)),
        },
        "pendientes": {
            "cobro": db.escalar(f"SELECT SUM(importe) FROM ingresos WHERE cobrado=0 AND {f}", p),
            "pago": db.escalar(f"SELECT SUM(importe) FROM costes WHERE pagado=0 AND {f}", p),
        },
        "evolucion": db.filas(f"""
            SELECT mes, SUM(ingresos) AS ingresos, SUM(gastos) AS gastos FROM (
              SELECT strftime('%Y-%m', fecha) AS mes, importe AS ingresos, 0 AS gastos FROM ingresos WHERE {f}
              UNION ALL
              SELECT strftime('%Y-%m', fecha) AS mes, 0, importe FROM costes WHERE {f}
            ) GROUP BY mes ORDER BY mes DESC LIMIT 6
        """, (*p, *p)),
        "obras_recientes": db.filas(f"""
            SELECT o.id, o.titulo, o.estado, o.ciudad, o.importe_venta,
                   c.nombre AS cliente,
                   COALESCE((SELECT SUM(importe) FROM costes WHERE obra_id=o.id),0) AS costes
            FROM obras o LEFT JOIN clientes c ON c.id=o.cliente_id
            WHERE {fo}
            ORDER BY o.id DESC LIMIT 5
        """, po),
        "solicitudes_recientes": db.filas(f"""
            SELECT id, nombre, servicio, estado, creado FROM solicitudes
            WHERE {f} ORDER BY id DESC LIMIT 5
        """, p) if ve_solicitudes else [],
        "avisos_stock": db.filas("""
            SELECT id, nombre, cantidad, minimo, unidad FROM stock
            WHERE minimo > 0 AND cantidad <= minimo ORDER BY cantidad ASC LIMIT 8
        """) if ve_stock else [],
    }
