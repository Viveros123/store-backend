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


# --------------------------------------------------------------------------- #
#  CU24/25/26 — Venta presencial, pago en caja, comprobante (rol Cajero)
# --------------------------------------------------------------------------- #
class ClienteBuscarOut(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str
    telefono: str | None


class ItemVentaPresencialIn(BaseModel):
    variante_id: int
    cantidad: int = Field(gt=0, le=50)


class VentaPresencialCreate(BaseModel):
    cliente_id: int
    items: list[ItemVentaPresencialIn] = Field(min_length=1)


class VentaCajaOut(VentaOut):
    cliente_id: int
    cliente_nombre: str
    cajero_nombre: str | None = None


class PagoCajaCreate(BaseModel):
    metodo: str = Field(description="EFECTIVO o TARJETA_CAJA")
    monto_recibido: Decimal | None = None


class ComprobanteOut(BaseModel):
    venta_id: int
    fecha_creacion: datetime
    sucursal: str
    ciudad: str
    direccion: str
    cliente_nombre: str
    cliente_email: str
    cajero_nombre: str | None
    items: list[ItemVentaOut]
    total: Decimal
    metodo_pago: str
    monto_recibido: Decimal | None
    vuelto: Decimal | None
