"""Lógica de negocio del módulo Productos — CU4."""

from datetime import date

from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from app.core.crud import paginate
from app.modules.catalogo.models import (
    Categoria,
    Coleccion,
    Color,
    Talla,
    Temporada,
)
from app.modules.inventario.models import Inventario, MovimientoInventario
from app.modules.productos.models import Producto, ProductoVariante
from app.modules.promociones import service as promociones_service
from app.modules.proveedores.models import Proveedor
from app.modules.reservas.models import ReservaDetalle
from app.modules.ventas.models import CarritoDetalle, VentaDetalle


# --------------------------------------------------------------------------- #
#  Serialización
# --------------------------------------------------------------------------- #
def _producto_out(session: Session, p: Producto) -> dict:
    cat = session.get(Categoria, p.categoria_id)
    prov = session.get(Proveedor, p.proveedor_id)
    col = session.get(Coleccion, p.coleccion_id) if p.coleccion_id else None
    temp = session.get(Temporada, col.temporada_id) if col else None
    n_var = session.exec(
        select(func.count()).select_from(ProductoVariante).where(
            ProductoVariante.producto_id == p.id
        )
    ).one()
    margen = (
        p.precio_base - p.precio_compra
        if p.precio_base is not None and p.precio_compra is not None
        else None
    )
    return {
        "id": p.id,
        "nombre": p.nombre,
        "descripcion": p.descripcion,
        "categoria_id": p.categoria_id,
        "categoria": cat.nombre if cat else None,
        "coleccion_id": p.coleccion_id,
        "coleccion": col.nombre if col else None,
        "temporada": temp.nombre if temp else None,
        "proveedor_id": p.proveedor_id,
        "proveedor": prov.nombre_empresa if prov else None,
        "precio_compra": p.precio_compra,
        "precio_base": p.precio_base,
        "margen": margen,
        "imagen_url": p.imagen_url,
        "activo": p.activo,
        "fecha_creacion": p.fecha_creacion,
        "cantidad_variantes": n_var,
    }


def _variante_out(session: Session, v: ProductoVariante, producto: Producto) -> dict:
    talla = session.get(Talla, v.talla_id)
    color = session.get(Color, v.color_id)
    return {
        "id": v.id,
        "producto_id": v.producto_id,
        "talla_id": v.talla_id,
        "talla": talla.valor if talla else None,
        "color_id": v.color_id,
        "color": color.nombre if color else None,
        "color_hex": color.codigo_hex if color else None,
        "sku": v.sku,
        "precio": v.precio,
        "precio_efectivo": v.precio if v.precio is not None else producto.precio_base,
        "precio_compra": v.precio_compra,
        "precio_compra_efectivo": (
            v.precio_compra if v.precio_compra is not None else producto.precio_compra
        ),
        "imagen_url": v.imagen_url,
        "imagen_efectivo": v.imagen_url or producto.imagen_url,
    }


# --------------------------------------------------------------------------- #
#  Validaciones de FKs
# --------------------------------------------------------------------------- #
def _validar_refs_producto(
    session: Session,
    *,
    categoria_id: int | None,
    coleccion_id: int | None,
    proveedor_id: int | None,
) -> None:
    if categoria_id is not None and session.get(Categoria, categoria_id) is None:
        raise HTTPException(422, "La categoría no existe")
    if coleccion_id is not None and session.get(Coleccion, coleccion_id) is None:
        raise HTTPException(422, "La colección no existe")
    if proveedor_id is not None and session.get(Proveedor, proveedor_id) is None:
        raise HTTPException(422, "El proveedor no existe")


# --------------------------------------------------------------------------- #
#  Productos
# --------------------------------------------------------------------------- #
def list_productos(
    session: Session,
    *,
    q=None,
    categoria_id=None,
    coleccion_id=None,
    proveedor_id=None,
    activo=None,
    page=1,
    size=20,
) -> tuple[list[dict], int]:
    filtros = []
    if q:
        filtros.append(func.lower(Producto.nombre).like(f"%{q.strip().lower()}%"))
    if categoria_id is not None:
        filtros.append(Producto.categoria_id == categoria_id)
    if coleccion_id is not None:
        filtros.append(Producto.coleccion_id == coleccion_id)
    if proveedor_id is not None:
        filtros.append(Producto.proveedor_id == proveedor_id)
    if activo is not None:
        filtros.append(Producto.activo == activo)

    items, total = paginate(
        session, Producto, filters=filtros, order_by=Producto.nombre, page=page, size=size
    )
    return [_producto_out(session, p) for p in items], total


