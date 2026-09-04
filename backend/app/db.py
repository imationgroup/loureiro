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

-- ── Solicitudes del formulario web ───────────────────────────────────
CREATE TABLE IF NOT EXISTS solicitudes (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre    TEXT NOT NULL,
  email     TEXT NOT NULL,
  telefono  TEXT,
  servicio  TEXT,
  mensaje   TEXT NOT NULL,
  ip        TEXT,
  estado    TEXT NOT NULL DEFAULT 'nueva',       -- nueva|contactada|presupuestada|ganada|perdida
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

CREATE INDEX IF NOT EXISTS idx_plineas ON presupuesto_lineas(presupuesto_id);
CREATE INDEX IF NOT EXISTS idx_flineas ON factura_lineas(factura_id);

CREATE INDEX IF NOT EXISTS idx_costes_obra       ON costes(obra_id);
CREATE INDEX IF NOT EXISTS idx_ingresos_obra     ON ingresos(obra_id);
CREATE INDEX IF NOT EXISTS idx_obraprof_obra     ON obra_profesionales(obra_id);
CREATE INDEX IF NOT EXISTS idx_mov_stock         ON movimientos_stock(stock_id);
CREATE INDEX IF NOT EXISTS idx_solicitudes_estado ON solicitudes(estado);
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
]


def migrar():
    con = conexion()
    for tabla, columna, tipo in MIGRACIONES:
        existentes = {r["name"] for r in con.execute(f"PRAGMA table_info({tabla})")}
        if columna not in existentes:
            con.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")
    con.commit()


def inicializar():
    con = conexion()
    con.executescript(ESQUEMA)
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
