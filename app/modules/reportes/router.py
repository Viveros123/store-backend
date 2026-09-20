"""Endpoints del módulo Reportes — CU31 (Generar Reportes de Ventas e Inventario)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import SessionDep, require_roles
from app.modules.identidad.models import RolNombre, Usuario
from app.modules.reportes import service
from app.modules.reportes.schemas import ReporteInventarioOut, ReporteVentasOut

router = APIRouter(prefix="/reportes", tags=["reportes"])

AdminUser = Annotated[Usuario, Depends(require_roles(RolNombre.ADMINISTRADOR))]


@router.get("/ventas", response_model=ReporteVentasOut)
def reporte_ventas(  # CU31
    session: SessionDep,
    admin: AdminUser,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    sucursal_id: int | None = None,
):
    return service.reporte_ventas(session, admin.id, fecha_desde, fecha_hasta, sucursal_id)


@router.get("/inventario", response_model=ReporteInventarioOut)
def reporte_inventario(  # CU31
    session: SessionDep,
    admin: AdminUser,
    sucursal_id: int | None = None,
    umbral: int = Query(default=3, ge=0, le=1000),
):
    return service.reporte_inventario(session, admin.id, sucursal_id, umbral)
