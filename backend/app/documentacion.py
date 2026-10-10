"""Documentación: informes y guías de trabajo que lee el equipo.

A diferencia de los estatutos, que escribe el administrador desde el panel,
esto son documentos técnicos que vienen con la aplicación: se escriben en
código, con sus fuentes citadas, y se leen en pantalla o se descargan en PDF.
La razón de que no sean editables es justamente esa: son informes con citas
del reglamento, y una cita que cualquiera pueda cambiar deja de ser una cita.

Se lee sin permisos especiales, como los estatutos: son instrucciones de
trabajo, no datos de nadie.
"""

from fastapi import APIRouter, Depends, HTTPException, Response

from . import documentacion_pdf, guia_pruebas_cuadro
from .auth import sesion_actual

# Antes que el CRUD genérico, que se tragaría /documentacion como si fuese
# una tabla de la base de datos.
router = APIRouter(prefix="/api/admin/documentacion", tags=["documentacion"])

DOCUMENTOS = [
    guia_pruebas_cuadro.DOCUMENTO,
]

PORTADA = ("titulo", "subtitulo", "resumen", "actualizado", "slug")


def _uno(slug: str) -> dict:
    for d in DOCUMENTOS:
        if d["slug"] == slug:
            return d
    raise HTTPException(404, "No encontrado")


@router.get("")
def listar(_: dict = Depends(sesion_actual)):
    """La portada de cada documento, sin su contenido: es lo que pinta la lista."""
    return [{k: d.get(k) for k in PORTADA} for d in DOCUMENTOS]


@router.get("/{slug}")
def ver(slug: str, _: dict = Depends(sesion_actual)):
    return _uno(slug)


@router.get("/{slug}/pdf")
def descargar(slug: str, _: dict = Depends(sesion_actual)):
    doc = _uno(slug)
    datos = documentacion_pdf.generar(doc)
    return Response(content=datos, media_type="application/pdf",
                    headers={"Content-Disposition":
                             'attachment; filename="%s.pdf"' % doc["slug"]})
