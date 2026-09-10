"""Esquemas del módulo Sucursales."""

from pydantic import BaseModel, ConfigDict, Field


class SucursalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    ciudad: str
    direccion: str
    telefono: str | None
    horario_atencion: str | None
    activa: bool


class SucursalCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    ciudad: str = Field(min_length=2, max_length=80)
    direccion: str = Field(min_length=3, max_length=150)
    telefono: str | None = Field(default=None, max_length=20)
    horario_atencion: str | None = Field(default=None, max_length=100)


class SucursalUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    ciudad: str | None = Field(default=None, min_length=2, max_length=80)
    direccion: str | None = Field(default=None, min_length=3, max_length=150)
    telefono: str | None = Field(default=None, max_length=20)
    horario_atencion: str | None = Field(default=None, max_length=100)
    activa: bool | None = None


class SucursalPage(BaseModel):
    items: list[SucursalOut]
    total: int
    page: int
    size: int


class SucursalOpcion(BaseModel):
    """Versión liviana para selects."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    ciudad: str