def productos_opciones(session: Session) -> list[Producto]:
    return session.exec(
        select(Producto).where(Producto.activo == True).order_by(Producto.nombre)  # noqa: E712
    ).all()


def get_producto_detalle(session: Session, producto_id: int) -> dict:
    p = session.get(Producto, producto_id)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    out = _producto_out(session, p)
    variantes = session.exec(
        select(ProductoVariante)
        .where(ProductoVariante.producto_id == producto_id)
        .order_by(ProductoVariante.id)
    ).all()
    out["variantes"] = [_variante_out(session, v, p) for v in variantes]
    return out


def create_producto(session: Session, data) -> dict:
    _validar_refs_producto(
        session,
        categoria_id=data.categoria_id,
        coleccion_id=data.coleccion_id,
        proveedor_id=data.proveedor_id,
    )
    p = Producto(**data.model_dump())
    session.add(p)
    session.commit()
    session.refresh(p)
    return _producto_out(session, p)


def update_producto(session: Session, producto_id: int, data) -> dict:
    p = session.get(Producto, producto_id)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    cambios = data.model_dump(exclude_unset=True)
    _validar_refs_producto(
        session,
        categoria_id=cambios.get("categoria_id"),
        coleccion_id=cambios.get("coleccion_id"),
        proveedor_id=cambios.get("proveedor_id"),
    )
    for k, v in cambios.items():
        setattr(p, k, v)

    if p.activo and p.precio_base is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Asigná un precio de venta antes de activar el producto",
        )

    session.add(p)
    session.commit()
    session.refresh(p)
    return _producto_out(session, p)


# --------------------------------------------------------------------------- #
#  Variantes
# --------------------------------------------------------------------------- #
def _get_producto(session: Session, producto_id: int) -> Producto:
    p = session.get(Producto, producto_id)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return p


def _validar_talla_color(session, talla_id, color_id) -> None:
    if talla_id is not None and session.get(Talla, talla_id) is None:
        raise HTTPException(422, "La talla no existe")
    if color_id is not None and session.get(Color, color_id) is None:
        raise HTTPException(422, "El color no existe")


def add_variante(session: Session, producto_id: int, data) -> dict:
    p = _get_producto(session, producto_id)
    _validar_talla_color(session, data.talla_id, data.color_id)

    if session.exec(select(ProductoVariante).where(ProductoVariante.sku == data.sku)).first():
        raise HTTPException(409, "Ya existe una variante con ese SKU")
    dup = session.exec(
        select(ProductoVariante).where(
            ProductoVariante.producto_id == producto_id,
            ProductoVariante.talla_id == data.talla_id,
            ProductoVariante.color_id == data.color_id,
        )
    ).first()
    if dup:
        raise HTTPException(409, "Ya existe una variante con esa talla y color")

    v = ProductoVariante(producto_id=producto_id, **data.model_dump())
    session.add(v)
    session.commit()
    session.refresh(v)
    return _variante_out(session, v, p)


def update_variante(session: Session, variante_id: int, data) -> dict:
    v = session.get(ProductoVariante, variante_id)
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante no encontrada")
    cambios = data.model_dump(exclude_unset=True)
    _validar_talla_color(session, cambios.get("talla_id"), cambios.get("color_id"))

    if "sku" in cambios and cambios["sku"]:
        otro = session.exec(
            select(ProductoVariante).where(ProductoVariante.sku == cambios["sku"])
        ).first()
        if otro and otro.id != variante_id:
            raise HTTPException(409, "Ya existe una variante con ese SKU")

    nueva_talla = cambios.get("talla_id", v.talla_id)
    nuevo_color = cambios.get("color_id", v.color_id)
    dup = session.exec(
        select(ProductoVariante).where(
            ProductoVariante.producto_id == v.producto_id,
            ProductoVariante.talla_id == nueva_talla,
            ProductoVariante.color_id == nuevo_color,
        )
    ).first()
    if dup and dup.id != variante_id:
        raise HTTPException(409, "Ya existe una variante con esa talla y color")

    for k, val in cambios.items():
        setattr(v, k, val)
    session.add(v)
    session.commit()
    session.refresh(v)
    p = session.get(Producto, v.producto_id)
    return _variante_out(session, v, p)


