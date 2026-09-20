"""Endpoints del módulo Reservas — CU16/17 (cliente) y CU18/19 (sucursal)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import CurrentUser, SessionDep, require_roles
from app.modules.identidad.models import Rol, RolNombre, Usuario
from app.modules.reservas import service
from app.modules.reservas.schemas import (
    FinalizarReservaIn,
    FinalizarReservaOut,
    ReservaCreate,
    ReservaOut,
    ReservaSucursalOut,
    ReservaSucursalPage,
    SlotsDisponibilidad,
)

router = APIRouter(prefix="/reservas", tags=["reservas"])

ClienteUser = Annotated[Usuario, Depends(require_roles(RolNombre.CLIENTE))]
AdminOEncargado = Annotated[
    Usuario, Depends(require_roles(RolNombre.ADMINISTRADOR, RolNombre.ENCARGADO))
]


def _sucursal_permitida(session: SessionDep, user: Usuario) -> int | None:
    """None = puede operar en cualquier sucursal (admin).
    Un id = solo puede operar en esa sucursal (encargado)."""
    rol = session.get(Rol, user.rol_id)
    if rol is not None and rol.nombre == RolNombre.ENCARGADO:
        if user.sucursal_id is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Tu cuenta no está vinculada a ninguna sucursal. Contactá al administrador.",
            )
        return user.sucursal_id
    return None


@router.get("/disponibilidad", response_model=SlotsDisponibilidad)
def disponibilidad(  # CU16
    session: SessionDep,
    _user: CurrentUser,
    sucursal_id: int,
    fecha: date,
    duracion_minutos: int = Query(default=30),
):
    return service.slots_disponibles(session, sucursal_id, fecha, duracion_minutos)


@router.post("", response_model=ReservaOut, status_code=status.HTTP_201_CREATED)
def crear(data: ReservaCreate, session: SessionDep, user: ClienteUser):  # CU16
    return service.crear_reserva(session, user.id, data)


@router.get("/mias", response_model=list[ReservaOut])
def mias(session: SessionDep, user: ClienteUser):  # CU16
    return service.mis_reservas(session, user.id)


@router.post("/{reserva_id}/cancelar", response_model=ReservaOut)
def cancelar(reserva_id: int, session: SessionDep, user: ClienteUser):  # CU17
    return service.cancelar_reserva(session, user.id, reserva_id)


@router.get("/sucursal", response_model=ReservaSucursalPage)
def listar_sucursal(  # CU18/19
    session: SessionDep,
    user: AdminOEncargado,
    sucursal_id: int | None = None,
    estado: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    sucursal_permitida = _sucursal_permitida(session, user)
    items, total = service.listar_por_sucursal(
        session,
        sucursal_id=sucursal_id,
        estado=estado,
        sucursal_permitida=sucursal_permitida,
        page=page,
        size=size,
    )
    return ReservaSucursalPage(items=items, total=total, page=page, size=size)


@router.post("/{reserva_id}/notificar", response_model=ReservaSucursalOut)
def notificar(reserva_id: int, session: SessionDep, user: AdminOEncargado):  # CU18
    sucursal_permitida = _sucursal_permitida(session, user)
    return service.notificar_reserva(session, reserva_id, sucursal_permitida)


@router.post("/{reserva_id}/recepcionar", response_model=ReservaSucursalOut)
def recepcionar(reserva_id: int, session: SessionDep, user: AdminOEncargado):  # CU19
    sucursal_permitida = _sucursal_permitida(session, user)
    return service.recepcionar_reserva(session, reserva_id, sucursal_permitida)


@router.post("/{reserva_id}/finalizar", response_model=FinalizarReservaOut)
def finalizar(  # CU35
    reserva_id: int,
    data: FinalizarReservaIn,
    session: SessionDep,
    user: AdminOEncargado,
):
    sucursal_permitida = _sucursal_permitida(session, user)
    return service.finalizar_reserva(session, user, reserva_id, data, sucursal_permitida)
