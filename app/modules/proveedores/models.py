"""Modelo del módulo Proveedores."""

from sqlmodel import Field, SQLModel


class Proveedor(SQLModel, table=True):
    __tablename__ = "proveedor"

    id: int | None = Field(default=None, primary_key=True)
    nombre_empresa: str = Field(max_length=120, index=True)
    contacto: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=120)
    telefono: str | None = Field(default=None, max_length=20)
    direccion: str | None = Field(default=None, max_length=150)
    activo: bool = Field(default=True)