def _borrar_inventario_de_variantes(session: Session, variante_ids: list[int]) -> None:
    """Limpia el stock y el historial de movimientos (CU12/CU13/CU14) antes
    de borrar variante(s), por la FK.

    No hay `Relationship()` declarada entre estas tablas y ProductoVariante
    (son FKs sueltas), así que SQLAlchemy no sabe ordenar el borrado solo:
    hace falta `flush()` para que esos DELETE se ejecuten antes de intentar
    borrar la variante.
    """
    if not variante_ids:
        return
    tiene_reservas = session.exec(
        select(ReservaDetalle.id).where(
            ReservaDetalle.variante_id.in_(variante_ids)
        )
    ).first()
    if tiene_reservas is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se puede eliminar: hay reservas de clientes asociadas a esta prenda.",
        )
    tiene_ventas = session.exec(
        select(VentaDetalle.id).where(VentaDetalle.variante_id.in_(variante_ids))
    ).first()
    if tiene_ventas is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se puede eliminar: hay ventas registradas de esta prenda.",
        )
    for mov in session.exec(
        select(MovimientoInventario).where(
            MovimientoInventario.variante_id.in_(variante_ids)
        )
    ).all():
        session.delete(mov)
    for inv in session.exec(
        select(Inventario).where(Inventario.variante_id.in_(variante_ids))
    ).all():
        session.delete(inv)
    for item in session.exec(
        select(CarritoDetalle).where(CarritoDetalle.variante_id.in_(variante_ids))
    ).all():
        session.delete(item)
    session.flush()


def _eliminar_variantes_del_producto(session: Session, producto_id: int) -> None:
    variantes = session.exec(
        select(ProductoVariante).where(ProductoVariante.producto_id == producto_id)
    ).all()
    _borrar_inventario_de_variantes(session, [v.id for v in variantes])
    for v in variantes:
        session.delete(v)
    session.flush()  # idem: que las variantes se borren antes que el producto


def delete_variante(session: Session, variante_id: int) -> None:
    v = session.get(ProductoVariante, variante_id)
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante no encontrada")
    _borrar_inventario_de_variantes(session, [v.id])
    session.delete(v)
    session.commit()


def delete_producto(session: Session, producto_id: int) -> None:
    """Admin: borra el producto, sus variantes y el stock asociado."""
    p = session.get(Producto, producto_id)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    _eliminar_variantes_del_producto(session, producto_id)
    session.delete(p)
    session.commit()


# --------------------------------------------------------------------------- #
#  CU8 — Portal del proveedor (productos de su propia empresa)
# --------------------------------------------------------------------------- #
def _producto_del_proveedor(
    session: Session, producto_id: int, proveedor_id: int
) -> Producto:
    p = session.get(Producto, producto_id)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    if p.proveedor_id != proveedor_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Este producto es de otro proveedor"
        )
    return p


def list_productos_proveedor(
    session: Session, proveedor_id: int, *, q=None, page=1, size=20
) -> tuple[list[dict], int]:
    filtros = [Producto.proveedor_id == proveedor_id]
    if q:
        filtros.append(func.lower(Producto.nombre).like(f"%{q.strip().lower()}%"))
    items, total = paginate(
        session, Producto, filters=filtros, order_by=Producto.nombre, page=page, size=size
    )
    return [_producto_out(session, p) for p in items], total


def get_detalle_proveedor(
    session: Session, producto_id: int, proveedor_id: int
) -> dict:
    p = _producto_del_proveedor(session, producto_id, proveedor_id)
    out = _producto_out(session, p)
    variantes = session.exec(
        select(ProductoVariante)
        .where(ProductoVariante.producto_id == producto_id)
        .order_by(ProductoVariante.id)
    ).all()
    out["variantes"] = [_variante_out(session, v, p) for v in variantes]
    return out


def delete_producto_proveedor(
    session: Session, producto_id: int, proveedor_id: int
) -> None:
    """El proveedor solo puede borrar productos que todavía no fueron activados."""
    p = _producto_del_proveedor(session, producto_id, proveedor_id)
    if p.activo:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este producto ya fue activado; pedile al administrador que lo dé de baja.",
        )
    _eliminar_variantes_del_producto(session, producto_id)
    session.delete(p)
    session.commit()


