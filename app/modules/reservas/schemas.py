"""Esquemas del módulo Reservas — CU16."""

from datetime import date, datetime, time

from pydantic import BaseModel, Field


class ItemReservaCreate(BaseModel):
    variante_id: int
    cantidad: int = Field(gt=0, le=20)


class ReservaCreate(BaseModel):
    sucursal_id: int
    fecha: date
    hora_inicio: time
    duracion_minutos: int = Field(description="30 o 60")
    items: list[ItemReservaCreate] = Field(min_length=1, max_length=10)


class ItemReservaOut(BaseModel):
    variante_id: int
    producto_id: int | None
    producto: str | None
    talla: str | None
    color: str | None
    sku: str | None
    cantidad: int


class ReservaOut(BaseModel):
    id: int
    sucursal_id: int
    sucursal: str | None
    ciudad: str | None
    fecha: date
    hora_inicio: time
    hora_fin: time
    duracion_minutos: int
    estado: str
    fecha_creacion: datetime
    items: list[ItemReservaOut] = []


class SlotsDisponibilidad(BaseModel):
    fecha: date
    duracion_minutos: int
    cerrado: bool
    slots: list[time]
