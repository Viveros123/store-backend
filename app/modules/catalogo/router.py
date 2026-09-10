"""Endpoints del módulo Catálogo — CU5: Categorías, Tallas y Colores."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, SessionDep, require_roles
from app.modules.catalogo import service
from app.modules.catalogo.schemas import (
    CategoriaCreate,
    CategoriaOut,
    CategoriaPage,
    CategoriaUpdate,
    ColorCreate,
    ColorOut,
    ColorPage,
    ColorUpdate,
    TallaCreate,
    TallaOut,
    TallaPage,
    TallaUpdate,
)
from app.modules.identidad.models import RolNombre, Usuario

router = APIRouter(tags=["catálogo"])

AdminUser = Annotated[Usuario, Depends(require_roles(RolNombre.ADMINISTRADOR))]


# --------------------------------------------------------------------------- #
#  Categorías
# --------------------------------------------------------------------------- #
@router.get("/categorias/opciones", response_model=list[CategoriaOut])
def categorias_opciones(session: SessionDep, _: CurrentUser):  # CU5
    return service.categorias_opciones(session)


@router.get("/categorias", response_model=CategoriaPage)
def listar_categorias(  # CU5
    session: SessionDep,
    _admin: AdminUser,
    q: str | None = None,
    activo: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    items, total = service.list_categorias(
        session, q=q, activo=activo, page=page, size=size
    )
    return CategoriaPage(
        items=[CategoriaOut.model_validate(x) for x in items],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "/categorias", response_model=CategoriaOut, status_code=status.HTTP_201_CREATED
)
def crear_categoria(data: CategoriaCreate, session: SessionDep, _admin: AdminUser):  # CU5
    return service.create_categoria(session, data)


@router.patch("/categorias/{cat_id}", response_model=CategoriaOut)
def actualizar_categoria(  # CU5
    cat_id: int, data: CategoriaUpdate, session: SessionDep, _admin: AdminUser
):
    return service.update_categoria(session, cat_id, data)


# --------------------------------------------------------------------------- #
#  Tallas
# --------------------------------------------------------------------------- #
@router.get("/tallas/opciones", response_model=list[TallaOut])
def tallas_opciones(session: SessionDep, _: CurrentUser):  # CU5
    return service.tallas_opciones(session)


@router.get("/tallas", response_model=TallaPage)
def listar_tallas(  # CU5
    session: SessionDep,
    _admin: AdminUser,
    q: str | None = None,
    tipo: str | None = None,
    activo: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    items, total = service.list_tallas(
        session, q=q, tipo=tipo, activo=activo, page=page, size=size
    )
    return TallaPage(
        items=[TallaOut.model_validate(x) for x in items],
        total=total,
        page=page,
        size=size,
    )


@router.post("/tallas", response_model=TallaOut, status_code=status.HTTP_201_CREATED)
def crear_talla(data: TallaCreate, session: SessionDep, _admin: AdminUser):  # CU5
    return service.create_talla(session, data)


@router.patch("/tallas/{talla_id}", response_model=TallaOut)
def actualizar_talla(  # CU5
    talla_id: int, data: TallaUpdate, session: SessionDep, _admin: AdminUser
):
    return service.update_talla(session, talla_id, data)


# --------------------------------------------------------------------------- #
#  Colores
# --------------------------------------------------------------------------- #
@router.get("/colores/opciones", response_model=list[ColorOut])
def colores_opciones(session: SessionDep, _: CurrentUser):  # CU5
    return service.colores_opciones(session)


@router.get("/colores", response_model=ColorPage)
def listar_colores(  # CU5
    session: SessionDep,
    _admin: AdminUser,
    q: str | None = None,
    activo: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    items, total = service.list_colores(
        session, q=q, activo=activo, page=page, size=size
    )
    return ColorPage(
        items=[ColorOut.model_validate(x) for x in items],
        total=total,
        page=page,
        size=size,
    )


@router.post("/colores", response_model=ColorOut, status_code=status.HTTP_201_CREATED)
def crear_color(data: ColorCreate, session: SessionDep, _admin: AdminUser):  # CU5
    return service.create_color(session, data)


@router.patch("/colores/{color_id}", response_model=ColorOut)
def actualizar_color(  # CU5
    color_id: int, data: ColorUpdate, session: SessionDep, _admin: AdminUser
):
    return service.update_color(session, color_id, data)
