"""CU8 — Portal del proveedor: registra/edita la información de SUS productos.

Los productos que crea el proveedor quedan inactivos hasta que el
administrador los active.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import CurrentUser, SessionDep, require_roles
from app.modules.identidad.models import RolNombre, Usuario
from app.modules.productos import service
from app.modules.productos.schemas import (
    ProductoCreate,
    ProductoDetalle,
    ProductoOut,
    ProductoPage,
    ProductoUpdate,
    VarianteCreate,
    VarianteOut,
    VarianteUpdate,
)

router = APIRouter(prefix="/portal-proveedor", tags=["portal-proveedor"])

ProveedorUser = Annotated[
    Usuario, Depends(require_roles(RolNombre.PROVEEDOR))
]


def _proveedor_id(user: Usuario) -> int:
    if user.proveedor_id is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Tu cuenta no está vinculada a ningún proveedor. Contactá al administrador.",
        )
    return user.proveedor_id


@router.get("/productos", response_model=ProductoPage)
def mis_productos(  # CU8
    session: SessionDep,
    user: ProveedorUser,
    q: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    items, total = service.list_productos_proveedor(
        session, _proveedor_id(user), q=q, page=page, size=size
    )
    return ProductoPage(items=items, total=total, page=page, size=size)


@router.get("/productos/{producto_id}", response_model=ProductoDetalle)
def mi_producto(producto_id: int, session: SessionDep, user: ProveedorUser):  # CU8
    return service.get_detalle_proveedor(session, producto_id, _proveedor_id(user))


@router.post(
    "/productos", response_model=ProductoOut, status_code=status.HTTP_201_CREATED
)
def registrar_producto(  # CU8
    data: ProductoCreate, session: SessionDep, user: ProveedorUser
):
    return service.create_producto_proveedor(session, _proveedor_id(user), data)


@router.patch("/productos/{producto_id}", response_model=ProductoOut)
def editar_producto(  # CU8
    producto_id: int,
    data: ProductoUpdate,
    session: SessionDep,
    user: ProveedorUser,
):
    return service.update_producto_proveedor(
        session, producto_id, _proveedor_id(user), data
    )


@router.delete("/productos/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_producto(  # CU8
    producto_id: int, session: SessionDep, user: ProveedorUser
):
    service.delete_producto_proveedor(session, producto_id, _proveedor_id(user))


@router.post(
    "/productos/{producto_id}/variantes",
    response_model=VarianteOut,
    status_code=status.HTTP_201_CREATED,
)
def agregar_variante(  # CU8
    producto_id: int,
    data: VarianteCreate,
    session: SessionDep,
    user: ProveedorUser,
):
    return service.add_variante_proveedor(
        session, producto_id, _proveedor_id(user), data
    )


@router.patch("/variantes/{variante_id}", response_model=VarianteOut)
def editar_variante(  # CU8
    variante_id: int,
    data: VarianteUpdate,
    session: SessionDep,
    user: ProveedorUser,
):
    return service.update_variante_proveedor(
        session, variante_id, _proveedor_id(user), data
    )


@router.delete("/variantes/{variante_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_variante(  # CU8
    variante_id: int, session: SessionDep, user: ProveedorUser
):
    service.delete_variante_proveedor(session, variante_id, _proveedor_id(user))


@router.get("/perfil")
def mi_empresa(session: SessionDep, user: ProveedorUser, _: CurrentUser):  # CU8
    from app.modules.proveedores.models import Proveedor

    prov = session.get(Proveedor, _proveedor_id(user))
    return {
        "id": prov.id,
        "nombre_empresa": prov.nombre_empresa,
        "email": prov.email,
        "telefono": prov.telefono,
    }
