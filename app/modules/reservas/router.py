"""Endpoints del módulo Reservas — CU16 (Reservar Prendas)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, SessionDep, require_roles
from app.modules.identidad.models import RolNombre, Usuario
from app.modules.reservas import service
from app.modules.reservas.schemas import ReservaCreate, ReservaOut, SlotsDisponibilidad

router = APIRouter(prefix="/reservas", tags=["reservas"])

ClienteUser = Annotated[Usuario, Depends(require_roles(RolNombre.CLIENTE))]


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
