"""Endpoints del módulo Ventas — CU22 (compra web), CU24/25/26 (venta
presencial, pago en caja, comprobante) y CU27/CU28 (pago electrónico)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import SessionDep, require_roles
from app.modules.identidad.models import RolNombre, Usuario
from app.modules.identidad.schemas import ClienteRegistroIn
from app.modules.ventas import service
from app.modules.ventas.schemas import (
    CheckoutCreate,
    ClienteBuscarOut,
    ComprobanteOut,
    EstadoPagoOut,
    PagoCajaCreate,
    PagoOut,
    VentaCajaOut,
    VentaOut,
    VentaPresencialCreate,
)

router = APIRouter(prefix="/ventas", tags=["ventas"])

ClienteUser = Annotated[Usuario, Depends(require_roles(RolNombre.CLIENTE))]
CajeroUser = Annotated[Usuario, Depends(require_roles(RolNombre.CAJERO))]


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


# --------------------------------------------------------------------------- #
#  CU24/25/26 — Venta presencial, pago en caja, comprobante (rol Cajero)
# --------------------------------------------------------------------------- #
@router.get("/clientes/buscar", response_model=list[ClienteBuscarOut])
def buscar_clientes(q: str, session: SessionDep, cajero: CajeroUser):
    if not q or len(q.strip()) < 2:
        return []
    usuarios = service.buscar_clientes(session, q)
    return [
        ClienteBuscarOut(
            id=u.id,
            nombre=u.nombre,
            apellido=u.apellido,
            email=u.email,
            telefono=u.telefono,
        )
        for u in usuarios
    ]


@router.post(
    "/clientes", response_model=ClienteBuscarOut, status_code=status.HTTP_201_CREATED
)
def registrar_cliente_rapido(
    data: ClienteRegistroIn, session: SessionDep, cajero: CajeroUser
):
    usuario = service.registrar_cliente_rapido(session, data)
    return ClienteBuscarOut(
        id=usuario.id,
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        email=usuario.email,
        telefono=usuario.telefono,
    )


@router.get("/caja/historial", response_model=list[VentaCajaOut])
def historial_caja(session: SessionDep, cajero: CajeroUser):
    return service.historial_caja(session, cajero)


@router.post(
    "/presencial", response_model=VentaOut, status_code=status.HTTP_201_CREATED
)
def crear_venta_presencial(  # CU24
    data: VentaPresencialCreate, session: SessionDep, cajero: CajeroUser
):
    return service.crear_venta_presencial(session, cajero, data)


@router.post("/{venta_id}/pagos/caja", response_model=VentaOut)
def procesar_pago_caja(  # CU25
    venta_id: int, data: PagoCajaCreate, session: SessionDep, cajero: CajeroUser
):
    return service.procesar_pago_caja(session, cajero, venta_id, data)


@router.get("/{venta_id}/comprobante", response_model=ComprobanteOut)
def obtener_comprobante(venta_id: int, session: SessionDep, cajero: CajeroUser):  # CU26
    return service.emitir_comprobante(session, cajero, venta_id)
