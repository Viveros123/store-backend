"""Endpoints del módulo Productos — CU4."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import SessionDep, require_roles
from app.modules.identidad.models import RolNombre, Usuario
from app.modules.productos import service
from app.modules.productos.schemas import (
    ProductoCreate,
    ProductoDetalle,
    ProductoOpcion,
    ProductoOut,
    ProductoPage,
    ProductoUpdate,
    VarianteCreate,
    VarianteOut,
    VarianteUpdate,
)

router = APIRouter(tags=["productos"])

AdminUser = Annotated[Usuario, Depends(require_roles(RolNombre.ADMINISTRADOR))]
# El encargado de sucursal necesita leer productos/variantes para las
# pantallas de inventario y movimientos de stock (CU13/CU14) de su sucursal.
AdminOEncargado = Annotated[
    Usuario, Depends(require_roles(RolNombre.ADMINISTRADOR, RolNombre.ENCARGADO))
]


# --------------------------------------------------------------------------- #
#  Productos
# --------------------------------------------------------------------------- #
@router.get("/productos/opciones", response_model=list[ProductoOpcion])
def productos_opciones(session: SessionDep, _user: AdminOEncargado):  # CU13 (selects)
    return service.productos_opciones(session)


@router.get("/productos", response_model=ProductoPage)
def listar_productos(  # CU4
    session: SessionDep,
    _admin: AdminUser,
    q: str | None = None,
    categoria_id: int | None = None,
    coleccion_id: int | None = None,
    proveedor_id: int | None = None,
    activo: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    items, total = service.list_productos(
        session,
        q=q,
        categoria_id=categoria_id,
        coleccion_id=coleccion_id,
        proveedor_id=proveedor_id,
        activo=activo,
        page=page,
        size=size,
    )
    return ProductoPage(items=items, total=total, page=page, size=size)


@router.get("/productos/{producto_id}", response_model=ProductoDetalle)
def obtener_producto(  # CU4
    producto_id: int, session: SessionDep, _user: AdminOEncargado
):
    return service.get_producto_detalle(session, producto_id)


@router.post(
    "/productos", response_model=ProductoOut, status_code=status.HTTP_201_CREATED
)
def crear_producto(data: ProductoCreate, session: SessionDep, _admin: AdminUser):  # CU4
    return service.create_producto(session, data)


@router.patch("/productos/{producto_id}", response_model=ProductoOut)
def actualizar_producto(  # CU4
    producto_id: int, data: ProductoUpdate, session: SessionDep, _admin: AdminUser
):
    return service.update_producto(session, producto_id, data)


@router.delete("/productos/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_producto(producto_id: int, session: SessionDep, _admin: AdminUser):  # CU4
    service.delete_producto(session, producto_id)


# --------------------------------------------------------------------------- #
#  Variantes
# --------------------------------------------------------------------------- #
@router.post(
    "/productos/{producto_id}/variantes",
    response_model=VarianteOut,
    status_code=status.HTTP_201_CREATED,
)
def agregar_variante(  # CU4
    producto_id: int, data: VarianteCreate, session: SessionDep, _admin: AdminUser
):
    return service.add_variante(session, producto_id, data)


@router.patch("/variantes/{variante_id}", response_model=VarianteOut)
def actualizar_variante(  # CU4
    variante_id: int, data: VarianteUpdate, session: SessionDep, _admin: AdminUser
):
    return service.update_variante(session, variante_id, data)


@router.delete("/variantes/{variante_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_variante(variante_id: int, session: SessionDep, _admin: AdminUser):  # CU4
    service.delete_variante(session, variante_id)
