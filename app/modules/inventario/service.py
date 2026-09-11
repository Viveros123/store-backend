"""Lógica de negocio del módulo Inventario — CU12/CU13."""

from fastapi import HTTPException, status
from sqlmodel import Session, func, or_, select

from app.core.crud import paginate
from app.modules.catalogo.models import Color, Talla
from app.modules.inventario.models import Inventario
from app.modules.inventario.schemas import InventarioAjuste
from app.modules.productos.models import Producto, ProductoVariante
from app.modules.sucursales.models import Sucursal


def _inventario_out(session: Session, inv: Inventario) -> dict:
    variante = session.get(ProductoVariante, inv.variante_id)
    producto = session.get(Producto, variante.producto_id) if variante else None
    talla = session.get(Talla, variante.talla_id) if variante else None
    color = session.get(Color, variante.color_id) if variante else None
    sucursal = session.get(Sucursal, inv.sucursal_id)

    return {
        "id": inv.id,
        "variante_id": inv.variante_id,
        "producto_id": producto.id if producto else None,
        "producto": producto.nombre if producto else None,
        "talla": talla.valor if talla else None,
        "color": color.nombre if color else None,
        "color_hex": color.codigo_hex if color else None,
        "sku": variante.sku if variante else None,
        "sucursal_id": inv.sucursal_id,
        "sucursal": sucursal.nombre if sucursal else None,
        "ciudad": sucursal.ciudad if sucursal else None,
        "cantidad_disponible": inv.cantidad_disponible,
        "cantidad_reservada": inv.cantidad_reservada,
        "estado": "DISPONIBLE" if inv.cantidad_disponible > 0 else "AGOTADO",
    }


def list_inventario(
    session: Session,
    *,
    sucursal_id: int | None = None,
    q: str | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[dict], int]:
    filtros = []
    if sucursal_id is not None:
        filtros.append(Inventario.sucursal_id == sucursal_id)
    if q:
        patron = f"%{q.strip().lower()}%"
        subq = (
            select(ProductoVariante.id)
            .join(Producto, ProductoVariante.producto_id == Producto.id)
            .where(
                or_(
                    func.lower(Producto.nombre).like(patron),
                    func.lower(ProductoVariante.sku).like(patron),
                )
            )
        )
        filtros.append(Inventario.variante_id.in_(subq))

    items, total = paginate(
        session,
        Inventario,
        filters=filtros,
        order_by=Inventario.id.desc(),
        page=page,
        size=size,
    )
    return [_inventario_out(session, i) for i in items], total


def ajustar_stock(session: Session, data: InventarioAjuste) -> dict:
    if session.get(ProductoVariante, data.variante_id) is None:
        raise HTTPException(422, "La variante no existe")
    if session.get(Sucursal, data.sucursal_id) is None:
        raise HTTPException(422, "La sucursal no existe")

    inv = session.exec(
        select(Inventario).where(
            Inventario.variante_id == data.variante_id,
            Inventario.sucursal_id == data.sucursal_id,
        )
    ).first()
    if inv is None:
        inv = Inventario(
            variante_id=data.variante_id,
            sucursal_id=data.sucursal_id,
            cantidad_disponible=data.cantidad_disponible,
        )
    else:
        inv.cantidad_disponible = data.cantidad_disponible

    session.add(inv)
    session.commit()
    session.refresh(inv)
    return _inventario_out(session, inv)


def disponibilidad_variante(session: Session, variante_id: int) -> list[dict]:
    """CU12 — sucursales con stock de una variante concreta."""
    filas = session.exec(
        select(Inventario, Sucursal)
        .join(Sucursal, Inventario.sucursal_id == Sucursal.id)  # type: ignore[arg-type]
        .where(
            Inventario.variante_id == variante_id,
            Inventario.cantidad_disponible > 0,
            Sucursal.activa == True,  # noqa: E712
        )
    ).all()
    return [
        {
            "sucursal_id": suc.id,
            "sucursal": suc.nombre,
            "ciudad": suc.ciudad,
            "cantidad_disponible": inv.cantidad_disponible,
        }
        for inv, suc in filas
    ]
