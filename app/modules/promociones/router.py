"""Endpoints del módulo Promociones — CU33 (Gestionar Promociones)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import SessionDep, require_roles
from app.modules.identidad.models import RolNombre, Usuario
from app.modules.promociones import service
from app.modules.promociones.schemas import (
    PromocionCreate,
    PromocionOut,
    PromocionUpdate,
    VarianteOpcionOut,
)

router = APIRouter(prefix="/promociones", tags=["promociones"])

AdminUser = Annotated[Usuario, Depends(require_roles(RolNombre.ADMINISTRADOR))]


@router.get("", response_model=list[PromocionOut])
def listar(session: SessionDep, _admin: AdminUser):  # CU33
    return service.listar_promociones(session)


@router.post("", response_model=PromocionOut, status_code=status.HTTP_201_CREATED)
def crear(data: PromocionCreate, session: SessionDep, _admin: AdminUser):  # CU33
    return service.crear_promocion(session, data)


@router.get("/variantes/opciones", response_model=list[VarianteOpcionOut])
def variantes_opciones(session: SessionDep, _admin: AdminUser):  # CU33
    return service.variantes_opciones(session)


@router.get("/{promocion_id}", response_model=PromocionOut)
def obtener(promocion_id: int, session: SessionDep, _admin: AdminUser):  # CU33
    return service.obtener_promocion(session, promocion_id)


@router.patch("/{promocion_id}", response_model=PromocionOut)
def actualizar(  # CU33
    promocion_id: int, data: PromocionUpdate, session: SessionDep, _admin: AdminUser
):
    return service.actualizar_promocion(session, promocion_id, data)
