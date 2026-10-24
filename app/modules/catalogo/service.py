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


def _get_or_404(
    session: Session, model: type, obj_id: int, nombre: str, empresa_id: int
):
    obj = session.get(model, obj_id)
    if obj is None or obj.empresa_id != empresa_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{nombre} no encontrado/a"
        )
    return obj


# --------------------------------------------------------------------------- #
#  Categorías
# --------------------------------------------------------------------------- #
def list_categorias(session, *, empresa_id, q=None, activo=None, page=1, size=20):
    filtros = [Categoria.empresa_id == empresa_id]
    if q:
        filtros.append(func.lower(Categoria.nombre).like(f"%{q.strip().lower()}%"))
    if activo is not None:
        filtros.append(Categoria.activo == activo)
    return paginate(
        session, Categoria, filters=filtros, order_by=Categoria.nombre, page=page, size=size
    )


def categorias_opciones(session: Session, *, empresa_id: int):
    return session.exec(
        select(Categoria).where(
            Categoria.empresa_id == empresa_id, Categoria.activo == True  # noqa: E712
        ).order_by(Categoria.nombre)
    ).all()


def create_categoria(session: Session, data, *, empresa_id: int) -> Categoria:
    if session.exec(
        select(Categoria).where(
            Categoria.empresa_id == empresa_id,
            func.lower(Categoria.nombre) == data.nombre.lower(),
        )
    ).first():
        raise HTTPException(409, "Ya existe una categoría con ese nombre")
    obj = Categoria(empresa_id=empresa_id, **data.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_categoria(
    session: Session, cat_id: int, data, *, empresa_id: int
) -> Categoria:
    obj = _get_or_404(session, Categoria, cat_id, "Categoría", empresa_id)
    cambios = data.model_dump(exclude_unset=True)
    if "nombre" in cambios and cambios["nombre"]:
        otro = session.exec(
            select(Categoria).where(
                Categoria.empresa_id == empresa_id,
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
def list_tallas(
    session, *, empresa_id, q=None, tipo=None, activo=None, page=1, size=20
):
    filtros = [Talla.empresa_id == empresa_id]
    if q:
        filtros.append(func.lower(Talla.valor).like(f"%{q.strip().lower()}%"))
    if tipo:
        filtros.append(Talla.tipo == tipo)
    if activo is not None:
        filtros.append(Talla.activo == activo)
    return paginate(
        session, Talla, filters=filtros, order_by=(Talla.tipo, Talla.valor), page=page, size=size
    )


def tallas_opciones(session: Session, *, empresa_id: int):
    return session.exec(
        select(Talla).where(
            Talla.empresa_id == empresa_id, Talla.activo == True  # noqa: E712
        ).order_by(Talla.tipo, Talla.valor)
    ).all()


def create_talla(session: Session, data, *, empresa_id: int) -> Talla:
    if session.exec(
        select(Talla).where(
            Talla.empresa_id == empresa_id,
            Talla.valor == data.valor,
            Talla.tipo == data.tipo,
        )
    ).first():
        raise HTTPException(409, "Esa talla ya existe para ese tipo")
    obj = Talla(empresa_id=empresa_id, **data.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_talla(
    session: Session, talla_id: int, data, *, empresa_id: int
) -> Talla:
    obj = _get_or_404(session, Talla, talla_id, "Talla", empresa_id)
    cambios = data.model_dump(exclude_unset=True)
    nuevo_valor = cambios.get("valor", obj.valor)
    nuevo_tipo = cambios.get("tipo", obj.tipo)
    otro = session.exec(
        select(Talla).where(
            Talla.empresa_id == empresa_id,
            Talla.valor == nuevo_valor,
            Talla.tipo == nuevo_tipo,
        )
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
def list_colores(session, *, empresa_id, q=None, activo=None, page=1, size=20):
    filtros = [Color.empresa_id == empresa_id]
    if q:
        filtros.append(func.lower(Color.nombre).like(f"%{q.strip().lower()}%"))
    if activo is not None:
        filtros.append(Color.activo == activo)
    return paginate(
        session, Color, filters=filtros, order_by=Color.nombre, page=page, size=size
    )


def colores_opciones(session: Session, *, empresa_id: int):
    return session.exec(
        select(Color).where(
            Color.empresa_id == empresa_id, Color.activo == True  # noqa: E712
        ).order_by(Color.nombre)
    ).all()


def create_color(session: Session, data, *, empresa_id: int) -> Color:
    if session.exec(
        select(Color).where(
            Color.empresa_id == empresa_id,
            func.lower(Color.nombre) == data.nombre.lower(),
        )
    ).first():
        raise HTTPException(409, "Ya existe un color con ese nombre")
    obj = Color(empresa_id=empresa_id, **data.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_color(
    session: Session, color_id: int, data, *, empresa_id: int
) -> Color:
    obj = _get_or_404(session, Color, color_id, "Color", empresa_id)
    cambios = data.model_dump(exclude_unset=True)
    if "nombre" in cambios and cambios["nombre"]:
        otro = session.exec(
            select(Color).where(
                Color.empresa_id == empresa_id,
                func.lower(Color.nombre) == cambios["nombre"].lower(),
            )
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
def list_temporadas(session, *, empresa_id, q=None, activo=None, page=1, size=20):
    filtros = [Temporada.empresa_id == empresa_id]
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


def temporadas_opciones(session: Session, *, empresa_id: int):
    return session.exec(
        select(Temporada).where(
            Temporada.empresa_id == empresa_id, Temporada.activo == True  # noqa: E712
        ).order_by(Temporada.nombre)
    ).all()


def create_temporada(session: Session, data, *, empresa_id: int) -> Temporada:
    if session.exec(
        select(Temporada).where(
            Temporada.empresa_id == empresa_id,
            func.lower(Temporada.nombre) == data.nombre.lower(),
        )
    ).first():
        raise HTTPException(409, "Ya existe una temporada con ese nombre")
    obj = Temporada(empresa_id=empresa_id, **data.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_temporada(
    session: Session, temp_id: int, data, *, empresa_id: int
) -> Temporada:
    obj = _get_or_404(session, Temporada, temp_id, "Temporada", empresa_id)
    cambios = data.model_dump(exclude_unset=True)
    if "nombre" in cambios and cambios["nombre"]:
        otro = session.exec(
            select(Temporada).where(
                Temporada.empresa_id == empresa_id,
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


def list_colecciones(
    session, *, empresa_id, q=None, temporada_id=None, activo=None, page=1, size=20
):
    filtros = [Coleccion.empresa_id == empresa_id]
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


def colecciones_opciones(
    session: Session, temporada_id: int | None = None, *, empresa_id: int
):
    base = select(Coleccion).where(
        Coleccion.empresa_id == empresa_id, Coleccion.activo == True  # noqa: E712
    )
    if temporada_id is not None:
        base = base.where(Coleccion.temporada_id == temporada_id)
    items = session.exec(base.order_by(Coleccion.nombre)).all()
    return [_coleccion_out(session, x) for x in items]


def _validar_temporada(
    session: Session, temporada_id: int, empresa_id: int
) -> None:
    temporada = session.get(Temporada, temporada_id)
    if temporada is None or temporada.empresa_id != empresa_id:
        raise HTTPException(422, f"La temporada {temporada_id} no existe")


def create_coleccion(session: Session, data, *, empresa_id: int) -> dict:
    _validar_temporada(session, data.temporada_id, empresa_id)
    obj = Coleccion(empresa_id=empresa_id, **data.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return _coleccion_out(session, obj)


def update_coleccion(
    session: Session, col_id: int, data, *, empresa_id: int
) -> dict:
    obj = _get_or_404(session, Coleccion, col_id, "Colección", empresa_id)
    cambios = data.model_dump(exclude_unset=True)
    if "temporada_id" in cambios and cambios["temporada_id"] is not None:
        _validar_temporada(session, cambios["temporada_id"], empresa_id)
    for k, v in cambios.items():
        setattr(obj, k, v)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return _coleccion_out(session, obj)
