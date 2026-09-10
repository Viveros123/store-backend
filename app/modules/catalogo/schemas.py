"""Esquemas del módulo Catálogo (CU5 y CU6)."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.catalogo.models import TallaTipo


# --------------------------------------------------------------------------- #
#  Categoría
# --------------------------------------------------------------------------- #
class CategoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    descripcion: str | None
    activo: bool


class CategoriaCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    descripcion: str | None = Field(default=None, max_length=300)


class CategoriaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    descripcion: str | None = Field(default=None, max_length=300)
    activo: bool | None = None


# --------------------------------------------------------------------------- #
#  Talla
# --------------------------------------------------------------------------- #
class TallaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    valor: str
    tipo: str
    activo: bool


class TallaCreate(BaseModel):
    valor: str = Field(min_length=1, max_length=10)
    tipo: str = Field(default=TallaTipo.ROPA, max_length=20)

    @field_validator("tipo")
    @classmethod
    def _tipo_valido(cls, v: str) -> str:
        if v not in TallaTipo.TODOS:
            raise ValueError(f"tipo debe ser uno de {TallaTipo.TODOS}")
        return v


class TallaUpdate(BaseModel):
    valor: str | None = Field(default=None, min_length=1, max_length=10)
    tipo: str | None = Field(default=None, max_length=20)
    activo: bool | None = None

    @field_validator("tipo")
    @classmethod
    def _tipo_valido(cls, v: str | None) -> str | None:
        if v is not None and v not in TallaTipo.TODOS:
            raise ValueError(f"tipo debe ser uno de {TallaTipo.TODOS}")
        return v


# --------------------------------------------------------------------------- #
#  Color
# --------------------------------------------------------------------------- #
class ColorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    codigo_hex: str | None
    activo: bool


class ColorCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=40)
    codigo_hex: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class ColorUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=40)
    codigo_hex: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    activo: bool | None = None


# --------------------------------------------------------------------------- #
#  Temporada (CU6)
# --------------------------------------------------------------------------- #
class TemporadaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    fecha_inicio: date | None
    fecha_fin: date | None
    activo: bool


class TemporadaCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=60)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None

    @model_validator(mode="after")
    def _rango(self):
        if (
            self.fecha_inicio
            and self.fecha_fin
            and self.fecha_fin < self.fecha_inicio
        ):
            raise ValueError("fecha_fin no puede ser anterior a fecha_inicio")
        return self


class TemporadaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=60)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    activo: bool | None = None


# --------------------------------------------------------------------------- #
#  Colección (CU6)
# --------------------------------------------------------------------------- #
class ColeccionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    descripcion: str | None
    temporada_id: int
    temporada: str | None = None
    activo: bool


class ColeccionCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    descripcion: str | None = Field(default=None, max_length=300)
    temporada_id: int


class ColeccionUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    descripcion: str | None = Field(default=None, max_length=300)
    temporada_id: int | None = None
    activo: bool | None = None


# --------------------------------------------------------------------------- #
#  Páginas
# --------------------------------------------------------------------------- #
class _PageBase(BaseModel):
    total: int
    page: int
    size: int


class CategoriaPage(_PageBase):
    items: list[CategoriaOut]


class TallaPage(_PageBase):
    items: list[TallaOut]


class ColorPage(_PageBase):
    items: list[ColorOut]


class TemporadaPage(_PageBase):
    items: list[TemporadaOut]


class ColeccionPage(_PageBase):
    items: list[ColeccionOut]
