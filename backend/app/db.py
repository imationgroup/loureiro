"""Base de datos del panel de gestión.

SQLite con la librería estándar, sin ORM. A la escala de una empresa de
reformas —un puñado de obras abiertas y unos miles de apuntes al año—
sobra de largo, el fichero se copia de una pieza para hacer copia de
seguridad y no añade otro servicio que mantener en el VPS.

El fichero vive en un volumen de Docker (ver docker-compose.yml), no
dentro del repo: el despliegue hace `git reset --hard` y no debe poder
llevarse los datos por delante.
"""

import os
import sqlite3
import threading
from contextlib import contextmanager

RUTA_DB = os.getenv("DB_PATH", "/data/loureiro.db")

_local = threading.local()


def conexion() -> sqlite3.Connection:
    """Una conexión por hilo. SQLite no permite compartirlas entre hilos."""
    if getattr(_local, "con", None) is None:
        os.makedirs(os.path.dirname(RUTA_DB), exist_ok=True)
        con = sqlite3.connect(RUTA_DB, check_same_thread=False)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        # WAL: permite leer mientras se escribe, y aguanta mejor un corte.
        con.execute("PRAGMA journal_mode = WAL")
        _local.con = con
    return _local.con


@contextmanager
def tx():
    """Transacción: confirma al salir bien, deshace si algo revienta."""
    con = conexion()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise


