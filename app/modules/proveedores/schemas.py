"""Esquemas del módulo Proveedores."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProveedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_empresa: str
    contacto: str | None
    email: str | None
    telefono: str | None
    direccion: str | None
    activo: bool


class ProveedorCreate(BaseModel):
    nombre_empresa: str = Field(min_length=2, max_length=120)
    contacto: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    telefono: str | None = Field(default=None, max_length=20)
    direccion: str | None = Field(default=None, max_length=150)


class ProveedorUpdate(BaseModel):
    nombre_empresa: str | None = Field(default=None, min_length=2, max_length=120)
    contacto: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    telefono: str | None = Field(default=None, max_length=20)
    direccion: str | None = Field(default=None, max_length=150)
    activo: bool | None = None


class ProveedorPage(BaseModel):
    items: list[ProveedorOut]
    total: int
    page: int
    size: int


class ProveedorOpcion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_empresa: str
