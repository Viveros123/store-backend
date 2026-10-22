"""Dependencias reutilizables para los endpoints: sesión, usuario actual, roles."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.db import get_session
from app.core.security import decode_access_token
from app.modules.identidad.models import Rol, RolNombre, Usuario

SessionDep = Annotated[Session, Depends(get_session)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/auth/login", auto_error=False
)

_CRED_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciales inválidas",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_authenticated_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
) -> Usuario:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except Exception:  # noqa: BLE001 - cualquier fallo => token inválido
        raise _CRED_EXC

    user = session.get(Usuario, user_id)
    if user is None or not user.activo:
        raise _CRED_EXC
    return user


AuthenticatedUser = Annotated[Usuario, Depends(get_authenticated_user)]


def get_optional_authenticated_user(
    token: Annotated[str | None, Depends(oauth2_scheme_optional)],
    session: SessionDep,
) -> Usuario | None:
    """Devuelve el usuario del token cuando existe, sin cerrar rutas públicas.

    El catálogo sigue disponible para visitantes, pero puede usar el tenant del
    cliente autenticado para no mezclar productos entre empresas.
    """
    if token is None:
        return None
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except Exception:  # noqa: BLE001 - un token inválido equivale a visitante
        return None
    user = session.get(Usuario, user_id)
    return user if user is not None and user.activo else None


OptionalAuthenticatedUser = Annotated[
    Usuario | None, Depends(get_optional_authenticated_user)
]


def get_current_user(user: AuthenticatedUser, session: SessionDep) -> Usuario:
    """Usuario con acceso operativo; respeta la suspensión de su empresa."""
    rol = session.get(Rol, user.rol_id)
    if rol is not None and rol.nombre == RolNombre.SUPERADMINISTRADOR:
        return user
    if user.empresa_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no está asociado a una empresa",
        )
    from app.modules.saas.models import Empresa

    empresa = session.get(Empresa, user.empresa_id)
    if empresa is None or not empresa.activa:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La empresa está suspendida",
        )
    return user


CurrentUser = Annotated[Usuario, Depends(get_current_user)]


def require_roles(*roles: str, allow_inactive_empresa: bool = False):
    """Uso: `_: Usuario = Depends(require_roles(RolNombre.ADMINISTRADOR))`."""

    dependency = get_authenticated_user if allow_inactive_empresa else get_current_user

    def checker(
        user: Annotated[Usuario, Depends(dependency)], session: SessionDep
    ) -> Usuario:
        rol = session.get(Rol, user.rol_id)
        es_superadmin = rol is not None and rol.nombre == RolNombre.SUPERADMINISTRADOR
        if rol is None or (rol.nombre not in roles and not es_superadmin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para esta operación",
            )
        if not es_superadmin and allow_inactive_empresa:
            if user.empresa_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="El usuario no está asociado a una empresa",
                )
        return user

    return checker
