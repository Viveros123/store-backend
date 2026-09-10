"""Endpoints del módulo Proveedores (CU7 — Gestionar Proveedores)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, SessionDep, require_roles
from app.modules.identidad.models import RolNombre, Usuario
from app.modules.proveedores import service
from app.modules.proveedores.schemas import (
    ProveedorCreate,
    ProveedorOpcion,
    ProveedorOut,
    ProveedorPage,
    ProveedorUpdate,
)

router = APIRouter(prefix="/proveedores", tags=["proveedores"])

AdminUser = Annotated[Usuario, Depends(require_roles(RolNombre.ADMINISTRADOR))]


@router.get("/opciones", response_model=list[ProveedorOpcion])
def opciones(session: SessionDep, _: CurrentUser):  # CU7 (para selects)
    return service.opciones(session)


@router.get("", response_model=ProveedorPage)
def listar(  # CU7
    session: SessionDep,
    _admin: AdminUser,
    q: str | None = Query(default=None, description="Busca por nombre de empresa"),
    activo: bool | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    items, total = service.list_proveedores(
        session, q=q, activo=activo, page=page, size=size
    )
    return ProveedorPage(
        items=[ProveedorOut.model_validate(p) for p in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{proveedor_id}", response_model=ProveedorOut)
def obtener(proveedor_id: int, session: SessionDep, _admin: AdminUser):  # CU7
    return service.get_or_404(session, proveedor_id)


@router.post("", response_model=ProveedorOut, status_code=status.HTTP_201_CREATED)
def crear(data: ProveedorCreate, session: SessionDep, _admin: AdminUser):  # CU7
    return service.create_proveedor(session, data)


@router.patch("/{proveedor_id}", response_model=ProveedorOut)
def actualizar(  # CU7
    proveedor_id: int,
    data: ProveedorUpdate,
    session: SessionDep,
    _admin: AdminUser,
):
    return service.update_proveedor(session, proveedor_id, data)
