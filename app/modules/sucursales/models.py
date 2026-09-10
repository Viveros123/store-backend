"""Modelo del módulo Sucursales."""

from sqlmodel import Field, SQLModel


class Sucursal(SQLModel, table=True):
    __tablename__ = "sucursal"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=100, index=True)
    ciudad: str = Field(max_length=80, index=True)
    direccion: str = Field(max_length=150)
    telefono: str | None = Field(default=None, max_length=20)
    horario_atencion: str | None = Field(default=None, max_length=100)
    activa: bool = Field(default=True)
