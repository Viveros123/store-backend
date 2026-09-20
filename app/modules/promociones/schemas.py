"""Esquemas del módulo Promociones — CU33."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class PromocionCreate(BaseModel):
    nombre: str = Field(min_length=3, max_length=100)
    descripcion: str | None = Field(default=None, max_length=500)
    tipo_descuento: Literal["PORCENTAJE", "MONTO_FIJO"]
    valor: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    fecha_inicio: date
    fecha_fin: date
    activo: bool = True
    # Productos completos (todas sus variantes) y/o variantes puntuales.
    producto_ids: list[int] = Field(default_factory=list)
    variante_ids: list[int] = Field(default_factory=list)


class PromocionUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=100)
    descripcion: str | None = Field(default=None, max_length=500)
    tipo_descuento: Literal["PORCENTAJE", "MONTO_FIJO"] | None = None
    valor: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    activo: bool | None = None
    producto_ids: list[int] | None = None
    variante_ids: list[int] | None = None


class ProductoPromocionOut(BaseModel):
    id: int
    nombre: str


class VariantePromocionOut(BaseModel):
    id: int
    producto: str
    talla: str | None
    color: str | None


class VarianteOpcionOut(VariantePromocionOut):
    producto_id: int


class PromocionOut(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    tipo_descuento: str
    valor: Decimal
    fecha_inicio: date
    fecha_fin: date
    activo: bool
    vigente: bool  # activa y dentro del rango de fechas (hoy, hora de Bolivia)
    productos: list[ProductoPromocionOut]
    variantes: list[VariantePromocionOut]
