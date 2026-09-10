"""Lógica de negocio del módulo Catálogo (CU5)."""

from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from app.core.crud import paginate
from app.modules.catalogo.models import Categoria, Color, Talla


def _get_or_404(session: Session, model: type, obj_id: int, nombre: str):
    obj = session.get(model, obj_id)
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{nombre} no encontrado/a"
        )
    return obj


# --------------------------------------------------------------------------- #
#  Categorías
# --------------------------------------------------------------------------- #
def list_categorias(session, *, q=None, activo=None, page=1, size=20):
    filtros = []
    if q:
        filtros.append(func.lower(Categoria.nombre).like(f"%{q.strip().lower()}%"))
    if activo is not None:
        filtros.append(Categoria.activo == activo)
    return paginate(
        session, Categoria, filters=filtros, order_by=Categoria.nombre, page=page, size=size
    )


def categorias_opciones(session: Session):
    return session.exec(
        select(Categoria).where(Categoria.activo == True).order_by(Categoria.nombre)  # noqa: E712
    ).all()


def create_categoria(session: Session, data) -> Categoria:
    if session.exec(
        select(Categoria).where(func.lower(Categoria.nombre) == data.nombre.lower())
    ).first():
        raise HTTPException(409, "Ya existe una categoría con ese nombre")
    obj = Categoria(**data.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_categoria(session: Session, cat_id: int, data) -> Categoria:
    obj = _get_or_404(session, Categoria, cat_id, "Categoría")
    cambios = data.model_dump(exclude_unset=True)
    if "nombre" in cambios and cambios["nombre"]:
        otro = session.exec(
            select(Categoria).where(
                func.lower(Categoria.nombre) == cambios["nombre"].lower()
            )
        ).first()
        if otro and otro.id != cat_id:
            raise HTTPException(409, "Ya existe una categoría con ese nombre")
    for k, v in cambios.items():
        setattr(obj, k, v)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


# --------------------------------------------------------------------------- #
#  Tallas
# --------------------------------------------------------------------------- #
def list_tallas(session, *, q=None, tipo=None, activo=None, page=1, size=20):
    filtros = []
    if q:
        filtros.append(func.lower(Talla.valor).like(f"%{q.strip().lower()}%"))
    if tipo:
        filtros.append(Talla.tipo == tipo)
    if activo is not None:
        filtros.append(Talla.activo == activo)
    return paginate(
        session, Talla, filters=filtros, order_by=(Talla.tipo, Talla.valor), page=page, size=size
    )


def tallas_opciones(session: Session):
    return session.exec(
        select(Talla).where(Talla.activo == True).order_by(Talla.tipo, Talla.valor)  # noqa: E712
    ).all()


def create_talla(session: Session, data) -> Talla:
    if session.exec(
        select(Talla).where(Talla.valor == data.valor, Talla.tipo == data.tipo)
    ).first():
        raise HTTPException(409, "Esa talla ya existe para ese tipo")
    obj = Talla(**data.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_talla(session: Session, talla_id: int, data) -> Talla:
    obj = _get_or_404(session, Talla, talla_id, "Talla")
    cambios = data.model_dump(exclude_unset=True)
    nuevo_valor = cambios.get("valor", obj.valor)
    nuevo_tipo = cambios.get("tipo", obj.tipo)
    otro = session.exec(
        select(Talla).where(Talla.valor == nuevo_valor, Talla.tipo == nuevo_tipo)
    ).first()
    if otro and otro.id != talla_id:
        raise HTTPException(409, "Esa talla ya existe para ese tipo")
    for k, v in cambios.items():
        setattr(obj, k, v)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


# --------------------------------------------------------------------------- #
#  Colores
# --------------------------------------------------------------------------- #
def list_colores(session, *, q=None, activo=None, page=1, size=20):
    filtros = []
    if q:
        filtros.append(func.lower(Color.nombre).like(f"%{q.strip().lower()}%"))
    if activo is not None:
        filtros.append(Color.activo == activo)
    return paginate(
        session, Color, filters=filtros, order_by=Color.nombre, page=page, size=size
    )


def colores_opciones(session: Session):
    return session.exec(
        select(Color).where(Color.activo == True).order_by(Color.nombre)  # noqa: E712
    ).all()


def create_color(session: Session, data) -> Color:
    if session.exec(
        select(Color).where(func.lower(Color.nombre) == data.nombre.lower())
    ).first():
        raise HTTPException(409, "Ya existe un color con ese nombre")
    obj = Color(**data.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_color(session: Session, color_id: int, data) -> Color:
    obj = _get_or_404(session, Color, color_id, "Color")
    cambios = data.model_dump(exclude_unset=True)
    if "nombre" in cambios and cambios["nombre"]:
        otro = session.exec(
            select(Color).where(func.lower(Color.nombre) == cambios["nombre"].lower())
        ).first()
        if otro and otro.id != color_id:
            raise HTTPException(409, "Ya existe un color con ese nombre")
    for k, v in cambios.items():
        setattr(obj, k, v)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj
