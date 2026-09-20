"""Modelos del módulo Reservas — CU16 (Reservar Prendas).

El cliente reserva un turno de 30 o 60 minutos en una sucursal para
probarse una o más prendas (variantes concretas). Mientras la reserva
está activa, esas unidades pasan de `cantidad_disponible` a
`cantidad_reservada` en Inventario (CU12/CU13).
"""

from datetime import date, datetime, time, timezone

from sqlmodel import Field, SQLModel


class EstadoReserva:
    PENDIENTE = "PENDIENTE"
    NOTIFICADA = "NOTIFICADA"
    PREPARADA = "PREPARADA"
    ATENDIDA = "ATENDIDA"
    COMPLETADA = "COMPLETADA"
    CANCELADA = "CANCELADA"
    EXPIRADA = "EXPIRADA"

    # Estados que todavía "ocupan" el turno y el stock reservado.
    ACTIVOS = (PENDIENTE, NOTIFICADA, PREPARADA, ATENDIDA)


class Reserva(SQLModel, table=True):
    __tablename__ = "reserva"

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="usuario.id")
    sucursal_id: int = Field(foreign_key="sucursal.id")

    fecha: date
    hora_inicio: time
    hora_fin: time
    duracion_minutos: int

    estado: str = Field(default=EstadoReserva.PENDIENTE, max_length=20)
    fecha_creacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ReservaDetalle(SQLModel, table=True):
    __tablename__ = "reserva_detalle"

    id: int | None = Field(default=None, primary_key=True)
    reserva_id: int = Field(foreign_key="reserva.id")
    variante_id: int = Field(foreign_key="producto_variante.id")
    cantidad: int = Field(gt=0)
    # Cuántas unidades se llevó el cliente al finalizar la reserva; el resto
    # se devolvió al stock. NULL = la reserva todavía no se finalizó.
    cantidad_llevada: int | None = Field(default=None, ge=0)
