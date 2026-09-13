"""Lógica de negocio del módulo Inventario — CU12/CU13/CU14."""

from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlmodel import Session, func, or_, select

from app.core.crud import paginate
from app.modules.catalogo.models import Color, Talla
from app.modules.identidad.models import Usuario
from app.modules.inventario.models import Inventario, MovimientoInventario, TipoMovimiento
from app.modules.inventario.schemas import InventarioAjuste, MovimientoInventarioCreate
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
        "costo_promedio": inv.costo_promedio,
        "estado": "DISPONIBLE" if inv.cantidad_disponible > 0 else "AGOTADO",
    }


def list_inventario(
    session: Session,
    *,
    sucursal_id: int | None = None,
    q: str | None = None,
    sucursal_permitida: int | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[dict], int]:
    filtros = []
    if sucursal_permitida is not None:
        filtros.append(Inventario.sucursal_id == sucursal_permitida)
    elif sucursal_id is not None:
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


def ajustar_stock(
    session: Session, data: InventarioAjuste, *, sucursal_permitida: int | None = None
) -> dict:
    if session.get(ProductoVariante, data.variante_id) is None:
        raise HTTPException(422, "La variante no existe")
    if session.get(Sucursal, data.sucursal_id) is None:
        raise HTTPException(422, "La sucursal no existe")
    if sucursal_permitida is not None and data.sucursal_id != sucursal_permitida:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo podés ajustar el stock de tu propia sucursal",
        )

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


# --------------------------------------------------------------------------- #
#  CU14 — Movimientos de inventario
# --------------------------------------------------------------------------- #
def _movimiento_out(session: Session, m: MovimientoInventario) -> dict:
    variante = session.get(ProductoVariante, m.variante_id)
    producto = session.get(Producto, variante.producto_id) if variante else None
    talla = session.get(Talla, variante.talla_id) if variante else None
    color = session.get(Color, variante.color_id) if variante else None
    sucursal = session.get(Sucursal, m.sucursal_id)
    usuario = session.get(Usuario, m.usuario_id)

    return {
        "id": m.id,
        "variante_id": m.variante_id,
        "producto_id": producto.id if producto else None,
        "producto": producto.nombre if producto else None,
        "talla": talla.valor if talla else None,
        "color": color.nombre if color else None,
        "sku": variante.sku if variante else None,
        "sucursal_id": m.sucursal_id,
        "sucursal": sucursal.nombre if sucursal else None,
        "ciudad": sucursal.ciudad if sucursal else None,
        "tipo": m.tipo,
        "cantidad": m.cantidad,
        "costo_unitario": m.costo_unitario,
        "nota": m.nota,
        "usuario_id": m.usuario_id,
        "usuario": f"{usuario.nombre} {usuario.apellido}" if usuario else None,
        "fecha": m.fecha,
    }


def registrar_ingreso(
    session: Session,
    data: MovimientoInventarioCreate,
    usuario_id: int,
    *,
    sucursal_permitida: int | None = None,
) -> dict:
    """CU14: registra la recepción de mercadería del proveedor.

    Suma la cantidad al stock actual (CU13/CU15) y recalcula el costo
    promedio ponderado de esa variante+sucursal.
    """
    if session.get(ProductoVariante, data.variante_id) is None:
        raise HTTPException(422, "La variante no existe")
    if session.get(Sucursal, data.sucursal_id) is None:
        raise HTTPException(422, "La sucursal no existe")
    if sucursal_permitida is not None and data.sucursal_id != sucursal_permitida:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo podés registrar movimientos de tu propia sucursal",
        )

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
            cantidad_disponible=0,
        )

    stock_previo = inv.cantidad_disponible
    costo_previo = inv.costo_promedio if inv.costo_promedio is not None else data.costo_unitario
    nuevo_total = stock_previo + data.cantidad
    promedio = (stock_previo * costo_previo + data.cantidad * data.costo_unitario) / nuevo_total

    inv.costo_promedio = promedio.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    inv.cantidad_disponible = nuevo_total

    session.add(inv)
    session.flush()  # que el UPDATE de inventario quede antes del INSERT del movimiento

    mov = MovimientoInventario(
        variante_id=data.variante_id,
        sucursal_id=data.sucursal_id,
        usuario_id=usuario_id,
        tipo=TipoMovimiento.INGRESO,
        cantidad=data.cantidad,
        costo_unitario=data.costo_unitario,
        nota=data.nota,
    )
    session.add(mov)
    session.commit()
    session.refresh(mov)
    return _movimiento_out(session, mov)


def list_movimientos(
    session: Session,
    *,
    sucursal_id: int | None = None,
    variante_id: int | None = None,
    sucursal_permitida: int | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[dict], int]:
    filtros = []
    if sucursal_permitida is not None:
        filtros.append(MovimientoInventario.sucursal_id == sucursal_permitida)
    elif sucursal_id is not None:
        filtros.append(MovimientoInventario.sucursal_id == sucursal_id)
    if variante_id is not None:
        filtros.append(MovimientoInventario.variante_id == variante_id)

    items, total = paginate(
        session,
        MovimientoInventario,
        filters=filtros,
        order_by=MovimientoInventario.fecha.desc(),
        page=page,
        size=size,
    )
    return [_movimiento_out(session, m) for m in items], total
