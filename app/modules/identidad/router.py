"""Endpoints del módulo Identidad: autenticación (CU2 base) y gestión de usuarios (CU3)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.deps import CurrentUser, SessionDep, require_roles
from app.core.security import create_access_token
from app.modules.identidad import service
from app.modules.identidad.models import RolNombre, Usuario
from app.modules.identidad.schemas import (
    CambioPasswordIn,
    ClienteRegistroIn,
    MiCuentaUpdate,
    RolOut,
    TokenOut,
    UsuarioCreate,
    UsuarioOut,
    UsuarioPage,
    UsuarioUpdate,
)

router = APIRouter()

# Usuario autenticado que además es Administrador.
AdminUser = Annotated[Usuario, Depends(require_roles(RolNombre.ADMINISTRADOR))]


# --------------------------------------------------------------------------- #
#  Autenticación
# --------------------------------------------------------------------------- #
@router.post(
    "/auth/registro",
    response_model=TokenOut,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
)
def registro(data: ClienteRegistroIn, session: SessionDep):  # CU1
    usuario = service.registrar_cliente(session, data)
    token = create_access_token(usuario.id)
    return TokenOut(
        access_token=token,
        usuario=service.to_usuario_out(session, usuario),
    )


@router.post("/auth/login", response_model=TokenOut, tags=["auth"])
def login(  # CU2 (base)
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
):
    usuario = service.authenticate(session, form.username, form.password)
    token = create_access_token(usuario.id)
    return TokenOut(
        access_token=token,
        usuario=service.to_usuario_out(session, usuario),
    )


@router.get("/auth/me", response_model=UsuarioOut, tags=["auth"])
def me(current: CurrentUser, session: SessionDep):  # CU2
    return service.to_usuario_out(session, current)


@router.patch("/auth/me", response_model=UsuarioOut, tags=["auth"])
def actualizar_mi_cuenta(  # CU2
    data: MiCuentaUpdate, current: CurrentUser, session: SessionDep
):
    usuario = service.actualizar_mi_cuenta(session, current, data)
    return service.to_usuario_out(session, usuario)


@router.post(
    "/auth/cambiar-password",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["auth"],
)
def cambiar_password(  # CU2
    data: CambioPasswordIn, current: CurrentUser, session: SessionDep
):
    service.cambiar_password(session, current, data)


# --------------------------------------------------------------------------- #
#  CU3 — Roles
# --------------------------------------------------------------------------- #
@router.get("/roles", response_model=list[RolOut], tags=["identidad"])
def listar_roles(session: SessionDep, _: CurrentUser):  # CU3
    return service.list_roles(session)


# --------------------------------------------------------------------------- #
#  CU3 — Usuarios
# --------------------------------------------------------------------------- #
@router.get("/usuarios", response_model=UsuarioPage, tags=["identidad"])
def listar_usuarios(  # CU3
    session: SessionDep,
    _admin: AdminUser,
    q: str | None = Query(default=None, description="Busca en nombre, apellido o email"),
    rol_id: int | None = None,
    activo: bool | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    items, total = service.list_usuarios(
        session, q=q, rol_id=rol_id, activo=activo, page=page, size=size
    )
    return UsuarioPage(
        items=[service.to_usuario_out(session, u) for u in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/usuarios/{usuario_id}", response_model=UsuarioOut, tags=["identidad"])
def obtener_usuario(usuario_id: int, session: SessionDep, _admin: AdminUser):  # CU3
    usuario = session.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    return service.to_usuario_out(session, usuario)


@router.post(
    "/usuarios",
    response_model=UsuarioOut,
    status_code=status.HTTP_201_CREATED,
    tags=["identidad"],
)
def crear_usuario(data: UsuarioCreate, session: SessionDep, _admin: AdminUser):  # CU3
    usuario = service.create_usuario(session, data)
    return service.to_usuario_out(session, usuario)


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioOut, tags=["identidad"])
def actualizar_usuario(  # CU3
    usuario_id: int,
    data: UsuarioUpdate,
    session: SessionDep,
    admin: AdminUser,
):
    usuario = service.update_usuario(session, usuario_id, data, actor_id=admin.id)
    return service.to_usuario_out(session, usuario)
