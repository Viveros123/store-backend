"""Endpoints del módulo Ventas al por mayor — CU53 (Administrador)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import SessionDep, require_roles
from app.core.tenant import empresa_actual_id
from app.modules.identidad.models import RolNombre, Usuario
from app.modules.mayoreo import service
from app.modules.mayoreo.schemas import (
    DescuentoMayoristaCreate,
    DescuentoMayoristaOut,
    DescuentoMayoristaUpdate,
    VarianteOpcionOut,
)

router = APIRouter(prefix="/mayoreo", tags=["mayoreo"])

AdminUser = Annotated[Usuario, Depends(require_roles(RolNombre.ADMINISTRADOR))]


@router.get("", response_model=list[DescuentoMayoristaOut])
def listar(session: SessionDep, admin: AdminUser):  # CU53
    return service.listar(session, empresa_id=empresa_actual_id(admin))


@router.post("", response_model=DescuentoMayoristaOut, status_code=status.HTTP_201_CREATED)
def crear(data: DescuentoMayoristaCreate, session: SessionDep, admin: AdminUser):  # CU53
    return service.crear(
        session, data, empresa_id=empresa_actual_id(admin), usuario_id=admin.id
    )


@router.get("/variantes/opciones", response_model=list[VarianteOpcionOut])
def variantes_opciones(session: SessionDep, admin: AdminUser):  # CU53
    return service.variantes_opciones(session, empresa_id=empresa_actual_id(admin))


@router.patch("/{regla_id}", response_model=DescuentoMayoristaOut)
def actualizar(  # CU53
    regla_id: int,
    data: DescuentoMayoristaUpdate,
    session: SessionDep,
    admin: AdminUser,
):
    return service.actualizar(
        session, regla_id, data, empresa_id=empresa_actual_id(admin)
    )
