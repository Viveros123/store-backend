"""Modelos del módulo Promociones — CU33 (Gestionar Promociones).

Una promoción da un descuento (porcentaje o monto fijo) sobre un conjunto de
productos durante un rango de fechas. Se aplica sola en catálogo, carrito y
ventas mientras esté activa y vigente.
"""

from datetime import date
from decimal import Decimal

from sqlmodel import Field, SQLModel


class TipoDescuento:
    PORCENTAJE = "PORCENTAJE"
    MONTO_FIJO = "MONTO_FIJO"


class Promocion(SQLModel, table=True):
    __tablename__ = "promocion"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=100)
    descripcion: str | None = Field(default=None, max_length=500)
    tipo_descuento: str = Field(max_length=20)
    valor: Decimal = Field(max_digits=10, decimal_places=2)
    fecha_inicio: date
    fecha_fin: date
    activo: bool = Field(default=True)


class PromocionProducto(SQLModel, table=True):
    """La promoción cubre TODAS las variantes (tallas y colores) del producto."""

    __tablename__ = "promocion_producto"

    promocion_id: int = Field(foreign_key="promocion.id", primary_key=True)
    producto_id: int = Field(foreign_key="producto.id", primary_key=True)


class PromocionVariante(SQLModel, table=True):
    """La promoción cubre solo esta variante puntual (talla + color)."""

    __tablename__ = "promocion_variante"

    promocion_id: int = Field(foreign_key="promocion.id", primary_key=True)
    variante_id: int = Field(foreign_key="producto_variante.id", primary_key=True)
