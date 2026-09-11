"""Esquemas del módulo Inventario — CU12/CU13."""

from pydantic import BaseModel, Field


class InventarioOut(BaseModel):
    id: int
    variante_id: int
    producto_id: int | None
    producto: str | None
    talla: str | None
    color: str | None
    color_hex: str | None
    sku: str | None
    sucursal_id: int
    sucursal: str | None
    ciudad: str | None
    cantidad_disponible: int
    cantidad_reservada: int
    estado: str  # DISPONIBLE / AGOTADO


class InventarioPage(BaseModel):
    items: list[InventarioOut]
    total: int
    page: int
    size: int


class InventarioAjuste(BaseModel):
    variante_id: int
    sucursal_id: int
    cantidad_disponible: int = Field(ge=0)


class DisponibilidadSucursal(BaseModel):
    sucursal_id: int
    sucursal: str
    ciudad: str
    cantidad_disponible: int
