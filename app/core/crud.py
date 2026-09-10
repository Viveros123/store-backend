"""Utilidades genéricas de paginación para listados."""

from typing import Any

from sqlmodel import Session, func, select


def paginate(
    session: Session,
    model: type,
    *,
    filters: list[Any] | None = None,
    order_by: Any | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Any], int]:
    base = select(model)
    for f in filters or []:
        base = base.where(f)

    total = session.exec(select(func.count()).select_from(base.subquery())).one()

    if order_by is not None:
        cols = order_by if isinstance(order_by, (list, tuple)) else [order_by]
        base = base.order_by(*cols)
    items = session.exec(base.offset((page - 1) * size).limit(size)).all()
    return items, total
