"""Lógica de negocio del módulo Promociones — CU33."""

from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.modules.catalogo.models import Color, Talla
from app.modules.productos.models import Producto, ProductoVariante
from app.modules.promociones.models import (
    Promocion,
    PromocionProducto,
    PromocionVariante,
    TipoDescuento,
)
from app.modules.promociones.schemas import PromocionCreate, PromocionUpdate

# Bolivia no tiene horario de verano: UTC-4 fijo. Evita que una promoción
# "hasta hoy" termine 4 horas antes por comparar contra la fecha en UTC.
_BOLIVIA = timezone(timedelta(hours=-4))
_PRECIO_MINIMO = Decimal("1.00")
_PORCENTAJE_MAXIMO = Decimal("90")


def hoy_bolivia() -> date:
    return datetime.now(_BOLIVIA).date()


def _vigente(p: Promocion, hoy: date) -> bool:
    return p.activo and p.fecha_inicio <= hoy <= p.fecha_fin


# --------------------------------------------------------------------------- #
#  Aplicación del descuento (catálogo, carrito, ventas)
# --------------------------------------------------------------------------- #
def _precio_con(promo: Promocion, precio: Decimal) -> Decimal:
    if promo.tipo_descuento == TipoDescuento.PORCENTAJE:
        descuento = precio * promo.valor / Decimal(100)
    else:
        descuento = promo.valor
    final = (precio - descuento).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return max(final, min(_PRECIO_MINIMO, precio))


def mejor_precio(
    precio: Decimal, promos: list[Promocion]
) -> tuple[Decimal, Promocion | None]:
    """Si varias promociones aplican al mismo producto, gana la que deja el
    precio más bajo para el cliente (no se acumulan)."""
    mejor: tuple[Decimal, Promocion | None] = (precio, None)
    for promo in promos:
        candidato = _precio_con(promo, precio)
        if candidato < mejor[0]:
            mejor = (candidato, promo)
    return mejor


def promos_vigentes_por_producto(
    session: Session, producto_ids: Iterable[int]
) -> dict[int, list[Promocion]]:
    ids = list(producto_ids)
    if not ids:
        return {}
    hoy = hoy_bolivia()
    filas = session.exec(
        select(PromocionProducto.producto_id, Promocion)
        .join(Promocion, Promocion.id == PromocionProducto.promocion_id)
        .where(
            PromocionProducto.producto_id.in_(ids),
            Promocion.activo == True,  # noqa: E712
            Promocion.fecha_inicio <= hoy,
            Promocion.fecha_fin >= hoy,
        )
    ).all()
    por_producto: dict[int, list[Promocion]] = {}
    for producto_id, promo in filas:
        por_producto.setdefault(producto_id, []).append(promo)
    return por_producto


def promos_de_producto(session: Session, producto_id: int) -> list[Promocion]:
    """Promociones vigentes que cubren el producto completo."""
    return promos_vigentes_por_producto(session, [producto_id]).get(producto_id, [])


def _promos_directas_por_variante(
    session: Session, variante_ids: list[int]
) -> dict[int, list[Promocion]]:
    if not variante_ids:
        return {}
    hoy = hoy_bolivia()
    filas = session.exec(
        select(PromocionVariante.variante_id, Promocion)
        .join(Promocion, Promocion.id == PromocionVariante.promocion_id)
        .where(
            PromocionVariante.variante_id.in_(variante_ids),
            Promocion.activo == True,  # noqa: E712
            Promocion.fecha_inicio <= hoy,
            Promocion.fecha_fin >= hoy,
        )
    ).all()
    por_variante: dict[int, list[Promocion]] = {}
    for variante_id, promo in filas:
        por_variante.setdefault(variante_id, []).append(promo)
    return por_variante


