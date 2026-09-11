"""CU9 — Catálogo público: lo consume cualquier visitante, sin login."""

from fastapi import APIRouter, Query

from app.core.deps import SessionDep
from app.modules.catalogo.schemas import CategoriaOut
from app.modules.catalogo.service import categorias_opciones
from app.modules.productos import service
from app.modules.productos.schemas import (
    CatalogoProductoDetalle,
    CatalogoProductoOut,
    CatalogoProductoPage,
)

router = APIRouter(prefix="/catalogo", tags=["catalogo-publico"])


@router.get("/categorias", response_model=list[CategoriaOut])
def categorias(session: SessionDep):  # CU9
    return categorias_opciones(session)


@router.get("/destacados", response_model=list[CatalogoProductoOut])
def destacados(session: SessionDep, limit: int = Query(default=12, ge=1, le=40)):  # CU9
    return service.list_destacados(session, limit=limit)


@router.get("/productos", response_model=CatalogoProductoPage)
def listar_productos(  # CU9 / CU10 (búsqueda básica)
    session: SessionDep,
    q: str | None = None,
    categoria_id: int | None = None,
    coleccion_id: int | None = None,
    orden: str = Query(default="novedad", pattern="^(novedad|precio_asc|precio_desc|nombre)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=24, ge=1, le=60),
):
    items, total = service.list_catalogo(
        session,
        q=q,
        categoria_id=categoria_id,
        coleccion_id=coleccion_id,
        orden=orden,
        page=page,
        size=size,
    )
    return CatalogoProductoPage(items=items, total=total, page=page, size=size)


@router.get("/productos/{producto_id}", response_model=CatalogoProductoDetalle)
def obtener_producto(producto_id: int, session: SessionDep):  # CU9
    return service.get_catalogo_detalle(session, producto_id)
