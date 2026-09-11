"""Endpoints del módulo Inventario — CU13: Consultar Inventario Global."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import SessionDep, require_roles
from app.modules.identidad.models import RolNombre, Usuario
from app.modules.inventario import service
from app.modules.inventario.schemas import (
    InventarioAjuste,
    InventarioOut,
    InventarioPage,
)

router = APIRouter(prefix="/inventario", tags=["inventario"])

AdminUser = Annotated[Usuario, Depends(require_roles(RolNombre.ADMINISTRADOR))]


@router.get("", response_model=InventarioPage)
def listar(  # CU13
    session: SessionDep,
    _admin: AdminUser,
    sucursal_id: int | None = None,
    q: str | None = Query(default=None, description="Busca por producto o SKU"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    items, total = service.list_inventario(
        session, sucursal_id=sucursal_id, q=q, page=page, size=size
    )
    return InventarioPage(items=items, total=total, page=page, size=size)


@router.post("/ajustar", response_model=InventarioOut)
def ajustar(data: InventarioAjuste, session: SessionDep, _admin: AdminUser):  # CU13
    return service.ajustar_stock(session, data)
