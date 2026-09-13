"""Esquemas del módulo Ventas y Pagos — CU21 (carrito), CU22/27/28 (compra web y pago)."""

from datetime import datetime
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


# --------------------------------------------------------------------------- #
#  CU22 — Comprar desde Plataforma Web
# --------------------------------------------------------------------------- #
class CheckoutCreate(BaseModel):
    sucursal_id: int = Field(description="Sucursal donde el cliente retira la compra")


class ItemVentaOut(BaseModel):
    id: int
    variante_id: int
    producto_id: int | None
    producto: str | None
    talla: str | None
    color: str | None
    sku: str | None
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal


class VentaOut(BaseModel):
    id: int
    sucursal_id: int
    sucursal: str | None
    ciudad: str | None
    estado: str
    total: Decimal
    fecha_creacion: datetime
    items: list[ItemVentaOut] = []


# --------------------------------------------------------------------------- #
#  CU27/CU28 — Pago electrónico (Stripe/QR) y confirmación
# --------------------------------------------------------------------------- #
class PagoOut(BaseModel):
    id: int
    venta_id: int
    metodo: str
    estado: str
    monto: Decimal
    checkout_url: str | None = None
    qr_data_url: str | None = None
    fecha_creacion: datetime


class EstadoPagoOut(BaseModel):
    venta_id: int
    venta_estado: str
    pago_id: int | None
    pago_estado: str | None
