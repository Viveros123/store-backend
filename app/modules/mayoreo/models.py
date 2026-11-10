"""Modelos del módulo Ventas al por mayor — CU53.

Una regla de mayoreo da un porcentaje de descuento automático a UNA variante
puntual cuando el cliente lleva una cantidad igual o mayor a la mínima
configurada. A diferencia de las promociones (CU49), no tiene rango de
fechas: queda vigente mientras esté activa.
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import Field, SQLModel


class DescuentoMayorista(SQLModel, table=True):
    __tablename__ = "descuento_mayorista"

    id: int | None = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    # Una sola regla de mayoreo activa por variante.
    variante_id: int = Field(foreign_key="producto_variante.id", unique=True, index=True)
    cantidad_minima: int = Field(gt=1)
    porcentaje_descuento: Decimal = Field(max_digits=5, decimal_places=2)
    activo: bool = Field(default=True)
    creado_por_id: int = Field(foreign_key="usuario.id")
    fecha_creacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
