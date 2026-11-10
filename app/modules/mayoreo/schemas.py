"""Esquemas del módulo Ventas al por mayor — CU53."""

from decimal import Decimal

from pydantic import BaseModel, Field


class DescuentoMayoristaCreate(BaseModel):
    variante_id: int
    cantidad_minima: int = Field(gt=1, le=100000)
    porcentaje_descuento: Decimal = Field(gt=0, le=90, max_digits=5, decimal_places=2)


class DescuentoMayoristaUpdate(BaseModel):
    cantidad_minima: int | None = Field(default=None, gt=1, le=100000)
    porcentaje_descuento: Decimal | None = Field(
        default=None, gt=0, le=90, max_digits=5, decimal_places=2
    )
    activo: bool | None = None


class VarianteOpcionOut(BaseModel):
    id: int
    producto_id: int
    producto: str
    talla: str | None
    color: str | None


class DescuentoMayoristaOut(BaseModel):
    id: int
    variante_id: int
    producto_id: int
    producto: str
    talla: str | None
    color: str | None
    cantidad_minima: int
    porcentaje_descuento: Decimal
    activo: bool
