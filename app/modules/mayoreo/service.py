"""Lógica de negocio del módulo Ventas al por mayor — CU53.

Multitenencia: cada regla pertenece a una empresa (`empresa_id`) y aplica en
TODAS las sucursales de esa empresa — no se configura por sucursal.
"""

from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.modules.catalogo.models import Color, Talla
from app.modules.productos.models import Producto, ProductoVariante

from .models import DescuentoMayorista
from .schemas import DescuentoMayoristaCreate, DescuentoMayoristaUpdate

_CENTAVOS = Decimal("0.01")


# --------------------------------------------------------------------------- #
#  Aplicación del descuento (ficha de producto, carrito y ventas)
# --------------------------------------------------------------------------- #
def _precio_con(regla: DescuentoMayorista, precio: Decimal) -> Decimal:
    descuento = precio * regla.porcentaje_descuento / Decimal(100)
    return (precio - descuento).quantize(_CENTAVOS, rounding=ROUND_HALF_UP)


def regla_vigente_de_variante(
    session: Session, variante_id: int
) -> DescuentoMayorista | None:
    return session.exec(
        select(DescuentoMayorista).where(
            DescuentoMayorista.variante_id == variante_id,
            DescuentoMayorista.activo == True,  # noqa: E712
        )
    ).first()


def reglas_vigentes_de_variantes(
    session: Session, variante_ids: list[int]
) -> dict[int, DescuentoMayorista]:
    if not variante_ids:
        return {}
    filas = session.exec(
        select(DescuentoMayorista).where(
            DescuentoMayorista.variante_id.in_(variante_ids),
            DescuentoMayorista.activo == True,  # noqa: E712
        )
    ).all()
    return {r.variante_id: r for r in filas}


def precio_con_mayoreo(
    regla: DescuentoMayorista | None, precio: Decimal, cantidad: int
) -> Decimal | None:
    """Precio unitario si `cantidad` alcanza el mínimo de la regla, o None si
    no aplica (todavía no llega al mínimo, o no hay regla)."""
    if regla is None or cantidad < regla.cantidad_minima:
        return None
    return _precio_con(regla, precio)


# --------------------------------------------------------------------------- #
#  CU53 — Gestionar ventas al por mayor (Administrador)
# --------------------------------------------------------------------------- #
def variantes_opciones(session: Session, *, empresa_id: int) -> list[dict]:
    """Variantes de productos activos, para elegirlas en el formulario."""
    filas = session.exec(
        select(
            ProductoVariante.id,
            ProductoVariante.producto_id,
            Producto.nombre,
            Talla.valor,
            Color.nombre,
        )
        .join(Producto, Producto.id == ProductoVariante.producto_id)
        .join(Talla, Talla.id == ProductoVariante.talla_id)
        .join(Color, Color.id == ProductoVariante.color_id)
        .where(
            Producto.empresa_id == empresa_id,
            ProductoVariante.empresa_id == empresa_id,
            Producto.activo == True,  # noqa: E712
        )
        .order_by(Producto.nombre, Talla.valor, Color.nombre)
    ).all()
    return [
        {"id": vid, "producto_id": pid, "producto": prod, "talla": talla, "color": color}
        for vid, pid, prod, talla, color in filas
    ]


def _descuento_out(session: Session, regla: DescuentoMayorista) -> dict:
    variante = session.get(ProductoVariante, regla.variante_id)
    producto = session.get(Producto, variante.producto_id) if variante else None
    talla = session.get(Talla, variante.talla_id) if variante else None
    color = session.get(Color, variante.color_id) if variante else None
    return {
        "id": regla.id,
        "variante_id": regla.variante_id,
        "producto_id": producto.id if producto else None,
        "producto": producto.nombre if producto else "",
        "talla": talla.valor if talla else None,
        "color": color.nombre if color else None,
        "cantidad_minima": regla.cantidad_minima,
        "porcentaje_descuento": regla.porcentaje_descuento,
        "activo": regla.activo,
    }


def _get_regla(session: Session, regla_id: int, empresa_id: int) -> DescuentoMayorista:
    regla = session.get(DescuentoMayorista, regla_id)
    if regla is None or regla.empresa_id != empresa_id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Regla de mayoreo no encontrada"
        )
    return regla


def listar(session: Session, *, empresa_id: int) -> list[dict]:
    reglas = session.exec(
        select(DescuentoMayorista)
        .where(DescuentoMayorista.empresa_id == empresa_id)
        .order_by(DescuentoMayorista.id.desc())
    ).all()
    return [_descuento_out(session, r) for r in reglas]


def crear(
    session: Session,
    data: DescuentoMayoristaCreate,
    *,
    empresa_id: int,
    usuario_id: int,
) -> dict:
    variante = session.get(ProductoVariante, data.variante_id)
    if variante is None or variante.empresa_id != empresa_id:
        raise HTTPException(422, "Esa variante no existe")

    existente = session.exec(
        select(DescuentoMayorista).where(
            DescuentoMayorista.variante_id == data.variante_id
        )
    ).first()
    if existente is not None:
        raise HTTPException(
            409,
            "Esa variante ya tiene una regla de mayoreo — "
            "edítala en vez de crear otra.",
        )

    regla = DescuentoMayorista(
        empresa_id=empresa_id,
        variante_id=data.variante_id,
        cantidad_minima=data.cantidad_minima,
        porcentaje_descuento=data.porcentaje_descuento,
        creado_por_id=usuario_id,
    )
    session.add(regla)
    session.commit()
    session.refresh(regla)
    return _descuento_out(session, regla)


def actualizar(
    session: Session,
    regla_id: int,
    data: DescuentoMayoristaUpdate,
    *,
    empresa_id: int,
) -> dict:
    regla = _get_regla(session, regla_id, empresa_id)
    cambios = data.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(regla, campo, valor)
    session.add(regla)
    session.commit()
    session.refresh(regla)
    return _descuento_out(session, regla)
