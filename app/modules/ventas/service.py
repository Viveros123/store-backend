"""Lógica de negocio del módulo Ventas — CU21 (carrito), CU22 (compra web),
CU27/CU28 (pago electrónico Stripe/QR y su confirmación)."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from app.core.config import settings
from app.modules.catalogo.models import Color, Talla
from app.modules.inventario.models import Inventario, MovimientoInventario, TipoMovimiento
from app.modules.productos.models import Producto, ProductoVariante
from app.modules.sucursales.models import Sucursal
from app.modules.ventas import stripe_client
from app.modules.ventas.models import (
    Carrito,
    CarritoDetalle,
    EstadoCarrito,
    EstadoPago,
    EstadoVenta,
    MetodoPago,
    Pago,
    Venta,
    VentaDetalle,
)
from app.modules.ventas.schemas import CheckoutCreate, ItemCarritoCreate, ItemCarritoUpdate


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


# --------------------------------------------------------------------------- #
#  CU22 — Comprar desde Plataforma Web
# --------------------------------------------------------------------------- #
def _venta_out(session: Session, venta: Venta) -> dict:
    sucursal = session.get(Sucursal, venta.sucursal_id)
    detalles = session.exec(
        select(VentaDetalle).where(VentaDetalle.venta_id == venta.id)
    ).all()
    items = []
    for d in detalles:
        variante = session.get(ProductoVariante, d.variante_id)
        producto = session.get(Producto, variante.producto_id) if variante else None
        talla = session.get(Talla, variante.talla_id) if variante else None
        color = session.get(Color, variante.color_id) if variante else None
        items.append(
            {
                "id": d.id,
                "variante_id": d.variante_id,
                "producto_id": producto.id if producto else None,
                "producto": producto.nombre if producto else None,
                "talla": talla.valor if talla else None,
                "color": color.nombre if color else None,
                "sku": variante.sku if variante else None,
                "cantidad": d.cantidad,
                "precio_unitario": d.precio_unitario,
                "subtotal": d.precio_unitario * d.cantidad,
            }
        )
    return {
        "id": venta.id,
        "sucursal_id": venta.sucursal_id,
        "sucursal": sucursal.nombre if sucursal else None,
        "ciudad": sucursal.ciudad if sucursal else None,
        "estado": venta.estado,
        "total": venta.total,
        "fecha_creacion": venta.fecha_creacion,
        "items": items,
    }


def _venta_del_cliente(session: Session, venta_id: int, cliente_id: int) -> Venta:
    venta = session.get(Venta, venta_id)
    if venta is None or venta.cliente_id != cliente_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venta no encontrada")
    return venta


def crear_checkout(session: Session, cliente_id: int, data: CheckoutCreate) -> dict:
    sucursal = session.get(Sucursal, data.sucursal_id)
    if sucursal is None or not sucursal.activa:
        raise HTTPException(422, "Esa sucursal no es válida")

    carrito = _get_o_crear_carrito(session, cliente_id)
    detalles_carrito = session.exec(
        select(CarritoDetalle).where(CarritoDetalle.carrito_id == carrito.id)
    ).all()
    if not detalles_carrito:
        raise HTTPException(422, "Tu carrito está vacío")

    lineas = []
    for d in detalles_carrito:
        variante = session.get(ProductoVariante, d.variante_id)
        if variante is None:
            raise HTTPException(422, "Una de las prendas de tu carrito ya no existe")
        producto = session.get(Producto, variante.producto_id)
        if producto is None or not producto.activo or producto.precio_base is None:
            raise HTTPException(
                422,
                f"'{producto.nombre if producto else variante.sku}' ya no está disponible",
            )
        inv = session.exec(
            select(Inventario).where(
                Inventario.variante_id == d.variante_id,
                Inventario.sucursal_id == data.sucursal_id,
            )
        ).first()
        if inv is None or inv.cantidad_disponible < d.cantidad:
            raise HTTPException(
                422,
                f"No hay stock suficiente de '{producto.nombre}' en esa sucursal. "
                "Probá con otra sucursal o ajustá la cantidad.",
            )
        precio = variante.precio if variante.precio is not None else producto.precio_base
        lineas.append((variante, d.cantidad, precio, inv))

    total = sum(precio * cantidad for _, cantidad, precio, _ in lineas)

    venta = Venta(cliente_id=cliente_id, sucursal_id=data.sucursal_id, total=total)
    session.add(venta)
    session.flush()  # necesitamos venta.id para el detalle

    for variante, cantidad, precio, inv in lineas:
        session.add(
            VentaDetalle(
                venta_id=venta.id,
                variante_id=variante.id,
                cantidad=cantidad,
                precio_unitario=precio,
                costo_unitario=inv.costo_promedio,
            )
        )
        inv.cantidad_disponible -= cantidad
        session.add(inv)
        session.add(
            MovimientoInventario(
                variante_id=variante.id,
                sucursal_id=data.sucursal_id,
                usuario_id=cliente_id,
                tipo=TipoMovimiento.SALIDA_VENTA,
                cantidad=cantidad,
                nota=f"Venta #{venta.id}",
            )
        )

    for d in detalles_carrito:
        session.delete(d)
    carrito.estado = EstadoCarrito.CONVERTIDO
    carrito.fecha_actualizacion = datetime.now(timezone.utc)
    session.add(carrito)

    session.commit()
    session.refresh(venta)
    return _venta_out(session, venta)


def mis_ventas(session: Session, cliente_id: int) -> list[dict]:
    ventas = session.exec(
        select(Venta)
        .where(Venta.cliente_id == cliente_id)
        .order_by(Venta.fecha_creacion.desc())
    ).all()
    return [_venta_out(session, v) for v in ventas]


def cancelar_venta(session: Session, cliente_id: int, venta_id: int) -> dict:
    venta = _venta_del_cliente(session, venta_id, cliente_id)
    if venta.estado != EstadoVenta.PENDIENTE_PAGO:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Esta venta ya no se puede cancelar"
        )

    detalles = session.exec(
        select(VentaDetalle).where(VentaDetalle.venta_id == venta.id)
    ).all()
    for d in detalles:
        inv = session.exec(
            select(Inventario).where(
                Inventario.variante_id == d.variante_id,
                Inventario.sucursal_id == venta.sucursal_id,
            )
        ).first()
        if inv is not None:
            inv.cantidad_disponible += d.cantidad
            session.add(inv)
        session.add(
            MovimientoInventario(
                variante_id=d.variante_id,
                sucursal_id=venta.sucursal_id,
                usuario_id=cliente_id,
                tipo=TipoMovimiento.ANULACION_VENTA,
                cantidad=d.cantidad,
                nota=f"Cancelación de la venta #{venta.id}",
            )
        )

    venta.estado = EstadoVenta.ANULADA
    session.add(venta)
    session.commit()
    return _venta_out(session, venta)


# --------------------------------------------------------------------------- #
#  CU27 — Procesar Pago Electrónico (QR / Stripe)
# --------------------------------------------------------------------------- #
def _pago_out(
    pago: Pago, *, checkout_url: str | None = None, qr_data_url: str | None = None
) -> dict:
    return {
        "id": pago.id,
        "venta_id": pago.venta_id,
        "metodo": pago.metodo,
        "estado": pago.estado,
        "monto": pago.monto,
        "checkout_url": checkout_url,
        "qr_data_url": qr_data_url,
        "fecha_creacion": pago.fecha_creacion,
    }


def iniciar_pago(session: Session, cliente_id: int, venta_id: int) -> dict:
    venta = _venta_del_cliente(session, venta_id, cliente_id)
    if venta.estado != EstadoVenta.PENDIENTE_PAGO:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Esta venta ya no está pendiente de pago"
        )

    base = settings.frontend_url.rstrip("/")
    stripe_session = stripe_client.crear_checkout_session(
        venta_id=venta.id,
        monto_bs=venta.total,
        descripcion=f"FashionStore - Pedido #{venta.id}",
        success_url=f"{base}/checkout/resultado?venta_id={venta.id}&resultado=exito",
        cancel_url=f"{base}/checkout/resultado?venta_id={venta.id}&resultado=cancelado",
    )

    pago = Pago(
        venta_id=venta.id,
        metodo=MetodoPago.STRIPE,
        monto=venta.total,
        stripe_session_id=stripe_session.id,
    )
    session.add(pago)
    session.commit()
    session.refresh(pago)

    qr_data_url = stripe_client.generar_qr_data_url(stripe_session.url)
    return _pago_out(pago, checkout_url=stripe_session.url, qr_data_url=qr_data_url)


# --------------------------------------------------------------------------- #
#  CU28 — Confirmar / Rechazar Transacción
# --------------------------------------------------------------------------- #
def consultar_estado_pago(session: Session, cliente_id: int, venta_id: int) -> dict:
    """CU28: en vez de depender de un webhook (que necesita una URL pública
    que no existe en localhost), consultamos activamente el estado en Stripe.
    Funciona igual en local y una vez desplegado."""
    venta = _venta_del_cliente(session, venta_id, cliente_id)
    ultimo_pago = session.exec(
        select(Pago).where(Pago.venta_id == venta.id).order_by(Pago.id.desc())
    ).first()

    if (
        ultimo_pago is not None
        and ultimo_pago.stripe_session_id
        and ultimo_pago.estado in (EstadoPago.PENDIENTE, EstadoPago.PROCESANDO)
    ):
        stripe_session = stripe_client.obtener_session(ultimo_pago.stripe_session_id)
        if stripe_session.payment_status == "paid":
            ultimo_pago.estado = EstadoPago.APROBADO
            ultimo_pago.fecha_actualizacion = datetime.now(timezone.utc)
            session.add(ultimo_pago)
            venta.estado = EstadoVenta.PAGADA
            session.add(venta)
            session.commit()
        elif stripe_session.status == "expired":
            ultimo_pago.estado = EstadoPago.RECHAZADO
            ultimo_pago.fecha_actualizacion = datetime.now(timezone.utc)
            session.add(ultimo_pago)
            session.commit()

    return {
        "venta_id": venta.id,
        "venta_estado": venta.estado,
        "pago_id": ultimo_pago.id if ultimo_pago else None,
        "pago_estado": ultimo_pago.estado if ultimo_pago else None,
    }
