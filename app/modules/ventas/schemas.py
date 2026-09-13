"""Esquemas del módulo Ventas y Pagos — CU21 (carrito)."""

from decimal import Decimal

from pydantic import BaseModel, Field


class ItemCarritoCreate(BaseModel):
    variante_id: int
    cantidad: int = Field(gt=0, le=20)


class ItemCarritoUpdate(BaseModel):
    cantidad: int = Field(gt=0, le=20)


class ItemCarritoOut(BaseModel):
    id: int
    variante_id: int
    producto_id: int | None
    producto: str | None
    talla: str | None
    color: str | None
    sku: str | None
    imagen_efectivo: str | None
    precio_unitario: Decimal | None
    cantidad: int
    subtotal: Decimal | None
    disponible: bool  # si sigue existiendo stock de esta prenda en alguna sucursal


class CarritoOut(BaseModel):
    id: int
    estado: str
    items: list[ItemCarritoOut] = []
    cantidad_items: int
    total: Decimal