def create_producto_proveedor(
    session: Session, proveedor_id: int, data
) -> dict:
    # El proveedor no elige proveedor_id ni puede activar el producto.
    if session.get(Categoria, data.categoria_id) is None:
        raise HTTPException(422, "La categoría no existe")
    if data.coleccion_id is not None and session.get(Coleccion, data.coleccion_id) is None:
        raise HTTPException(422, "La colección no existe")

    p = Producto(
        nombre=data.nombre,
        descripcion=data.descripcion,
        categoria_id=data.categoria_id,
        coleccion_id=data.coleccion_id,
        proveedor_id=proveedor_id,
        precio_compra=data.precio_compra,
        precio_base=None,  # el precio de venta lo fija el administrador
        imagen_url=data.imagen_url,
        activo=False,  # pendiente de activación por el administrador
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return _producto_out(session, p)


def update_producto_proveedor(
    session: Session, producto_id: int, proveedor_id: int, data
) -> dict:
    p = _producto_del_proveedor(session, producto_id, proveedor_id)
    cambios = data.model_dump(exclude_unset=True)
    # El proveedor no fija ni el precio de venta ni la activación.
    cambios.pop("activo", None)
    cambios.pop("proveedor_id", None)
    cambios.pop("precio_base", None)
    _validar_refs_producto(
        session,
        categoria_id=cambios.get("categoria_id"),
        coleccion_id=cambios.get("coleccion_id"),
        proveedor_id=None,
    )
    for k, v in cambios.items():
        setattr(p, k, v)
    session.add(p)
    session.commit()
    session.refresh(p)
    return _producto_out(session, p)


def _variante_del_proveedor(
    session: Session, variante_id: int, proveedor_id: int
) -> ProductoVariante:
    v = session.get(ProductoVariante, variante_id)
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante no encontrada")
    _producto_del_proveedor(session, v.producto_id, proveedor_id)
    return v


def add_variante_proveedor(
    session: Session, producto_id: int, proveedor_id: int, data
) -> dict:
    _producto_del_proveedor(session, producto_id, proveedor_id)
    return add_variante(session, producto_id, data)


def update_variante_proveedor(
    session: Session, variante_id: int, proveedor_id: int, data
) -> dict:
    _variante_del_proveedor(session, variante_id, proveedor_id)
    return update_variante(session, variante_id, data)


def delete_variante_proveedor(
    session: Session, variante_id: int, proveedor_id: int
) -> None:
    _variante_del_proveedor(session, variante_id, proveedor_id)
    delete_variante(session, variante_id)


# --------------------------------------------------------------------------- #
#  CU9 — Catálogo público (cliente): solo productos activos, sin costos
# --------------------------------------------------------------------------- #
def _catalogo_producto_out(session: Session, p: Producto) -> dict:
    cat = session.get(Categoria, p.categoria_id)
    col = session.get(Coleccion, p.coleccion_id) if p.coleccion_id else None
    temp = session.get(Temporada, col.temporada_id) if col else None

    variantes = session.exec(
        select(ProductoVariante).where(ProductoVariante.producto_id == p.id)
    ).all()
    colores_vistos: dict[int, dict] = {}
    for v in variantes:
        if v.color_id in colores_vistos:
            continue
        color = session.get(Color, v.color_id)
        if color:
            colores_vistos[v.color_id] = {
                "id": color.id,
                "nombre": color.nombre,
                "codigo_hex": color.codigo_hex,
            }

    precio_final, promo = promociones_service.mejor_precio(
        p.precio_base, promociones_service.promos_de_producto(session, p.id)
    )
    # Si la promoción cubre solo algunas variantes no hay un único precio para
    # la tarjeta: se muestra la etiqueta "Oferta" y el precio exacto en el detalle.
    en_variantes = (
        [] if promo else promociones_service.promos_de_variantes_del_producto(session, p.id)
    )
    etiqueta_oferta = promo.nombre if promo else (en_variantes[0].nombre if en_variantes else None)

    return {
        "id": p.id,
        "nombre": p.nombre,
        "descripcion": p.descripcion,
        "categoria": cat.nombre if cat else None,
        "coleccion": col.nombre if col else None,
        "temporada": temp.nombre if temp else None,
        "precio_base": p.precio_base,
        "precio_promocional": precio_final if promo else None,
        "promocion": etiqueta_oferta,
        "imagen_url": p.imagen_url,
        "colores": list(colores_vistos.values()),
        "cantidad_variantes": len(variantes),
    }


def _temporadas_vigentes_ids(session: Session) -> list[int]:
    hoy = date.today()
    temporadas = session.exec(select(Temporada).where(Temporada.activo == True)).all()  # noqa: E712
    return [
        t.id
        for t in temporadas
        if (t.fecha_inicio is None or t.fecha_inicio <= hoy)
        and (t.fecha_fin is None or hoy <= t.fecha_fin)
    ]


def list_catalogo(
    session: Session,
    *,
    q: str | None = None,
    categoria_id: int | None = None,
    coleccion_id: int | None = None,
    talla_id: int | None = None,
    color_id: int | None = None,
    precio_min: float | None = None,
    precio_max: float | None = None,
    orden: str = "novedad",
    page: int = 1,
    size: int = 20,
) -> tuple[list[dict], int]:
    filtros = [Producto.activo == True, Producto.precio_base.is_not(None)]  # noqa: E712
    if q:
        filtros.append(func.lower(Producto.nombre).like(f"%{q.strip().lower()}%"))
    if categoria_id is not None:
        filtros.append(Producto.categoria_id == categoria_id)
    if coleccion_id is not None:
        filtros.append(Producto.coleccion_id == coleccion_id)
    if precio_min is not None:
        filtros.append(Producto.precio_base >= precio_min)
    if precio_max is not None:
        filtros.append(Producto.precio_base <= precio_max)
    if talla_id is not None or color_id is not None:
        subq = select(ProductoVariante.producto_id)
        if talla_id is not None:
            subq = subq.where(ProductoVariante.talla_id == talla_id)
        if color_id is not None:
            subq = subq.where(ProductoVariante.color_id == color_id)
        filtros.append(Producto.id.in_(subq))

    orden_map = {
        "novedad": Producto.fecha_creacion.desc(),
        "precio_asc": Producto.precio_base.asc(),
        "precio_desc": Producto.precio_base.desc(),
        "nombre": Producto.nombre.asc(),
    }
    order_by = orden_map.get(orden, Producto.fecha_creacion.desc())

    items, total = paginate(
        session, Producto, filters=filtros, order_by=order_by, page=page, size=size
    )
    return [_catalogo_producto_out(session, p) for p in items], total


def list_destacados(session: Session, limit: int = 12) -> list[dict]:
    """Vitrina de la portada: productos de temporadas vigentes."""
    ids_vigentes = _temporadas_vigentes_ids(session)
    if not ids_vigentes:
        return []
    colecciones = session.exec(
        select(Coleccion).where(
            Coleccion.temporada_id.in_(ids_vigentes), Coleccion.activo == True  # noqa: E712
        )
    ).all()
    col_ids = [c.id for c in colecciones]
    if not col_ids:
        return []
    productos = session.exec(
        select(Producto)
        .where(
            Producto.activo == True,  # noqa: E712
            Producto.precio_base.is_not(None),
            Producto.coleccion_id.in_(col_ids),
        )
        .order_by(Producto.fecha_creacion.desc())
        .limit(limit)
    ).all()
    return [_catalogo_producto_out(session, p) for p in productos]


def get_catalogo_detalle(session: Session, producto_id: int) -> dict:
    p = session.get(Producto, producto_id)
    if p is None or not p.activo or p.precio_base is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")

    out = _catalogo_producto_out(session, p)
    variantes = session.exec(
        select(ProductoVariante)
        .where(ProductoVariante.producto_id == producto_id)
        .order_by(ProductoVariante.id)
    ).all()
    promos_por_variante = promociones_service.promos_vigentes_por_variante(
        session, [(v.id, producto_id) for v in variantes]
    )
    resultado_variantes = []
    for v in variantes:
        talla = session.get(Talla, v.talla_id)
        color = session.get(Color, v.color_id)
        precio_efectivo = v.precio if v.precio is not None else p.precio_base
        precio_final, promo = promociones_service.mejor_precio(
            precio_efectivo, promos_por_variante.get(v.id, [])
        )
        resultado_variantes.append(
            {
                "id": v.id,
                "talla_id": v.talla_id,
                "talla": talla.valor if talla else None,
                "color_id": v.color_id,
                "color": color.nombre if color else None,
                "color_hex": color.codigo_hex if color else None,
                "precio_efectivo": precio_efectivo,
                "precio_promocional": precio_final if promo else None,
                "promocion": promo.nombre if promo else None,
                "imagen_efectivo": v.imagen_url or p.imagen_url,
            }
        )
    out["variantes"] = resultado_variantes
    return out