ESQUEMA = """
-- ── Sesiones del panel ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sesiones (
  token       TEXT PRIMARY KEY,
  email       TEXT NOT NULL,
  creada      TEXT NOT NULL,
  expira      TEXT NOT NULL
);

-- ── Clientes ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clientes (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre      TEXT NOT NULL,
  nif         TEXT,
  email       TEXT,
  telefono    TEXT,
  direccion   TEXT,
  cp          TEXT,
  ciudad      TEXT,
  provincia   TEXT DEFAULT 'Ourense',
  notas       TEXT,
  creado      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Profesionales ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profesionales (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre      TEXT NOT NULL,
  categoria   TEXT NOT NULL,
  telefono    TEXT,
  email       TEXT,
  nif         TEXT,
  ciudades    TEXT,               -- ciudades donde opera, separadas por coma
  provincia   TEXT DEFAULT 'Ourense',
  tarifa_hora REAL,
  autonomo    INTEGER NOT NULL DEFAULT 1,
  activo      INTEGER NOT NULL DEFAULT 1,
  notas       TEXT,
  creado      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Proveedores ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS proveedores (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre      TEXT NOT NULL,
  nif         TEXT,
  telefono    TEXT,
  email       TEXT,
  categoria   TEXT,
  notas       TEXT,
  creado      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Obras ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS obras (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  codigo            TEXT UNIQUE,
  titulo            TEXT NOT NULL,
  cliente_id        INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
  direccion         TEXT,
  cp                TEXT,
  ciudad            TEXT,
  provincia         TEXT DEFAULT 'Ourense',
  estado            TEXT NOT NULL DEFAULT 'presupuesto',
  fecha_inicio      TEXT,
  fecha_fin_prevista TEXT,
  fecha_fin_real    TEXT,
  importe_venta     REAL NOT NULL DEFAULT 0,   -- lo presupuestado al cliente
  notas             TEXT,
  creado            TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Profesionales asignados a cada obra
CREATE TABLE IF NOT EXISTS obra_profesionales (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  obra_id        INTEGER NOT NULL REFERENCES obras(id) ON DELETE CASCADE,
  profesional_id INTEGER NOT NULL REFERENCES profesionales(id) ON DELETE CASCADE,
  rol            TEXT,
  desde          TEXT,
  hasta          TEXT,
  UNIQUE(obra_id, profesional_id)
);

-- ── Costes ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS costes (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  obra_id        INTEGER REFERENCES obras(id) ON DELETE CASCADE,
  profesional_id INTEGER REFERENCES profesionales(id) ON DELETE SET NULL,
  proveedor_id   INTEGER REFERENCES proveedores(id) ON DELETE SET NULL,
  categoria      TEXT NOT NULL DEFAULT 'material',
  concepto       TEXT NOT NULL,
  importe        REAL NOT NULL DEFAULT 0,       -- base imponible
  iva            REAL NOT NULL DEFAULT 21,      -- porcentaje
  fecha          TEXT NOT NULL DEFAULT (date('now')),
  factura_ref    TEXT,
  pagado         INTEGER NOT NULL DEFAULT 0,
  notas          TEXT,
  creado         TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Ingresos / facturación ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ingresos (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  obra_id     INTEGER REFERENCES obras(id) ON DELETE SET NULL,
  cliente_id  INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
  concepto    TEXT NOT NULL,
  importe     REAL NOT NULL DEFAULT 0,          -- base imponible
  iva         REAL NOT NULL DEFAULT 21,
  fecha       TEXT NOT NULL DEFAULT (date('now')),
  factura_ref TEXT,
  cobrado     INTEGER NOT NULL DEFAULT 0,
  notas       TEXT,
  creado      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Almacén ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stock (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  referencia     TEXT,
  nombre         TEXT NOT NULL,
  categoria      TEXT,
  unidad         TEXT NOT NULL DEFAULT 'ud',
  cantidad       REAL NOT NULL DEFAULT 0,
  minimo         REAL NOT NULL DEFAULT 0,
  precio_unitario REAL NOT NULL DEFAULT 0,
  proveedor_id   INTEGER REFERENCES proveedores(id) ON DELETE SET NULL,
  ubicacion      TEXT,
  creado         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS movimientos_stock (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  stock_id  INTEGER NOT NULL REFERENCES stock(id) ON DELETE CASCADE,
  tipo      TEXT NOT NULL,                       -- entrada | salida
  cantidad  REAL NOT NULL,
  obra_id   INTEGER REFERENCES obras(id) ON DELETE SET NULL,
  fecha     TEXT NOT NULL DEFAULT (date('now')),
  nota      TEXT,
  creado    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Firmas de presupuestos que se editaron después ───────────────────
-- Una firma prueba que el cliente aceptó ESE documento. Si luego se cambian
-- las líneas o el precio, deja de probar lo que hay delante, pero no se tira:
-- se guarda aquí entera, con su PDF y sus huellas, por si hay que enseñar qué
-- se firmó aquel día.
CREATE TABLE IF NOT EXISTS firmas (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  presupuesto_id   INTEGER NOT NULL REFERENCES presupuestos(id) ON DELETE CASCADE,
  numero           TEXT,
  firmado_el       TEXT,
  firmante_nombre  TEXT,
  firmante_nif     TEXT,
  ip               TEXT,
  agente           TEXT,
  imagen           TEXT,
  huella           TEXT,
  hash_pdf         TEXT,
  inicio_inmediato INTEGER,
  pdf              BLOB,
  anulada_el       TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Solicitudes del formulario web ───────────────────────────────────
CREATE TABLE IF NOT EXISTS solicitudes (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre    TEXT NOT NULL,
  email     TEXT NOT NULL,
  telefono  TEXT,
  servicio  TEXT,
  mensaje   TEXT NOT NULL,
  ip        TEXT,
  estado    TEXT NOT NULL DEFAULT 'pendiente',   -- pendiente|atendida|descartada
  notas     TEXT,
  creado    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Presupuestos y facturas ──────────────────────────────────────────
-- Documentos con lineas de detalle. El total NO se guarda: se calcula
-- siempre desde las lineas, asi no puede quedar descuadrado.
CREATE TABLE IF NOT EXISTS presupuestos (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  numero      TEXT,
  cliente_id  INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
  obra_id     INTEGER REFERENCES obras(id) ON DELETE SET NULL,
  fecha       TEXT NOT NULL DEFAULT (date('now')),
  validez     INTEGER NOT NULL DEFAULT 30,      -- días
  estado      TEXT NOT NULL DEFAULT 'borrador', -- borrador|enviado|aceptado|rechazado
  notas       TEXT,
  creado      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS presupuesto_lineas (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  presupuesto_id INTEGER NOT NULL REFERENCES presupuestos(id) ON DELETE CASCADE,
  concepto       TEXT NOT NULL,
  cantidad       REAL NOT NULL DEFAULT 1,
  unidad         TEXT NOT NULL DEFAULT 'ud',
  precio         REAL NOT NULL DEFAULT 0,
  iva            REAL NOT NULL DEFAULT 21,
  orden          INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS facturas (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  numero         TEXT,
  cliente_id     INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
  obra_id        INTEGER REFERENCES obras(id) ON DELETE SET NULL,
  presupuesto_id INTEGER REFERENCES presupuestos(id) ON DELETE SET NULL,
  fecha          TEXT NOT NULL DEFAULT (date('now')),
  vencimiento    TEXT,
  estado         TEXT NOT NULL DEFAULT 'emitida', -- emitida|cobrada|anulada
  notas          TEXT,
  creado         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS factura_lineas (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  factura_id INTEGER NOT NULL REFERENCES facturas(id) ON DELETE CASCADE,
  concepto   TEXT NOT NULL,
  cantidad   REAL NOT NULL DEFAULT 1,
  unidad     TEXT NOT NULL DEFAULT 'ud',
  precio     REAL NOT NULL DEFAULT 0,
  iva        REAL NOT NULL DEFAULT 21,
  orden      INTEGER NOT NULL DEFAULT 0
);

-- ── Proformas ────────────────────────────────────────────────────────
-- Mismo formato que una factura pero SIN valor fiscal. Van en tablas propias
-- y no como un estado de la factura a propósito: así no pueden colarse en la
-- contabilidad ni ocupar números de la serie de facturas, que tiene que ser
-- correlativa y sin huecos.
CREATE TABLE IF NOT EXISTS proformas (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  numero         TEXT,
  cliente_id     INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
  obra_id        INTEGER REFERENCES obras(id) ON DELETE SET NULL,
  presupuesto_id INTEGER REFERENCES presupuestos(id) ON DELETE SET NULL,
  fecha          TEXT NOT NULL DEFAULT (date('now')),
  validez        INTEGER NOT NULL DEFAULT 30,
  estado         TEXT NOT NULL DEFAULT 'borrador', -- borrador|enviada|aceptada|facturada|anulada
  notas          TEXT,
  creado         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS proforma_lineas (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  proforma_id INTEGER NOT NULL REFERENCES proformas(id) ON DELETE CASCADE,
  concepto    TEXT NOT NULL,
  cantidad    REAL NOT NULL DEFAULT 1,
  unidad      TEXT NOT NULL DEFAULT 'ud',
  precio      REAL NOT NULL DEFAULT 0,
  iva         REAL NOT NULL DEFAULT 21,
  orden       INTEGER NOT NULL DEFAULT 0
);

-- ── Agenda ───────────────────────────────────────────────────────────
-- Las horas van en hora local de Ourense y sin zona: "2026-09-15T10:00".
CREATE TABLE IF NOT EXISTS citas (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  titulo         TEXT NOT NULL,
  tipo           TEXT NOT NULL DEFAULT 'visita',    -- visita|presupuesto|obra|revisión|otro
  inicio         TEXT NOT NULL,
  fin            TEXT,                              -- vacío = una hora
  profesional_id INTEGER REFERENCES profesionales(id) ON DELETE SET NULL,
  cliente_id     INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
  obra_id        INTEGER REFERENCES obras(id) ON DELETE SET NULL,
  direccion      TEXT,                              -- vacío = la de la obra o la del cliente
  estado         TEXT NOT NULL DEFAULT 'pendiente', -- pendiente|hecha|cancelada
  notas          TEXT,
  creado         TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Visitas ──────────────────────────────────────────────────────────
-- Lo que se ve y se apunta en casa del cliente antes de presupuestar: notas y
-- fotos. Un presupuesto puede decir de qué visita sale (presupuestos.visita_id).
CREATE TABLE IF NOT EXISTS visitas (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  titulo      TEXT,                     -- qué se quiere hacer: "reforma de baño"
  cliente_id  INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
  fecha       TEXT NOT NULL DEFAULT (date('now')),
  direccion   TEXT,
  notas       TEXT,
  usuario_id  INTEGER,
  creado      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Las fotos van en la base y no sueltas en disco, igual que el PDF firmado:
-- así la copia de seguridad sigue siendo un solo fichero. Llegan ya reducidas
-- desde el móvil (unos cientos de KB), con una miniatura aparte para que la
-- galería no tenga que bajarse las grandes.
CREATE TABLE IF NOT EXISTS visita_fotos (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  visita_id   INTEGER NOT NULL REFERENCES visitas(id) ON DELETE CASCADE,
  tipo        TEXT NOT NULL,             -- image/jpeg | image/png | image/webp
  datos       BLOB NOT NULL,
  miniatura   BLOB,
  creado      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Categorías y estados de los gastos ───────────────────────────────
-- Se editan desde el panel (Gastos > Categorías / Estados). Los gastos guardan
-- el nombre, no el id: ver gastos.py.
CREATE TABLE IF NOT EXISTS gasto_categorias (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre  TEXT NOT NULL UNIQUE COLLATE NOCASE,
  orden   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS gasto_estados (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre  TEXT NOT NULL UNIQUE COLLATE NOCASE,
  pagado  INTEGER NOT NULL DEFAULT 0,   -- si un gasto en este estado está pagado
  orden   INTEGER NOT NULL DEFAULT 0
);

-- Estados de las obras, también editables (Obras > Estados). `activa` dice si
-- una obra en ese estado cuenta como activa en el panel.
CREATE TABLE IF NOT EXISTS obra_estados (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre  TEXT NOT NULL UNIQUE COLLATE NOCASE,
  activa  INTEGER NOT NULL DEFAULT 0,
  orden   INTEGER NOT NULL DEFAULT 0
);

-- ── Notas ────────────────────────────────────────────────────────────
-- Apuntes sueltos. Pueden ir colgados de una obra (lo que se habló con el
-- cliente, lo que falta por pedir) o de ninguna.
CREATE TABLE IF NOT EXISTS notas (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  titulo      TEXT,
  contenido   TEXT NOT NULL DEFAULT '',
  obra_id     INTEGER REFERENCES obras(id) ON DELETE SET NULL,
  usuario_id  INTEGER,
  actualizado TEXT,
  creado      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Ajustes sueltos del panel (clave -> valor). Hoy solo el token secreto del
-- enlace de la agenda para Google Calendar.
CREATE TABLE IF NOT EXISTS ajustes (
  clave TEXT PRIMARY KEY,
  valor TEXT
);

-- ── Equipo: usuarios del panel ───────────────────────────────────────
-- El administrador lo ve todo; un miembro, solo los módulos de `permisos` y
-- dentro de ellos solo lo que tiene a su nombre (columna usuario_id).
CREATE TABLE IF NOT EXISTS usuarios (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  email          TEXT NOT NULL UNIQUE COLLATE NOCASE,
  nombre         TEXT,
  rol            TEXT NOT NULL DEFAULT 'miembro',   -- admin|miembro
  password_hash  TEXT,                              -- vacío = invitación sin aceptar
  activo         INTEGER NOT NULL DEFAULT 1,
  permisos       TEXT NOT NULL DEFAULT '',          -- módulos separados por comas
  profesional_id INTEGER REFERENCES profesionales(id) ON DELETE SET NULL,
  agenda_token   TEXT UNIQUE,                       -- su enlace de Google Calendar
  ultimo_acceso  TEXT,
  creado         TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Estatutos: cómo funciona la empresa, por escrito ─────────────────
-- Secciones que escribe el administrador y lee todo el equipo. El texto se
-- guarda en crudo, sin HTML: lo pinta el panel.
CREATE TABLE IF NOT EXISTS estatutos (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  titulo          TEXT NOT NULL,
  contenido       TEXT NOT NULL DEFAULT '',
  orden           INTEGER NOT NULL DEFAULT 0,
  actualizado     TEXT,
  actualizado_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);

-- Enlaces de un solo uso para crear la contraseña (invitación) o cambiarla
-- (recuperación). Se guarda la huella SHA-256 del enlace, no el enlace: quien
-- lea la base de datos no puede usarlos.
CREATE TABLE IF NOT EXISTS claves (
  token_hash  TEXT PRIMARY KEY,
  usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  tipo        TEXT NOT NULL,      -- invitacion|recuperar
  expira      TEXT NOT NULL,
  creado      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Contadores de numeración ─────────────────────────────────────────
-- La numeración NO se deduce del máximo existente. Si se deduce y alguien
-- borra el último documento, el siguiente reutiliza su número, y dos
-- documentos distintos acaban compartiendo numeración. Un contador que solo
-- sube nunca hace eso.
CREATE TABLE IF NOT EXISTS contadores (
  serie  TEXT    NOT NULL,          -- 'presupuestos'
  anio   INTEGER NOT NULL,
  ultimo INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (serie, anio)
);

CREATE INDEX IF NOT EXISTS idx_plineas ON presupuesto_lineas(presupuesto_id);
CREATE INDEX IF NOT EXISTS idx_flineas ON factura_lineas(factura_id);
CREATE INDEX IF NOT EXISTS idx_prlineas ON proforma_lineas(proforma_id);
CREATE INDEX IF NOT EXISTS idx_citas_inicio ON citas(inicio);

CREATE INDEX IF NOT EXISTS idx_costes_obra       ON costes(obra_id);
CREATE INDEX IF NOT EXISTS idx_ingresos_obra     ON ingresos(obra_id);
CREATE INDEX IF NOT EXISTS idx_obraprof_obra     ON obra_profesionales(obra_id);
CREATE INDEX IF NOT EXISTS idx_mov_stock         ON movimientos_stock(stock_id);
CREATE INDEX IF NOT EXISTS idx_solicitudes_estado ON solicitudes(estado);
CREATE INDEX IF NOT EXISTS idx_firmas_presupuesto ON firmas(presupuesto_id);
CREATE INDEX IF NOT EXISTS idx_visita_fotos       ON visita_fotos(visita_id);
CREATE INDEX IF NOT EXISTS idx_notas_obra         ON notas(obra_id);
"""


