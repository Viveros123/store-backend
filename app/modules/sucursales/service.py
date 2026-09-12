"""Lógica de negocio del módulo Sucursales."""

from fastapi import HTTPException, status
from sqlmodel import Session, func, or_, select

from app.modules.sucursales.models import Sucursal, SucursalHorario
from app.modules.sucursales.schemas import (
    HorarioDia,
    HorarioSemana,
    SucursalCreate,
    SucursalUpdate,
)


def list_sucursales(
    session: Session,
    *,
    q: str | None = None,
    activa: bool | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Sucursal], int]:
    base = select(Sucursal)
    if q:
        patron = f"%{q.strip().lower()}%"
        base = base.where(
            or_(
                func.lower(Sucursal.nombre).like(patron),
                func.lower(Sucursal.ciudad).like(patron),
            )
        )
    if activa is not None:
        base = base.where(Sucursal.activa == activa)

    total = session.exec(select(func.count()).select_from(base.subquery())).one()
    items = session.exec(
        base.order_by(Sucursal.ciudad, Sucursal.nombre)
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return items, total


def opciones(session: Session) -> list[Sucursal]:
    return session.exec(
        select(Sucursal)
        .where(Sucursal.activa == True)  # noqa: E712
        .order_by(Sucursal.ciudad, Sucursal.nombre)
    ).all()


def get_or_404(session: Session, sucursal_id: int) -> Sucursal:
    sucursal = session.get(Sucursal, sucursal_id)
    if sucursal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada"
        )
    return sucursal


def create_sucursal(session: Session, data: SucursalCreate) -> Sucursal:
    sucursal = Sucursal(**data.model_dump())
    session.add(sucursal)
    session.commit()
    session.refresh(sucursal)
    return sucursal


def update_sucursal(
    session: Session, sucursal_id: int, data: SucursalUpdate
) -> Sucursal:
    sucursal = get_or_404(session, sucursal_id)
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(sucursal, campo, valor)
    session.add(sucursal)
    session.commit()
    session.refresh(sucursal)
    return sucursal


# --------------------------------------------------------------------------- #
#  CU16 — Horarios de atención (para reservas)
# --------------------------------------------------------------------------- #
def get_horarios(session: Session, sucursal_id: int) -> list[SucursalHorario]:
    get_or_404(session, sucursal_id)
    filas = session.exec(
        select(SucursalHorario)
        .where(SucursalHorario.sucursal_id == sucursal_id)
        .order_by(SucursalHorario.dia_semana)
    ).all()
    por_dia = {f.dia_semana: f for f in filas}
    # Si un día no tiene fila cargada, se muestra como "cerrado" por defecto.
    return [
        por_dia.get(
            d,
            SucursalHorario(sucursal_id=sucursal_id, dia_semana=d, cerrado=True),
        )
        for d in range(7)
    ]


def set_horarios(
    session: Session, sucursal_id: int, data: HorarioSemana
) -> list[SucursalHorario]:
    get_or_404(session, sucursal_id)
    dias_vistos = {d.dia_semana for d in data.dias}
    if dias_vistos != set(range(7)):
        raise HTTPException(422, "Hay que mandar los 7 días de la semana, sin repetir")

    existentes = session.exec(
        select(SucursalHorario).where(SucursalHorario.sucursal_id == sucursal_id)
    ).all()
    for f in existentes:
        session.delete(f)
    session.flush()

    nuevas = [
        SucursalHorario(
            sucursal_id=sucursal_id,
            dia_semana=d.dia_semana,
            cerrado=d.cerrado,
            hora_apertura=None if d.cerrado else d.hora_apertura,
            hora_cierre=None if d.cerrado else d.hora_cierre,
        )
        for d in data.dias
    ]
    session.add_all(nuevas)
    session.commit()
    return get_horarios(session, sucursal_id)


def horario_del_dia(session: Session, sucursal_id: int, dia_semana: int) -> HorarioDia:
    fila = session.exec(
        select(SucursalHorario).where(
            SucursalHorario.sucursal_id == sucursal_id,
            SucursalHorario.dia_semana == dia_semana,
        )
    ).first()
    if fila is None:
        return HorarioDia(dia_semana=dia_semana, cerrado=True)
    return HorarioDia.model_validate(fila, from_attributes=True)
