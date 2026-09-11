"""Modelo del módulo Inventario — CU12/CU13.

Stock actual por variante (talla+color) y sucursal. Los movimientos con
historial (entradas por compra, salidas por venta, ajustes) se agregan en
CU14 sobre esta misma tabla.
"""

from sqlmodel import Field, SQLModel, UniqueConstraint


class Inventario(SQLModel, table=True):
    __tablename__ = "inventario"
    __table_args__ = (
        UniqueConstraint(
            "variante_id", "sucursal_id", name="uq_inventario_variante_sucursal"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    variante_id: int = Field(foreign_key="producto_variante.id")
    sucursal_id: int = Field(foreign_key="sucursal.id")
    cantidad_disponible: int = Field(default=0, ge=0)
    cantidad_reservada: int = Field(default=0, ge=0)