# Columnas añadidas después de la primera versión. CREATE TABLE IF NOT
# EXISTS no toca una tabla que ya existe, así que hay que añadirlas a mano.
MIGRACIONES = [
    ("clientes", "provincia", "TEXT DEFAULT 'Ourense'"),
    ("obras", "provincia", "TEXT DEFAULT 'Ourense'"),
    ("profesionales", "provincia", "TEXT DEFAULT 'Ourense'"),
    ("clientes", "cp", "TEXT"),
    ("obras", "cp", "TEXT"),
    ("ingresos", "factura_id", "INTEGER"),
    ("solicitudes", "cliente_id", "INTEGER"),
    # De qué presupuesto sale una obra. Su importe de venta se copia de
    # ahí, para que lo que se factura y lo que se firmó sean lo mismo.
    ("obras", "presupuesto_id", "INTEGER"),
    ("sesiones", "usuario_id", "INTEGER"),
    # Cancelaciones: quién las pide y por qué. Sin esto, una cita cancelada o
    # un presupuesto caído no dejan rastro de lo que pasó.
    ("citas", "cancelada_por", "TEXT"),
    ("citas", "motivo_cancelacion", "TEXT"),
    ("presupuestos", "motivo_cancelacion", "TEXT"),
    ("presupuestos", "cancelado_el", "TEXT"),
    # Firma del presupuesto por el cliente. Se guardan las pruebas de quién
    # firmó, cuándo y qué documento exacto: una firma sin eso no vale de nada
    # el día que alguien la discuta.
    ("presupuestos", "firma_token", "TEXT"),
    ("presupuestos", "firmado_el", "TEXT"),
    ("presupuestos", "firmante_nombre", "TEXT"),
    ("presupuestos", "firmante_nif", "TEXT"),
    ("presupuestos", "firma_ip", "TEXT"),
    ("presupuestos", "firma_agente", "TEXT"),
    ("presupuestos", "firma_imagen", "TEXT"),
    ("presupuestos", "firma_huella", "TEXT"),
    ("presupuestos", "firma_hash_pdf", "TEXT"),
    ("presupuestos", "firma_inicio_inmediato", "INTEGER"),
    # El PDF tal como se firmó. Se guarda entero a propósito: si el
    # presupuesto se tocara después, lo firmado sigue siendo esto.
    ("presupuestos", "firma_pdf", "BLOB"),
    # De qué visita sale el presupuesto: las fotos y notas de la toma de datos.
    ("presupuestos", "visita_id", "INTEGER"),
    # Estado del gasto (pendiente, pagado… editable). `pagado` se sigue
    # rellenando a juego, que es lo que suma contabilidad.
    ("costes", "estado", "TEXT"),
    # Una nota puede ser de un cliente además de (o en vez de) una obra.
    ("notas", "cliente_id", "INTEGER"),
]

