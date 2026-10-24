from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class VarianteOfflineOut(BaseModel):
    id: int
    sku: str
    talla_id: int
    talla: str
    color_id: int
    color: str
    codigo_hex: str | None
    precio: Decimal | None
    imagen_url: str | None
    cantidad_disponible: int
    cantidad_reservada: int


class ProductoOfflineOut(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    categoria_id: int
    categoria: str
    precio_base: Decimal | None
    imagen_url: str | None
    variantes: list[VarianteOfflineOut]


class DatosOfflineOut(BaseModel):
    schema_version: int = 1
    version_datos: str
    empresa_id: int
    sucursal_id: int
    sucursal_nombre: str
    generado_en: datetime
    productos: list[ProductoOfflineOut]
    total_productos: int
    total_variantes: int
