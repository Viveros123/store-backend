"""Endpoints del módulo Reportes — CU31 (Generar Reportes de Ventas e Inventario)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import SessionDep, require_roles
from app.modules.identidad.models import RolNombre, Usuario
from app.modules.reportes import service
from app.modules.reportes.schemas import ReporteInventarioOut, ReporteVentasOut
from app.modules.saas.models import CodigoFuncionalidad
from app.modules.saas.service import validar_acceso_plan

router = APIRouter(prefix="/reportes", tags=["reportes"])

AdminUser = Annotated[Usuario, Depends(require_roles(RolNombre.ADMINISTRADOR))]


def _validar_reporte(session: SessionDep, admin: Usuario, sucursal_id: int | None) -> None:
    if admin.empresa_id is None:
        raise HTTPException(403, "El usuario no está asociado a una empresa")
    validar_acceso_plan(
        session,
        admin.empresa_id,
        funcionalidad=CodigoFuncionalidad.REPORTES_CONVENCIONALES,
    )
    if sucursal_id is None:
        validar_acceso_plan(
            session,
            admin.empresa_id,
            funcionalidad=CodigoFuncionalidad.REPORTES_MULTISUCURSAL,
        )


@router.get("/ventas", response_model=ReporteVentasOut)
def reporte_ventas(  # CU31
    session: SessionDep,
    admin: AdminUser,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    sucursal_id: int | None = None,
):
    _validar_reporte(session, admin, sucursal_id)
    return service.reporte_ventas(
        session,
        admin.id,
        fecha_desde,
        fecha_hasta,
        sucursal_id,
        empresa_id=admin.empresa_id,
    )


@router.get("/inventario", response_model=ReporteInventarioOut)
def reporte_inventario(  # CU31
    session: SessionDep,
    admin: AdminUser,
    sucursal_id: int | None = None,
    umbral: int = Query(default=3, ge=0, le=1000),
):
    _validar_reporte(session, admin, sucursal_id)
    return service.reporte_inventario(
        session,
        admin.id,
        sucursal_id,
        umbral,
        empresa_id=admin.empresa_id,
    )
