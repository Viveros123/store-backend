"""Modelos del módulo Sucursales."""

from datetime import time

from sqlmodel import Field, SQLModel, UniqueConstraint


class Sucursal(SQLModel, table=True):
    __tablename__ = "sucursal"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=100, index=True)
    ciudad: str = Field(max_length=80, index=True)
    direccion: str = Field(max_length=150)
    telefono: str | None = Field(default=None, max_length=20)
    horario_atencion: str | None = Field(default=None, max_length=100)
    activa: bool = Field(default=True)


class SucursalHorario(SQLModel, table=True):
    """Horario de atención por día de semana — CU16 (reservas).

    dia_semana sigue la convención de `date.weekday()`: 0=Lunes … 6=Domingo.
    """

    __tablename__ = "sucursal_horario"
    __table_args__ = (
        UniqueConstraint("sucursal_id", "dia_semana", name="uq_horario_sucursal_dia"),
    )

    id: int | None = Field(default=None, primary_key=True)
    sucursal_id: int = Field(foreign_key="sucursal.id")
    dia_semana: int = Field(ge=0, le=6)
    cerrado: bool = Field(default=False)
    hora_apertura: time | None = Field(default=None)
    hora_cierre: time | None = Field(default=None)
