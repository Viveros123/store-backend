"""Lógica de negocio del módulo Ventas — CU21 (Gestionar Carrito de Compras)."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from app.modules.catalogo.models import Color, Talla
from app.modules.inventario.models import Inventario
from app.modules.productos.models import Producto, ProductoVariante
from app.modules.sucursales.models import Sucursal
from app.modules.ventas.models import Carrito, CarritoDetalle, EstadoCarrito
from app.modules.ventas.schemas import ItemCarritoCreate, ItemCarritoUpdate


def _get_o_crear_carrito(session: Session, cliente_id: int) -> Carrito:
    carrito = session.exec(
        select(Carrito).where(
            Carrito.cliente_id == cliente_id, Carrito.estado == EstadoCarrito.ACTIVO
        )
    ).first()
    if carrito is None:
        carrito = Carrito(cliente_id=cliente_id)
        session.add(carrito)
        session.commit()
        session.refresh(carrito)
    return carrito


def _hay_stock(session: Session, variante_id: int) -> bool:
    total = session.exec(
        select(func.coalesce(func.sum(Inventario.cantidad_disponible), 0))
        .join(Sucursal, Inventario.sucursal_id == Sucursal.id)  # type: ignore[arg-type]
        .where(Inventario.variante_id == variante_id, Sucursal.activa == True)  # noqa: E712
    ).one()
    return total > 0


def _item_out(session: Session, d: CarritoDetalle) -> dict:
    variante = session.get(ProductoVariante, d.variante_id)
    producto = session.get(Producto, variante.producto_id) if variante else None
    talla = session.get(Talla, variante.talla_id) if variante else None
    color = session.get(Color, variante.color_id) if variante else None

    precio = None
    if variante is not None:
        precio = (
            variante.precio
            if variante.precio is not None
            else (producto.precio_base if producto else None)
        )
    subtotal = precio * d.cantidad if precio is not None else None

    return {
        "id": d.id,
        "variante_id": d.variante_id,
        "producto_id": producto.id if producto else None,
        "producto": producto.nombre if producto else None,
        "talla": talla.valor if talla else None,
        "color": color.nombre if color else None,
        "sku": variante.sku if variante else None,
        "imagen_efectivo": (variante.imagen_url if variante else None)
        or (producto.imagen_url if producto else None),
        "precio_unitario": precio,
        "cantidad": d.cantidad,
        "subtotal": subtotal,
        "disponible": _hay_stock(session, d.variante_id) if variante else False,
    }


def _carrito_out(session: Session, carrito: Carrito) -> dict:
    detalles = session.exec(
        select(CarritoDetalle)
        .where(CarritoDetalle.carrito_id == carrito.id)
        .order_by(CarritoDetalle.id)
    ).all()
    items = [_item_out(session, d) for d in detalles]
    total = sum((i["subtotal"] or Decimal(0)) for i in items) if items else Decimal(0)
    return {
        "id": carrito.id,
        "estado": carrito.estado,
        "items": items,
        "cantidad_items": sum(i["cantidad"] for i in items),
        "total": total,
    }


def mi_carrito(session: Session, cliente_id: int) -> dict:
    carrito = _get_o_crear_carrito(session, cliente_id)
    return _carrito_out(session, carrito)


def agregar_item(session: Session, cliente_id: int, data: ItemCarritoCreate) -> dict:
    variante = session.get(ProductoVariante, data.variante_id)
    if variante is None:
        raise HTTPException(422, "Esa prenda ya no existe")
    producto = session.get(Producto, variante.producto_id)
    if producto is None or not producto.activo or producto.precio_base is None:
        raise HTTPException(422, "Esa prenda ya no está disponible")
    if not _hay_stock(session, data.variante_id):
        raise HTTPException(422, "No hay stock de esa prenda por ahora")

    carrito = _get_o_crear_carrito(session, cliente_id)
    existente = session.exec(
        select(CarritoDetalle).where(
            CarritoDetalle.carrito_id == carrito.id,
            CarritoDetalle.variante_id == data.variante_id,
        )
    ).first()
    if existente:
        existente.cantidad = min(existente.cantidad + data.cantidad, 20)
        session.add(existente)
    else:
        session.add(
            CarritoDetalle(
                carrito_id=carrito.id,
                variante_id=data.variante_id,
                cantidad=data.cantidad,
            )
        )
    carrito.fecha_actualizacion = datetime.now(timezone.utc)
    session.add(carrito)
    session.commit()
    return mi_carrito(session, cliente_id)


def _item_del_cliente(
    session: Session, item_id: int, cliente_id: int
) -> CarritoDetalle:
    item = session.get(CarritoDetalle, item_id)
    if item is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Ese ítem no está en tu carrito"
        )
    carrito = session.get(Carrito, item.carrito_id)
    if carrito is None or carrito.cliente_id != cliente_id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Ese ítem no está en tu carrito"
        )
    return item


def actualizar_item(
    session: Session, cliente_id: int, item_id: int, data: ItemCarritoUpdate
) -> dict:
    item = _item_del_cliente(session, item_id, cliente_id)
    item.cantidad = data.cantidad
    session.add(item)
    session.commit()
    return mi_carrito(session, cliente_id)


def quitar_item(session: Session, cliente_id: int, item_id: int) -> dict:
    item = _item_del_cliente(session, item_id, cliente_id)
    session.delete(item)
    session.commit()
    return mi_carrito(session, cliente_id)


def vaciar_carrito(session: Session, cliente_id: int) -> dict:
    carrito = _get_o_crear_carrito(session, cliente_id)
    for d in session.exec(
        select(CarritoDetalle).where(CarritoDetalle.carrito_id == carrito.id)
    ).all():
        session.delete(d)
    session.commit()
    return mi_carrito(session, cliente_id)
