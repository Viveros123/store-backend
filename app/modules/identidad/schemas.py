"""Esquemas de entrada/salida del módulo Identidad."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# --------------------------------------------------------------------------- #
#  Roles
# --------------------------------------------------------------------------- #
class RolOut(BaseModel):
    id: int
    nombre: str


# --------------------------------------------------------------------------- #
#  Usuarios
# --------------------------------------------------------------------------- #
class UsuarioOut(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: EmailStr
    telefono: str | None
    rol_id: int
    rol: str | None = None
    sucursal_id: int | None
    proveedor_id: int | None
    activo: bool
    fecha_registro: datetime


class UsuarioCreate(BaseModel):
    """CU3 — el administrador da de alta un usuario (de cualquier rol)."""

    nombre: str = Field(min_length=2, max_length=80)
    apellido: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    telefono: str | None = Field(default=None, max_length=20)
    rol_id: int
    sucursal_id: int | None = None
    proveedor_id: int | None = None


class UsuarioUpdate(BaseModel):
    """CU3 — edición. Todos los campos son opcionales."""

    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    apellido: str | None = Field(default=None, min_length=2, max_length=80)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)
    telefono: str | None = Field(default=None, max_length=20)
    rol_id: int | None = None
    sucursal_id: int | None = None
    proveedor_id: int | None = None
    activo: bool | None = None


class UsuarioPage(BaseModel):
    items: list[UsuarioOut]
    total: int
    page: int
    size: int


# --------------------------------------------------------------------------- #
#  Autenticación
# --------------------------------------------------------------------------- #
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


class ClienteRegistroIn(BaseModel):
    """CU1 — registro público: crea una cuenta con rol Cliente."""

    nombre: str = Field(min_length=2, max_length=80)
    apellido: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    telefono: str | None = Field(default=None, max_length=20)


class MiCuentaUpdate(BaseModel):
    """CU2 — el usuario edita sus propios datos."""

    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    apellido: str | None = Field(default=None, min_length=2, max_length=80)
    telefono: str | None = Field(default=None, max_length=20)


class CambioPasswordIn(BaseModel):
    """CU2 — cambio de la propia contraseña."""

    password_actual: str
    password_nueva: str = Field(min_length=8, max_length=72)
