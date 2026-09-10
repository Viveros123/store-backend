"""Lógica de negocio del módulo Productos — CU4."""

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
from app.modules.productos.models import Producto, ProductoVariante
from app.modules.proveedores.models import Proveedor


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
        "precio_base": p.precio_base,
        "imagen_url": p.imagen_url,
        "activo": p.activo,
        "fecha_creacion": p.fecha_creacion,
        "cantidad_variantes": n_var,
    }


def _variante_out(session: Session, v: ProductoVariante, precio_base) -> dict:
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
        "precio_efectivo": v.precio if v.precio is not None else precio_base,
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
    out["variantes"] = [_variante_out(session, v, p.precio_base) for v in variantes]
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
    return _variante_out(session, v, p.precio_base)


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
    return _variante_out(session, v, p.precio_base)


def delete_variante(session: Session, variante_id: int) -> None:
    v = session.get(ProductoVariante, variante_id)
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante no encontrada")
    session.delete(v)
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
    out["variantes"] = [_variante_out(session, v, p.precio_base) for v in variantes]
    return out


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
        precio_base=data.precio_base,
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
    cambios.pop("activo", None)
    cambios.pop("proveedor_id", None)
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
