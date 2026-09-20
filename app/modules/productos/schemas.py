"""Esquemas del módulo Productos — CU4 / CU8."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- #
#  Variante
# --------------------------------------------------------------------------- #
class VarianteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    producto_id: int
    talla_id: int
    talla: str | None = None
    color_id: int
    color: str | None = None
    color_hex: str | None = None
    sku: str
    precio: Decimal | None
    precio_efectivo: Decimal | None = None  # precio o precio_base del producto
    precio_compra: Decimal | None = None
    precio_compra_efectivo: Decimal | None = None  # precio_compra o el del producto
    imagen_url: str | None = None
    imagen_efectivo: str | None = None  # imagen_url o la del producto


class VarianteCreate(BaseModel):
    talla_id: int
    color_id: int
    sku: str = Field(min_length=1, max_length=50)
    precio: Decimal | None = Field(default=None, gt=0)
    precio_compra: Decimal | None = Field(default=None, gt=0)
    imagen_url: str | None = Field(default=None, max_length=255)


class VarianteUpdate(BaseModel):
    talla_id: int | None = None
    color_id: int | None = None
    sku: str | None = Field(default=None, min_length=1, max_length=50)
    precio: Decimal | None = Field(default=None, gt=0)
    precio_compra: Decimal | None = Field(default=None, gt=0)
    imagen_url: str | None = Field(default=None, max_length=255)


# --------------------------------------------------------------------------- #
#  Producto
# --------------------------------------------------------------------------- #
class ProductoOut(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    categoria_id: int
    categoria: str | None
    coleccion_id: int | None
    coleccion: str | None
    temporada: str | None
    proveedor_id: int
    proveedor: str | None
    precio_compra: Decimal | None
    precio_base: Decimal | None
    margen: Decimal | None = None  # precio_base - precio_compra
    imagen_url: str | None
    activo: bool
    fecha_creacion: datetime
    cantidad_variantes: int = 0


class ProductoDetalle(ProductoOut):
    variantes: list[VarianteOut] = []


class ProductoCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    descripcion: str | None = Field(default=None, max_length=1000)
    categoria_id: int
    coleccion_id: int | None = None
    proveedor_id: int
    precio_compra: Decimal | None = Field(default=None, gt=0)
    precio_base: Decimal | None = Field(default=None, gt=0)
    imagen_url: str | None = Field(default=None, max_length=255)


class ProductoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    descripcion: str | None = Field(default=None, max_length=1000)
    categoria_id: int | None = None
    coleccion_id: int | None = None
    proveedor_id: int | None = None
    precio_compra: Decimal | None = Field(default=None, gt=0)
    precio_base: Decimal | None = Field(default=None, gt=0)
    imagen_url: str | None = Field(default=None, max_length=255)
    activo: bool | None = None


class ProductoPage(BaseModel):
    items: list[ProductoOut]
    total: int
    page: int
    size: int


class ProductoOpcion(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


# --------------------------------------------------------------------------- #
#  Catálogo público (CU9) — sin costos ni datos internos
# --------------------------------------------------------------------------- #
class ColorMini(BaseModel):
    id: int
    nombre: str
    codigo_hex: str | None


class CatalogoProductoOut(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    categoria: str | None
    coleccion: str | None
    temporada: str | None
    precio_base: Decimal
    # CU33: precio con la mejor promoción vigente (None si no hay ninguna).
    precio_promocional: Decimal | None = None
    promocion: str | None = None
    imagen_url: str | None
    colores: list[ColorMini] = []
    cantidad_variantes: int = 0


class CatalogoVarianteOut(BaseModel):
    id: int
    talla_id: int
    talla: str | None
    color_id: int
    color: str | None
    color_hex: str | None
    precio_efectivo: Decimal
    precio_promocional: Decimal | None = None
    promocion: str | None = None  # nombre de la promoción que aplica a esta variante
    imagen_efectivo: str | None = None


class CatalogoProductoDetalle(CatalogoProductoOut):
    variantes: list[CatalogoVarianteOut] = []


class CatalogoProductoPage(BaseModel):
    items: list[CatalogoProductoOut]
    total: int
    page: int
    size: int