# Punto de partida de las listas editables de gastos. Solo se siembran si la
# tabla está vacía: después son del usuario.
CATEGORIAS_GASTO = ["material", "mano de obra", "maquinaria", "residuos", "subcontrata",
                    "desplazamiento", "otros"]
ESTADOS_GASTO = [("pendiente", 0), ("pagado", 1)]
ESTADOS_OBRA = [("presupuesto", 0), ("en curso", 1), ("pausada", 1), ("terminada", 0),
                ("cancelada", 0)]

# Tablas donde cada fila tiene responsable (usuario_id). Lo que ya existía
# antes del equipo queda con el responsable vacío, que es lo del
# administrador: nadie más lo ve hasta que él lo reparta.
TABLAS_CON_RESPONSABLE = ("clientes", "obras", "citas", "presupuestos", "proformas",
                          "facturas", "costes", "ingresos", "solicitudes", "visitas",
                          "notas")
MIGRACIONES += [(t, "usuario_id", "INTEGER") for t in TABLAS_CON_RESPONSABLE]


# Estados de las solicitudes, simplificados el 2026-09-10 a tres: pendiente,
# atendida y descartada. Los antiguos se traducen al arrancar; es idempotente,
# así que da igual cuántas veces se ejecute.
ESTADOS_SOLICITUD_ANTIGUOS = {
    "nueva": "pendiente",
    "contactada": "atendida",
    "presupuestada": "atendida",
    "ganada": "atendida",
    "perdida": "descartada",
}


