"""Modelos del módulo Ventas y Pagos — CU21 en adelante.

Por ahora solo el carrito (CU21). Venta/VentaDetalle/Pago se agregan
cuando lleguemos a CU22/24-28 (compra web, venta presencial, pagos).
"""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel, UniqueConstraint


class EstadoCarrito:
    ACTIVO = "ACTIVO"
    CONVERTIDO = "CONVERTIDO"
    ABANDONADO = "ABANDONADO"


class Carrito(SQLModel, table=True):
    __tablename__ = "carrito"

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="usuario.id")
    estado: str = Field(default=EstadoCarrito.ACTIVO, max_length=20)
    fecha_creacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    fecha_actualizacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class CarritoDetalle(SQLModel, table=True):
    __tablename__ = "carrito_detalle"
    __table_args__ = (
        UniqueConstraint("carrito_id", "variante_id", name="uq_carrito_variante"),
    )

    id: int | None = Field(default=None, primary_key=True)
    carrito_id: int = Field(foreign_key="carrito.id")
    variante_id: int = Field(foreign_key="producto_variante.id")
    cantidad: int = Field(gt=0)
