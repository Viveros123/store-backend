"""Lógica de negocio del módulo Catálogo (CU5)."""

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


# --------------------------------------------------------------------------- #
#  Temporadas (CU6)
# --------------------------------------------------------------------------- #
def list_temporadas(session, *, q=None, activo=None, page=1, size=20):
    filtros = []
    if q:
        filtros.append(func.lower(Temporada.nombre).like(f"%{q.strip().lower()}%"))
    if activo is not None:
        filtros.append(Temporada.activo == activo)
    return paginate(
        session,
        Temporada,
        filters=filtros,
        order_by=Temporada.fecha_inicio,
        page=page,
        size=size,
    )


def temporadas_opciones(session: Session):
    return session.exec(
        select(Temporada).where(Temporada.activo == True).order_by(Temporada.nombre)  # noqa: E712
    ).all()


def create_temporada(session: Session, data) -> Temporada:
    if session.exec(
        select(Temporada).where(func.lower(Temporada.nombre) == data.nombre.lower())
    ).first():
        raise HTTPException(409, "Ya existe una temporada con ese nombre")
    obj = Temporada(**data.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_temporada(session: Session, temp_id: int, data) -> Temporada:
    obj = _get_or_404(session, Temporada, temp_id, "Temporada")
    cambios = data.model_dump(exclude_unset=True)
    if "nombre" in cambios and cambios["nombre"]:
        otro = session.exec(
            select(Temporada).where(
                func.lower(Temporada.nombre) == cambios["nombre"].lower()
            )
        ).first()
        if otro and otro.id != temp_id:
            raise HTTPException(409, "Ya existe una temporada con ese nombre")
    for k, v in cambios.items():
        setattr(obj, k, v)
    if (
        obj.fecha_inicio
        and obj.fecha_fin
        and obj.fecha_fin < obj.fecha_inicio
    ):
        raise HTTPException(422, "fecha_fin no puede ser anterior a fecha_inicio")
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


# --------------------------------------------------------------------------- #
#  Colecciones (CU6)
# --------------------------------------------------------------------------- #
def _coleccion_out(session: Session, obj: Coleccion) -> dict:
    temp = session.get(Temporada, obj.temporada_id)
    return {
        "id": obj.id,
        "nombre": obj.nombre,
        "descripcion": obj.descripcion,
        "temporada_id": obj.temporada_id,
        "temporada": temp.nombre if temp else None,
        "activo": obj.activo,
    }


def list_colecciones(session, *, q=None, temporada_id=None, activo=None, page=1, size=20):
    filtros = []
    if q:
        filtros.append(func.lower(Coleccion.nombre).like(f"%{q.strip().lower()}%"))
    if temporada_id is not None:
        filtros.append(Coleccion.temporada_id == temporada_id)
    if activo is not None:
        filtros.append(Coleccion.activo == activo)
    items, total = paginate(
        session, Coleccion, filters=filtros, order_by=Coleccion.nombre, page=page, size=size
    )
    return [_coleccion_out(session, x) for x in items], total


def colecciones_opciones(session: Session, temporada_id: int | None = None):
    base = select(Coleccion).where(Coleccion.activo == True)  # noqa: E712
    if temporada_id is not None:
        base = base.where(Coleccion.temporada_id == temporada_id)
    items = session.exec(base.order_by(Coleccion.nombre)).all()
    return [_coleccion_out(session, x) for x in items]


def _validar_temporada(session: Session, temporada_id: int) -> None:
    if session.get(Temporada, temporada_id) is None:
        raise HTTPException(422, f"La temporada {temporada_id} no existe")


def create_coleccion(session: Session, data) -> dict:
    _validar_temporada(session, data.temporada_id)
    obj = Coleccion(**data.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return _coleccion_out(session, obj)


def update_coleccion(session: Session, col_id: int, data) -> dict:
    obj = _get_or_404(session, Coleccion, col_id, "Colección")
    cambios = data.model_dump(exclude_unset=True)
    if "temporada_id" in cambios and cambios["temporada_id"] is not None:
        _validar_temporada(session, cambios["temporada_id"])
    for k, v in cambios.items():
        setattr(obj, k, v)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return _coleccion_out(session, obj)
