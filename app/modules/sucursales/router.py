"""Endpoints del módulo Sucursales (CU11 — Gestionar Sucursales)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, SessionDep, require_roles
from app.modules.identidad.models import RolNombre, Usuario
from app.modules.sucursales import service
from app.modules.sucursales.schemas import (
    HorarioDia,
    HorarioSemana,
    SucursalCreate,
    SucursalOpcion,
    SucursalOut,
    SucursalPage,
    SucursalUpdate,
)

router = APIRouter(prefix="/sucursales", tags=["sucursales"])

AdminUser = Annotated[Usuario, Depends(require_roles(RolNombre.ADMINISTRADOR))]


@router.get("/opciones", response_model=list[SucursalOpcion])
def opciones(session: SessionDep, _: CurrentUser):  # CU11 (para selects)
    return service.opciones(session)


@router.get("", response_model=SucursalPage)
def listar(  # CU11
    session: SessionDep,
    _admin: AdminUser,
    q: str | None = Query(default=None, description="Busca en nombre o ciudad"),
    activa: bool | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    items, total = service.list_sucursales(
        session, q=q, activa=activa, page=page, size=size
    )
    return SucursalPage(
        items=[SucursalOut.model_validate(s) for s in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{sucursal_id}", response_model=SucursalOut)
def obtener(sucursal_id: int, session: SessionDep, _admin: AdminUser):  # CU11
    return service.get_or_404(session, sucursal_id)


@router.post(
    "", response_model=SucursalOut, status_code=status.HTTP_201_CREATED
)
def crear(data: SucursalCreate, session: SessionDep, _admin: AdminUser):  # CU11
    return service.create_sucursal(session, data)


@router.patch("/{sucursal_id}", response_model=SucursalOut)
def actualizar(  # CU11
    sucursal_id: int,
    data: SucursalUpdate,
    session: SessionDep,
    _admin: AdminUser,
):
    return service.update_sucursal(session, sucursal_id, data)


@router.get("/{sucursal_id}/horarios", response_model=list[HorarioDia])
def obtener_horarios(sucursal_id: int, session: SessionDep, _admin: AdminUser):  # CU16
    return service.get_horarios(session, sucursal_id)


@router.put("/{sucursal_id}/horarios", response_model=list[HorarioDia])
def guardar_horarios(  # CU16
    sucursal_id: int, data: HorarioSemana, session: SessionDep, _admin: AdminUser
):
    return service.set_horarios(session, sucursal_id, data)
