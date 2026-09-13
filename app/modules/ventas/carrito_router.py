"""Endpoints del módulo Ventas — CU21 (Gestionar Carrito de Compras)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import SessionDep, require_roles
from app.modules.identidad.models import RolNombre, Usuario
from app.modules.ventas import service
from app.modules.ventas.schemas import CarritoOut, ItemCarritoCreate, ItemCarritoUpdate

router = APIRouter(prefix="/carrito", tags=["carrito"])

ClienteUser = Annotated[Usuario, Depends(require_roles(RolNombre.CLIENTE))]


@router.get("", response_model=CarritoOut)
def mi_carrito(session: SessionDep, user: ClienteUser):  # CU21
    return service.mi_carrito(session, user.id)


@router.post("/items", response_model=CarritoOut, status_code=status.HTTP_201_CREATED)
def agregar_item(  # CU21
    data: ItemCarritoCreate, session: SessionDep, user: ClienteUser
):
    return service.agregar_item(session, user.id, data)


@router.patch("/items/{item_id}", response_model=CarritoOut)
def actualizar_item(  # CU21
    item_id: int, data: ItemCarritoUpdate, session: SessionDep, user: ClienteUser
):
    return service.actualizar_item(session, user.id, item_id, data)


@router.delete("/items/{item_id}", response_model=CarritoOut)
def quitar_item(item_id: int, session: SessionDep, user: ClienteUser):  # CU21
    return service.quitar_item(session, user.id, item_id)


@router.delete("", response_model=CarritoOut)
def vaciar(session: SessionDep, user: ClienteUser):  # CU21
    return service.vaciar_carrito(session, user.id)