def migrar():
    con = conexion()
    for tabla, columna, tipo in MIGRACIONES:
        existentes = {r["name"] for r in con.execute(f"PRAGMA table_info({tabla})")}
        if columna not in existentes:
            con.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")
    # Los índices van aquí y no en el esquema: la columna puede no existir
    # todavía cuando se ejecuta el CREATE TABLE de una base antigua.
    for tabla in TABLAS_CON_RESPONSABLE:
        con.execute(f"CREATE INDEX IF NOT EXISTS idx_{tabla}_usuario ON {tabla}(usuario_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_presupuestos_firma ON presupuestos(firma_token)")
    for viejo, nuevo in ESTADOS_SOLICITUD_ANTIGUOS.items():
        con.execute("UPDATE solicitudes SET estado = ? WHERE estado = ?", (nuevo, viejo))
    # Enlace obra ↔ presupuesto en los dos lados. Antes se escribía solo el de
    # donde se elegía, y la otra pantalla no lo veía. El presupuesto elegido en
    # una obra apunta a ella; y una obra sin presupuesto toma el único (no
    # cancelado) que apunte a ella.
    con.execute("""UPDATE presupuestos SET obra_id = (
                     SELECT o.id FROM obras o WHERE o.presupuesto_id = presupuestos.id LIMIT 1)
                   WHERE obra_id IS NULL AND EXISTS (
                     SELECT 1 FROM obras o WHERE o.presupuesto_id = presupuestos.id)""")
    con.execute("""UPDATE obras SET presupuesto_id = (
                     SELECT p.id FROM presupuestos p WHERE p.obra_id = obras.id AND p.estado != 'cancelado')
                   WHERE presupuesto_id IS NULL AND (
                     SELECT COUNT(*) FROM presupuestos p
                     WHERE p.obra_id = obras.id AND p.estado != 'cancelado') = 1""")
    # El importe de una obra es la base de su presupuesto, sin IVA, como los
    # gastos con los que se compara (antes se copiaba el total con IVA y el
    # margen salía inflado). Se recalcula siempre: si el presupuesto se retocó,
    # la obra queda al día. Las obras sin presupuesto llevan el suyo a mano.
    con.execute("""UPDATE obras SET importe_venta = (
                     SELECT ROUND(SUM(cantidad * precio), 2) FROM presupuesto_lineas l
                     WHERE l.presupuesto_id = obras.presupuesto_id)
                   WHERE presupuesto_id IS NOT NULL AND EXISTS (
                     SELECT 1 FROM presupuesto_lineas l WHERE l.presupuesto_id = obras.presupuesto_id)""")
    # Listas de gastos: se siembran la primera vez, y se añaden las categorías
    # que ya usaba algún gasto para que ninguno se quede con una que no existe.
    if not con.execute("SELECT COUNT(*) FROM gasto_categorias").fetchone()[0]:
        for i, nombre in enumerate(CATEGORIAS_GASTO, 1):
            con.execute("INSERT INTO gasto_categorias (nombre, orden) VALUES (?,?)", (nombre, i))
    con.execute("""INSERT OR IGNORE INTO gasto_categorias (nombre, orden)
                   SELECT DISTINCT categoria, 100 FROM costes
                   WHERE categoria IS NOT NULL AND trim(categoria) != ''""")
    if not con.execute("SELECT COUNT(*) FROM gasto_estados").fetchone()[0]:
        for i, (nombre, pagado) in enumerate(ESTADOS_GASTO, 1):
            con.execute("INSERT INTO gasto_estados (nombre, pagado, orden) VALUES (?,?,?)",
                        (nombre, pagado, i))
    if not con.execute("SELECT COUNT(*) FROM obra_estados").fetchone()[0]:
        for i, (nombre, activa) in enumerate(ESTADOS_OBRA, 1):
            con.execute("INSERT INTO obra_estados (nombre, activa, orden) VALUES (?,?,?)",
                        (nombre, activa, i))
    con.execute("""INSERT OR IGNORE INTO obra_estados (nombre, orden)
                   SELECT DISTINCT estado, 100 FROM obras
                   WHERE estado IS NOT NULL AND trim(estado) != ''""")
    # Gastos sin estado (los de antes, o uno que se colara sin él): el primer
    # estado que diga lo mismo que su casilla de pagado.
    con.execute("""UPDATE costes SET estado = (
                     SELECT nombre FROM gasto_estados e WHERE e.pagado = costes.pagado
                     ORDER BY orden, id LIMIT 1)
                   WHERE estado IS NULL OR estado = ''""")
    # Un presupuesto no se "rechaza", se cancela, y al cancelarlo se pide el
    # motivo. Los que quedaron rechazados pasan al nombre nuevo.
    con.execute("UPDATE presupuestos SET estado = 'cancelado' WHERE estado = 'rechazado'")
    con.commit()


