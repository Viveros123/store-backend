"""Endpoints del módulo Ventas — CU22 (compra web) y CU27/CU28 (pago)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import SessionDep, require_roles
from app.modules.identidad.models import RolNombre, Usuario
from app.modules.ventas import service
from app.modules.ventas.schemas import CheckoutCreate, EstadoPagoOut, PagoOut, VentaOut

router = APIRouter(prefix="/ventas", tags=["ventas"])

ClienteUser = Annotated[Usuario, Depends(require_roles(RolNombre.CLIENTE))]


@router.post("/checkout", response_model=VentaOut, status_code=status.HTTP_201_CREATED)
def checkout(  # CU22
    data: CheckoutCreate, session: SessionDep, user: ClienteUser
):
    return service.crear_checkout(session, user.id, data)


@router.get("/mias", response_model=list[VentaOut])
def mis_ventas(session: SessionDep, user: ClienteUser):  # CU22
    return service.mis_ventas(session, user.id)


@router.post("/{venta_id}/cancelar", response_model=VentaOut)
def cancelar(venta_id: int, session: SessionDep, user: ClienteUser):  # CU22
    return service.cancelar_venta(session, user.id, venta_id)


@router.post(
    "/{venta_id}/pagos", response_model=PagoOut, status_code=status.HTTP_201_CREATED
)
def iniciar_pago(venta_id: int, session: SessionDep, user: ClienteUser):  # CU27
    return service.iniciar_pago(session, user.id, venta_id)


@router.get("/{venta_id}/pagos/estado", response_model=EstadoPagoOut)
def estado_pago(venta_id: int, session: SessionDep, user: ClienteUser):  # CU28
    return service.consultar_estado_pago(session, user.id, venta_id)
