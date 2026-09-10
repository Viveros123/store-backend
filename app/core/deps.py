"""Dependencias reutilizables para los endpoints: sesión, usuario actual, roles."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.db import get_session
from app.core.security import decode_access_token
from app.modules.identidad.models import Rol, Usuario

SessionDep = Annotated[Session, Depends(get_session)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_CRED_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciales inválidas",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
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


CurrentUser = Annotated[Usuario, Depends(get_current_user)]


def require_roles(*roles: str):
    """Uso: `_: Usuario = Depends(require_roles(RolNombre.ADMINISTRADOR))`."""

    def checker(user: CurrentUser, session: SessionDep) -> Usuario:
        rol = session.get(Rol, user.rol_id)
        if rol is None or rol.nombre not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para esta operación",
            )
        return user

    return checker
