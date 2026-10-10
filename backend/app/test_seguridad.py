"""Test de seguridad del cuadro de una vivienda.

La lista de la guía «Pruebas de seguridad en un cuadro de vivienda» para ir
marcando en la casa del cliente. De lo marcado sale una puntuación, los
defectos clasificados como en el reglamento (muy graves, graves y leves) y
qué hacer con cada uno, y todo eso se entrega en un PDF.

No es un certificado: es una revisión con polímetro y pinza, y el propio
informe lo dice. Vive junto a los certificados porque lo hace la misma gente
en la misma visita, y por eso comparte su permiso.

Lo marcado se guarda como JSON en una sola columna: son cuarenta puntos que
siempre van juntos y que nadie va a consultar de uno en uno. La nota y el
recuento de defectos sí se guardan aparte, para pintar la lista sin
recalcular cada test.
"""

import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from . import db, test_seguridad_pdf
from . import test_seguridad_puntos as puntos
from .auth import (comprobar_referencias, es_admin, exigir, filtro_responsable,
                   sesion_actual)
from .documentos import siguiente_numero

# Antes que el CRUD genérico, que se tragaría la ruta como si fuese una tabla.
router = APIRouter(prefix="/api/admin/tests-seguridad", tags=["tests de seguridad"])

MODULO = "certificados"

CAMPOS = ("cliente_id", "obra_id", "titular", "direccion", "instalador",
          "observaciones", "fecha")


class Respuestas(BaseModel):
    estados: dict[str, str] = {}
    valores: dict[str, str] = {}


class Test(BaseModel):
    titular: str = Field(min_length=1, max_length=160)
    direccion: str | None = Field(default=None, max_length=200)
    instalador: str | None = Field(default=None, max_length=120)
    observaciones: str | None = Field(default=None, max_length=2000)
    fecha: str | None = None
    cliente_id: int | None = None
    obra_id: int | None = None
    usuario_id: int | None = None
    respuestas: Respuestas = Respuestas()


def _visible(u: dict, id_: int) -> dict:
    """El test, si es de quien lo pide. 404 y no 403: ni existe."""
    cond, params = filtro_responsable(u)
    fila = db.fila(f"SELECT * FROM tests_seguridad WHERE id = ? AND {cond}", (id_, *params))
    if not fila:
        raise HTTPException(404, "No encontrado")
    return fila


def _respuestas(fila: dict) -> dict:
    try:
        return puntos.limpiar(json.loads(fila.get("respuestas") or "{}"))
    except ValueError:
        return puntos.limpiar({})


def _resumen(resultado: dict) -> dict:
    """Lo que se guarda en columnas para la lista."""
    return {"puntuacion": resultado["puntuacion"], "nivel": resultado["nivel"],
            "muy_graves": resultado["n"][puntos.MUY_GRAVE],
            "graves": resultado["n"][puntos.GRAVE],
            "leves": resultado["n"][puntos.LEVE],
            "pendientes": resultado["pendientes"]}


@router.get("")
def listar(u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
    cond, params = filtro_responsable(u, "t")
    return db.filas(f"""
        SELECT t.id, t.numero, t.fecha, t.titular, t.direccion, t.instalador, t.cliente_id,
               t.puntuacion, t.nivel, t.muy_graves, t.graves, t.leves, t.pendientes,
               {db.sql_nombre_cliente("cl")} AS cliente
        FROM tests_seguridad t
        LEFT JOIN clientes cl ON cl.id = t.cliente_id
        WHERE {cond}
        ORDER BY t.fecha DESC, t.id DESC""", params)


@router.get("/plantilla")
def plantilla(u: dict = Depends(sesion_actual)):
    """Los puntos de la lista, para pintar el formulario."""
    exigir(u, MODULO)
    return puntos.plantilla()


@router.post("/evaluar")
def evaluar(respuestas: Respuestas, u: dict = Depends(sesion_actual)):
    """La nota de lo que hay marcado ahora mismo, sin guardar nada."""
    exigir(u, MODULO)
    return puntos.evaluar(respuestas.model_dump())


@router.get("/{id_}")
def ver(id_: int, u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
    test = _visible(u, id_)
    test["respuestas"] = _respuestas(test)
    test["resultado"] = puntos.evaluar(test["respuestas"])
    return test


@router.post("", status_code=201)
def crear(test: Test, u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
    datos = test.model_dump()
    comprobar_referencias(u, datos)
    # Lo que se crea es de quien lo crea; el administrador puede repartirlo.
    datos["usuario_id"] = datos.get("usuario_id") if es_admin(u) else u["id"]
    datos["fecha"] = datos.get("fecha") or date.today().isoformat()
    respuestas = puntos.limpiar(datos["respuestas"])
    resumen = _resumen(puntos.evaluar(respuestas))

    columnas = list(CAMPOS) + ["usuario_id"] + list(resumen) + ["respuestas", "numero"]
    with db.tx() as con:
        numero = siguiente_numero(con, "tests_seguridad", int(datos["fecha"][:4]))
        valores = ([datos.get(k) for k in CAMPOS] + [datos["usuario_id"]] +
                   list(resumen.values()) + [json.dumps(respuestas), numero])
        nuevo = con.execute(
            "INSERT INTO tests_seguridad (%s) VALUES (%s)"
            % (", ".join(columnas), ", ".join("?" * len(columnas))), valores).lastrowid
    return ver(nuevo, u)


@router.put("/{id_}")
def actualizar(id_: int, test: Test, u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
    existente = _visible(u, id_)
    datos = test.model_dump()
    comprobar_referencias(u, datos, existente)
    if not es_admin(u):
        datos["usuario_id"] = existente["usuario_id"]
    datos["fecha"] = datos.get("fecha") or existente["fecha"]
    respuestas = puntos.limpiar(datos["respuestas"])
    resumen = _resumen(puntos.evaluar(respuestas))

    columnas = list(CAMPOS) + ["usuario_id"] + list(resumen) + ["respuestas"]
    with db.tx() as con:
        con.execute("UPDATE tests_seguridad SET %s WHERE id = ?"
                    % ", ".join("%s = ?" % k for k in columnas),
                    [datos.get(k) for k in CAMPOS] + [datos["usuario_id"]] +
                    list(resumen.values()) + [json.dumps(respuestas), id_])
    return ver(id_, u)


@router.delete("/{id_}", status_code=204)
def borrar(id_: int, u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
    _visible(u, id_)
    with db.tx() as con:
        con.execute("DELETE FROM tests_seguridad WHERE id = ?", (id_,))
    return Response(status_code=204)


@router.get("/{id_}/pdf")
def descargar(id_: int, u: dict = Depends(sesion_actual)):
    """El informe para el cliente: nota, defectos y recomendaciones."""
    exigir(u, MODULO)
    test = _visible(u, id_)
    respuestas = _respuestas(test)
    datos = test_seguridad_pdf.generar(test, respuestas, puntos.evaluar(respuestas))
    return Response(content=datos, media_type="application/pdf",
                    headers={"Content-Disposition":
                             'attachment; filename="%s.pdf"' % (test.get("numero") or "TS-%d" % id_)})
