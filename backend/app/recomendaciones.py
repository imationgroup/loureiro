"""Hojas de recomendaciones: lo que el electricista ve y lo que aconseja.

Tras una visita o durante una obra, el electricista escribe lo que ha visto y
cada cosa que recomienda hacer, con su prioridad y el porqué. Sale un PDF
pensado para el cliente, que no es electricista: primero lo urgente, y en
cada punto qué se vio, qué se recomienda y por qué.

No es un certificado ni un presupuesto. Vive junto a los certificados porque
lo hace la misma gente en la misma visita, y por eso comparte su permiso,
como el test de seguridad.

Las recomendaciones van como JSON en una sola columna: siempre se leen y se
escriben juntas. El recuento por prioridad sí va aparte, para la lista.
"""

import json
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from . import db, recomendaciones_pdf
from .auth import (comprobar_referencias, es_admin, exigir, filtro_responsable,
                   sesion_actual)
from .documentos import siguiente_numero

router = APIRouter(prefix="/api/admin/recomendaciones", tags=["recomendaciones"])

MODULO = "certificados"

CAMPOS = ("cliente_id", "obra_id", "visita_id", "titular", "direccion", "autor",
          "visto", "conclusion", "fecha")

# De más a menos urgente: es también el orden en que salen en el PDF.
PRIORIDADES = ("urgente", "recomendada", "mejora")
COLUMNA = {"urgente": "urgentes", "recomendada": "recomendadas", "mejora": "mejoras"}
MAX_PUNTOS = 40


class Punto(BaseModel):
    prioridad: Literal["urgente", "recomendada", "mejora"] = "recomendada"
    titulo: str = Field(min_length=1, max_length=200)
    visto: str | None = Field(default=None, max_length=2000)
    porque: str | None = Field(default=None, max_length=2000)
    coste: str | None = Field(default=None, max_length=120)


class Hoja(BaseModel):
    titular: str = Field(min_length=1, max_length=160)
    direccion: str | None = Field(default=None, max_length=200)
    autor: str | None = Field(default=None, max_length=120)
    visto: str | None = Field(default=None, max_length=4000)
    conclusion: str | None = Field(default=None, max_length=2000)
    fecha: str | None = None
    cliente_id: int | None = None
    obra_id: int | None = None
    visita_id: int | None = None
    usuario_id: int | None = None
    puntos: list[Punto] = Field(default=[], max_length=MAX_PUNTOS)


def _visible(u: dict, id_: int) -> dict:
    """La hoja, si es de quien la pide. 404 y no 403: ni existe."""
    cond, params = filtro_responsable(u)
    fila = db.fila(f"SELECT * FROM recomendaciones WHERE id = ? AND {cond}", (id_, *params))
    if not fila:
        raise HTTPException(404, "No encontrado")
    return fila


def _puntos(fila: dict) -> list[dict]:
    try:
        lista = json.loads(fila.get("puntos") or "[]")
    except ValueError:
        return []
    return [p for p in lista if isinstance(p, dict) and p.get("titulo")]


def _limpios(puntos: list[Punto]) -> list[dict]:
    """Sin espacios sobrantes, y los vacíos de verdad como None."""
    salida = []
    for p in puntos:
        d = {k: (v.strip() or None) if isinstance(v, str) else v for k, v in p.model_dump().items()}
        if d["titulo"]:
            salida.append(d)
    return salida


def _recuento(puntos: list[dict]) -> dict:
    return {COLUMNA[k]: sum(1 for p in puntos if p["prioridad"] == k) for k in PRIORIDADES}


@router.get("")
def listar(u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
    cond, params = filtro_responsable(u, "r")
    return db.filas(f"""
        SELECT r.id, r.numero, r.fecha, r.titular, r.direccion, r.autor, r.cliente_id,
               r.obra_id, r.visita_id, r.urgentes, r.recomendadas, r.mejoras,
               {db.sql_nombre_cliente("cl")} AS cliente
        FROM recomendaciones r
        LEFT JOIN clientes cl ON cl.id = r.cliente_id
        WHERE {cond}
        ORDER BY r.fecha DESC, r.id DESC""", params)


@router.get("/{id_}")
def ver(id_: int, u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
    hoja = _visible(u, id_)
    hoja["puntos"] = _puntos(hoja)
    return hoja


@router.post("", status_code=201)
def crear(hoja: Hoja, u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
    datos = hoja.model_dump()
    comprobar_referencias(u, datos)
    # Lo que se crea es de quien lo crea; el administrador puede repartirlo.
    datos["usuario_id"] = datos.get("usuario_id") if es_admin(u) else u["id"]
    datos["fecha"] = datos.get("fecha") or date.today().isoformat()
    puntos = _limpios(hoja.puntos)
    recuento = _recuento(puntos)

    columnas = list(CAMPOS) + ["usuario_id"] + list(recuento) + ["puntos", "numero"]
    with db.tx() as con:
        numero = siguiente_numero(con, "recomendaciones", int(datos["fecha"][:4]))
        valores = ([datos.get(k) for k in CAMPOS] + [datos["usuario_id"]] +
                   list(recuento.values()) + [json.dumps(puntos, ensure_ascii=False), numero])
        nuevo = con.execute(
            "INSERT INTO recomendaciones (%s) VALUES (%s)"
            % (", ".join(columnas), ", ".join("?" * len(columnas))), valores).lastrowid
    return ver(nuevo, u)


@router.put("/{id_}")
def actualizar(id_: int, hoja: Hoja, u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
    existente = _visible(u, id_)
    datos = hoja.model_dump()
    comprobar_referencias(u, datos, existente)
    if not es_admin(u):
        datos["usuario_id"] = existente["usuario_id"]
    datos["fecha"] = datos.get("fecha") or existente["fecha"]
    puntos = _limpios(hoja.puntos)
    recuento = _recuento(puntos)

    columnas = list(CAMPOS) + ["usuario_id"] + list(recuento) + ["puntos"]
    with db.tx() as con:
        con.execute("UPDATE recomendaciones SET %s WHERE id = ?"
                    % ", ".join("%s = ?" % k for k in columnas),
                    [datos.get(k) for k in CAMPOS] + [datos["usuario_id"]] +
                    list(recuento.values()) + [json.dumps(puntos, ensure_ascii=False), id_])
    return ver(id_, u)


@router.delete("/{id_}", status_code=204)
def borrar(id_: int, u: dict = Depends(sesion_actual)):
    exigir(u, MODULO)
    _visible(u, id_)
    with db.tx() as con:
        con.execute("DELETE FROM recomendaciones WHERE id = ?", (id_,))
    return Response(status_code=204)


@router.get("/{id_}/pdf")
def descargar(id_: int, u: dict = Depends(sesion_actual)):
    """La hoja para el cliente."""
    exigir(u, MODULO)
    hoja = _visible(u, id_)
    datos = recomendaciones_pdf.generar(hoja, _puntos(hoja))
    return Response(content=datos, media_type="application/pdf",
                    headers={"Content-Disposition":
                             'attachment; filename="%s.pdf"' % (hoja.get("numero") or "REC-%d" % id_)})
