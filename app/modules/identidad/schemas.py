"""Esquemas de entrada/salida del módulo Identidad."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# --- Salida genérica de usuario ---
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


# --- Autenticación ---
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


# --- CU1: Registrar Cliente ---
class ClienteRegistroIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    apellido: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    telefono: str | None = Field(default=None, max_length=20)