# Punto de partida de cada serie. El valor es el ÚLTIMO número usado, así
# que el siguiente presupuesto de 2026 sale con el 087: el 2026-09-14 el
# usuario pidió empezar ahí (antes empezaba en el 078).
#
# Se aplica como mínimo, no como valor fijo: sube el contador si va por
# detrás, pero nunca lo baja. Si ya se han hecho presupuestos por encima del
# 086, la serie sigue desde el último y no repite números.
SEMILLAS_CONTADOR = [("presupuestos", 2026, 86)]


def inicializar():
    con = conexion()
    con.executescript(ESQUEMA)
    for serie, anio, ultimo in SEMILLAS_CONTADOR:
        con.execute(
            "INSERT OR IGNORE INTO contadores (serie, anio, ultimo) VALUES (?,?,?)",
            (serie, anio, ultimo))
        con.execute(
            "UPDATE contadores SET ultimo = MAX(ultimo, ?) WHERE serie = ? AND anio = ?",
            (ultimo, serie, anio))
    con.commit()
    migrar()


def filas(sql: str, params=()) -> list[dict]:
    return [dict(r) for r in conexion().execute(sql, params).fetchall()]


def fila(sql: str, params=()) -> dict | None:
    r = conexion().execute(sql, params).fetchone()
    return dict(r) if r else None


def escalar(sql: str, params=(), por_defecto=0):
    r = conexion().execute(sql, params).fetchone()
    if not r or r[0] is None:
        return por_defecto
    return r[0]
