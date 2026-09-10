"""Lógica de negocio del módulo Sucursales."""

from fastapi import HTTPException, status
from sqlmodel import Session, func, or_, select

from app.modules.sucursales.models import Sucursal
from app.modules.sucursales.schemas import SucursalCreate, SucursalUpdate


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
