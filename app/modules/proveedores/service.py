"""Lógica de negocio del módulo Proveedores."""

from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from app.modules.proveedores.models import Proveedor
from app.modules.proveedores.schemas import ProveedorCreate, ProveedorUpdate


def list_proveedores(
    session: Session,
    *,
    q: str | None = None,
    activo: bool | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Proveedor], int]:
    base = select(Proveedor)
    if q:
        base = base.where(
            func.lower(Proveedor.nombre_empresa).like(f"%{q.strip().lower()}%")
        )
    if activo is not None:
        base = base.where(Proveedor.activo == activo)

    total = session.exec(select(func.count()).select_from(base.subquery())).one()
    items = session.exec(
        base.order_by(Proveedor.nombre_empresa)
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return items, total


def opciones(session: Session) -> list[Proveedor]:
    return session.exec(
        select(Proveedor)
        .where(Proveedor.activo == True)  # noqa: E712
        .order_by(Proveedor.nombre_empresa)
    ).all()


def get_or_404(session: Session, proveedor_id: int) -> Proveedor:
    proveedor = session.get(Proveedor, proveedor_id)
    if proveedor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado"
        )
    return proveedor


def create_proveedor(session: Session, data: ProveedorCreate) -> Proveedor:
    datos = data.model_dump()
    if datos.get("email") is not None:
        datos["email"] = str(datos["email"])
    proveedor = Proveedor(**datos)
    session.add(proveedor)
    session.commit()
    session.refresh(proveedor)
    return proveedor


def update_proveedor(
    session: Session, proveedor_id: int, data: ProveedorUpdate
) -> Proveedor:
    proveedor = get_or_404(session, proveedor_id)
    cambios = data.model_dump(exclude_unset=True)
    if "email" in cambios and cambios["email"] is not None:
        cambios["email"] = str(cambios["email"])
    for campo, valor in cambios.items():
        setattr(proveedor, campo, valor)
    session.add(proveedor)
    session.commit()
    session.refresh(proveedor)
    return proveedor
