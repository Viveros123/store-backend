"""Lógica de negocio del módulo Identidad."""

from sqlmodel import Session, select

from app.modules.identidad.models import Rol, Usuario
from app.modules.identidad.schemas import UsuarioOut


def get_rol_by_nombre(session: Session, nombre: str) -> Rol | None:
    return session.exec(select(Rol).where(Rol.nombre == nombre)).first()


def get_usuario_by_email(session: Session, email: str) -> Usuario | None:
    return session.exec(select(Usuario).where(Usuario.email == email)).first()


def to_usuario_out(session: Session, usuario: Usuario) -> UsuarioOut:
    rol = session.get(Rol, usuario.rol_id)
    return UsuarioOut(
        id=usuario.id,
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        email=usuario.email,
        telefono=usuario.telefono,
        rol_id=usuario.rol_id,
        rol=rol.nombre if rol else None,
        sucursal_id=usuario.sucursal_id,
        proveedor_id=usuario.proveedor_id,
        activo=usuario.activo,
        fecha_registro=usuario.fecha_registro,
    )
