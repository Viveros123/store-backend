"""CU9/CU10 — Catálogo público: lo consume cualquier visitante, sin login."""

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from app.core.deps import OptionalAuthenticatedUser, SessionDep
from app.modules.catalogo.schemas import CategoriaOut, ColorOut, TallaOut
from app.modules.catalogo.service import (
    categorias_opciones,
    colores_opciones,
    tallas_opciones,
)
from app.modules.inventario.schemas import DisponibilidadSucursal
from app.modules.inventario.service import disponibilidad_variante
from app.modules.saas.models import Empresa
from app.modules.productos import service
from app.modules.productos.schemas import (
    CatalogoProductoDetalle,
    CatalogoProductoOut,
    CatalogoProductoPage,
)

router = APIRouter(prefix="/catalogo", tags=["catalogo-publico"])


def _empresa_catalogo_id(
    session: SessionDep, usuario: OptionalAuthenticatedUser
) -> int:
    """Tenant de la vitrina: usuario autenticado o tienda heredada pública."""
    if usuario is not None and usuario.empresa_id is not None:
        return usuario.empresa_id
    principal = session.exec(
        select(Empresa).where(
            Empresa.identificador == "fashionstore-principal"
        )
    ).first()
    if principal is None:
        raise HTTPException(503, "La tienda principal no está configurada")
    return principal.id


@router.get("/categorias", response_model=list[CategoriaOut])
def categorias(session: SessionDep, usuario: OptionalAuthenticatedUser):  # CU9
    return categorias_opciones(
        session, empresa_id=_empresa_catalogo_id(session, usuario)
    )


@router.get("/tallas", response_model=list[TallaOut])
def tallas(session: SessionDep, usuario: OptionalAuthenticatedUser):  # CU10
    return tallas_opciones(session, empresa_id=_empresa_catalogo_id(session, usuario))


@router.get("/colores", response_model=list[ColorOut])
def colores(session: SessionDep, usuario: OptionalAuthenticatedUser):  # CU10
    return colores_opciones(
        session, empresa_id=_empresa_catalogo_id(session, usuario)
    )


@router.get("/destacados", response_model=list[CatalogoProductoOut])
def destacados(
    session: SessionDep,
    usuario: OptionalAuthenticatedUser,
    limit: int = Query(default=12, ge=1, le=40),
):  # CU9
    return service.list_destacados(
        session,
        empresa_id=_empresa_catalogo_id(session, usuario),
        limit=limit,
    )


@router.get("/productos", response_model=CatalogoProductoPage)
def listar_productos(  # CU9 / CU10
    session: SessionDep,
    usuario: OptionalAuthenticatedUser,
    q: str | None = None,
    categoria_id: int | None = None,
    coleccion_id: int | None = None,
    talla_id: int | None = None,
    color_id: int | None = None,
    precio_min: float | None = Query(default=None, ge=0),
    precio_max: float | None = Query(default=None, ge=0),
    orden: str = Query(default="novedad", pattern="^(novedad|precio_asc|precio_desc|nombre)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=24, ge=1, le=60),
):
    items, total = service.list_catalogo(
        session,
        empresa_id=_empresa_catalogo_id(session, usuario),
        q=q,
        categoria_id=categoria_id,
        coleccion_id=coleccion_id,
        talla_id=talla_id,
        color_id=color_id,
        precio_min=precio_min,
        precio_max=precio_max,
        orden=orden,
        page=page,
        size=size,
    )
    return CatalogoProductoPage(items=items, total=total, page=page, size=size)


@router.get("/productos/{producto_id}", response_model=CatalogoProductoDetalle)
def obtener_producto(
    producto_id: int,
    session: SessionDep,
    usuario: OptionalAuthenticatedUser,
):  # CU9
    return service.get_catalogo_detalle(
        session,
        producto_id,
        empresa_id=_empresa_catalogo_id(session, usuario),
    )


@router.get(
    "/variantes/{variante_id}/disponibilidad",
    response_model=list[DisponibilidadSucursal],
)
def disponibilidad(
    variante_id: int,
    session: SessionDep,
    usuario: OptionalAuthenticatedUser,
):  # CU12
    return disponibilidad_variante(
        session,
        variante_id,
        empresa_id=_empresa_catalogo_id(session, usuario),
    )
