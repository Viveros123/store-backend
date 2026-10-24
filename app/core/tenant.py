"""Utilidades para exigir el tenant del usuario autenticado."""

from fastapi import HTTPException, status

from app.modules.identidad.models import Usuario


def empresa_actual_id(usuario: Usuario) -> int:
    """Devuelve la empresa del actor o falla sin revelar datos de otro tenant."""
    if usuario.empresa_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario no está asociado a ninguna empresa",
        )
    return usuario.empresa_id
