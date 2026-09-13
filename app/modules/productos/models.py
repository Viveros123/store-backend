"""Modelos del módulo Productos — CU4.

Producto = la prenda (ej. "Polera manga corta básica").
ProductoVariante = una combinación concreta talla + color, con su SKU.
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import Field, SQLModel, UniqueConstraint


class Producto(SQLModel, table=True):
    __tablename__ = "producto"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=120, index=True)
    descripcion: str | None = Field(default=None, max_length=1000)

    categoria_id: int = Field(foreign_key="categoria.id")
    coleccion_id: int | None = Field(default=None, foreign_key="coleccion.id")
    proveedor_id: int = Field(foreign_key="proveedor.id")

    # Precio que el proveedor cobra por unidad (referencia). Lo carga el proveedor.
    precio_compra: Decimal | None = Field(
        default=None, max_digits=10, decimal_places=2
    )
    # Precio de venta al público. Lo fija el administrador; NULL = todavía sin precio.
    precio_base: Decimal | None = Field(
        default=None, max_digits=10, decimal_places=2
    )
    imagen_url: str | None = Field(default=None, max_length=255)

    activo: bool = Field(default=True)
    fecha_creacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ProductoVariante(SQLModel, table=True):
    __tablename__ = "producto_variante"
    __table_args__ = (
        UniqueConstraint(
            "producto_id", "talla_id", "color_id", name="uq_variante_prod_talla_color"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    producto_id: int = Field(foreign_key="producto.id")
    talla_id: int = Field(foreign_key="talla.id")
    color_id: int = Field(foreign_key="color.id")

    sku: str = Field(max_length=50, unique=True, index=True)
    # Si es NULL, se usa el precio_base del producto.
    precio: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    # Precio que cobra el proveedor por ESTA variante puntual (lo carga el
    # proveedor). Si es NULL, se usa el precio_compra general del producto.
    precio_compra: Decimal | None = Field(
        default=None, max_digits=10, decimal_places=2
    )
    # Si es NULL, se usa la imagen_url del producto (ej. variantes de otro color).
    imagen_url: str | None = Field(default=None, max_length=255)