def promos_vigentes_por_variante(
    session: Session, variantes: Iterable[tuple[int, int]]
) -> dict[int, list[Promocion]]:
    """variante_id -> promociones vigentes que le aplican, ya sea porque cubren
    su producto completo o porque la eligen a ella puntualmente.
    `variantes` son pares (variante_id, producto_id)."""
    pares = list(variantes)
    if not pares:
        return {}
    del_producto = promos_vigentes_por_producto(session, {pid for _, pid in pares})
    directas = _promos_directas_por_variante(session, [vid for vid, _ in pares])
    resultado: dict[int, list[Promocion]] = {}
    for variante_id, producto_id in pares:
        unicas = {
            promo.id: promo
            for promo in [*del_producto.get(producto_id, []), *directas.get(variante_id, [])]
        }
        resultado[variante_id] = list(unicas.values())
    return resultado


def promos_de_variante(
    session: Session, variante_id: int, producto_id: int
) -> list[Promocion]:
    return promos_vigentes_por_variante(session, [(variante_id, producto_id)]).get(
        variante_id, []
    )


def promos_de_variantes_del_producto(
    session: Session, producto_id: int
) -> list[Promocion]:
    """Promociones vigentes que cubren solo algunas variantes del producto
    (sirven para mostrar la etiqueta "Oferta" en la tarjeta del catálogo)."""
    ids = session.exec(
        select(ProductoVariante.id).where(ProductoVariante.producto_id == producto_id)
    ).all()
    directas = _promos_directas_por_variante(session, list(ids))
    unicas = {p.id: p for lista in directas.values() for p in lista}
    return list(unicas.values())


# --------------------------------------------------------------------------- #
#  CU33 — Gestionar Promociones (Administrador)
# --------------------------------------------------------------------------- #
def _validar(tipo: str, valor: Decimal, fecha_inicio: date, fecha_fin: date) -> None:
    if fecha_fin < fecha_inicio:
        raise HTTPException(422, "La fecha de fin no puede ser anterior a la de inicio")
    if tipo == TipoDescuento.PORCENTAJE and valor > _PORCENTAJE_MAXIMO:
        raise HTTPException(422, "El descuento porcentual no puede superar el 90%")


def _productos_existentes(session: Session, producto_ids: list[int]) -> list[Producto]:
    ids = list(dict.fromkeys(producto_ids))
    productos = session.exec(select(Producto).where(Producto.id.in_(ids))).all()
    if len(productos) != len(ids):
        raise HTTPException(422, "Alguno de los productos elegidos no existe")
    return productos


def _variantes_existentes(
    session: Session, variante_ids: list[int]
) -> list[ProductoVariante]:
    ids = list(dict.fromkeys(variante_ids))
    if not ids:
        return []
    variantes = session.exec(
        select(ProductoVariante).where(ProductoVariante.id.in_(ids))
    ).all()
    if len(variantes) != len(ids):
        raise HTTPException(422, "Alguna de las variantes elegidas no existe")
    return variantes


def _promocion_out(session: Session, promo: Promocion) -> dict:
    variantes = session.exec(
        select(ProductoVariante.id, Producto.nombre, Talla.valor, Color.nombre)
        .select_from(PromocionVariante)
        .join(ProductoVariante, ProductoVariante.id == PromocionVariante.variante_id)
        .join(Producto, Producto.id == ProductoVariante.producto_id)
        .join(Talla, Talla.id == ProductoVariante.talla_id)
        .join(Color, Color.id == ProductoVariante.color_id)
        .where(PromocionVariante.promocion_id == promo.id)
        .order_by(Producto.nombre, Talla.valor, Color.nombre)
    ).all()
    productos = session.exec(
        select(Producto)
        .join(PromocionProducto, PromocionProducto.producto_id == Producto.id)
        .where(PromocionProducto.promocion_id == promo.id)
        .order_by(Producto.nombre)
    ).all()
    return {
        "id": promo.id,
        "nombre": promo.nombre,
        "descripcion": promo.descripcion,
        "tipo_descuento": promo.tipo_descuento,
        "valor": promo.valor,
        "fecha_inicio": promo.fecha_inicio,
        "fecha_fin": promo.fecha_fin,
        "activo": promo.activo,
        "vigente": _vigente(promo, hoy_bolivia()),
        "productos": [{"id": p.id, "nombre": p.nombre} for p in productos],
        "variantes": [
            {"id": vid, "producto": prod, "talla": talla, "color": color}
            for vid, prod, talla, color in variantes
        ],
    }


def _get_promocion(session: Session, promocion_id: int) -> Promocion:
    promo = session.get(Promocion, promocion_id)
    if promo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Promoción no encontrada")
    return promo


def _reemplazar_productos(
    session: Session, promocion_id: int, producto_ids: list[int]
) -> None:
    for fila in session.exec(
        select(PromocionProducto).where(PromocionProducto.promocion_id == promocion_id)
    ).all():
        session.delete(fila)
    session.flush()
    for producto in _productos_existentes(session, producto_ids):
        session.add(PromocionProducto(promocion_id=promocion_id, producto_id=producto.id))


def _reemplazar_variantes(
    session: Session, promocion_id: int, variante_ids: list[int]
) -> None:
    for fila in session.exec(
        select(PromocionVariante).where(PromocionVariante.promocion_id == promocion_id)
    ).all():
        session.delete(fila)
    session.flush()
    for variante in _variantes_existentes(session, variante_ids):
        session.add(PromocionVariante(promocion_id=promocion_id, variante_id=variante.id))


def _exigir_algun_objetivo(session: Session, promocion_id: int) -> None:
    hay_productos = session.exec(
        select(PromocionProducto.producto_id).where(
            PromocionProducto.promocion_id == promocion_id
        )
    ).first()
    hay_variantes = session.exec(
        select(PromocionVariante.variante_id).where(
            PromocionVariante.promocion_id == promocion_id
        )
    ).first()
    if hay_productos is None and hay_variantes is None:
        raise HTTPException(422, "Elegí al menos un producto o una variante")


def variantes_opciones(session: Session) -> list[dict]:
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
        .where(Producto.activo == True)  # noqa: E712
        .order_by(Producto.nombre, Talla.valor, Color.nombre)
    ).all()
    return [
        {"id": vid, "producto_id": pid, "producto": prod, "talla": talla, "color": color}
        for vid, pid, prod, talla, color in filas
    ]


def listar_promociones(session: Session) -> list[dict]:
    promos = session.exec(select(Promocion).order_by(Promocion.id.desc())).all()
    return [_promocion_out(session, p) for p in promos]


def obtener_promocion(session: Session, promocion_id: int) -> dict:
    return _promocion_out(session, _get_promocion(session, promocion_id))


def crear_promocion(session: Session, data: PromocionCreate) -> dict:
    _validar(data.tipo_descuento, data.valor, data.fecha_inicio, data.fecha_fin)
    if not data.producto_ids and not data.variante_ids:
        raise HTTPException(422, "Elegí al menos un producto o una variante")
    _productos_existentes(session, data.producto_ids)
    _variantes_existentes(session, data.variante_ids)
    promo = Promocion(**data.model_dump(exclude={"producto_ids", "variante_ids"}))
    session.add(promo)
    session.flush()
    _reemplazar_productos(session, promo.id, data.producto_ids)
    _reemplazar_variantes(session, promo.id, data.variante_ids)
    session.commit()
    session.refresh(promo)
    return _promocion_out(session, promo)


def actualizar_promocion(
    session: Session, promocion_id: int, data: PromocionUpdate
) -> dict:
    promo = _get_promocion(session, promocion_id)
    cambios = data.model_dump(exclude_unset=True)
    producto_ids = cambios.pop("producto_ids", None)
    variante_ids = cambios.pop("variante_ids", None)
    for campo, valor in cambios.items():
        setattr(promo, campo, valor)
    _validar(promo.tipo_descuento, promo.valor, promo.fecha_inicio, promo.fecha_fin)
    session.add(promo)
    if producto_ids is not None:
        _reemplazar_productos(session, promo.id, producto_ids)
    if variante_ids is not None:
        _reemplazar_variantes(session, promo.id, variante_ids)
    session.flush()
    _exigir_algun_objetivo(session, promo.id)
    session.commit()
    session.refresh(promo)
    return _promocion_out(session, promo)
