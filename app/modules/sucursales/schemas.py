"""Esquemas del módulo Sucursales."""

from datetime import time

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SucursalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    ciudad: str
    direccion: str
    telefono: str | None
    horario_atencion: str | None
    activa: bool


class SucursalCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    ciudad: str = Field(min_length=2, max_length=80)
    direccion: str = Field(min_length=3, max_length=150)
    telefono: str | None = Field(default=None, max_length=20)
    horario_atencion: str | None = Field(default=None, max_length=100)


class SucursalUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    ciudad: str | None = Field(default=None, min_length=2, max_length=80)
    direccion: str | None = Field(default=None, min_length=3, max_length=150)
    telefono: str | None = Field(default=None, max_length=20)
    horario_atencion: str | None = Field(default=None, max_length=100)
    activa: bool | None = None


class SucursalPage(BaseModel):
    items: list[SucursalOut]
    total: int
    page: int
    size: int


class SucursalOpcion(BaseModel):
    """Versión liviana para selects."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    ciudad: str


# --------------------------------------------------------------------------- #
#  CU16 — Horarios de atención (para reservas)
# --------------------------------------------------------------------------- #
class HorarioDia(BaseModel):
    dia_semana: int = Field(ge=0, le=6)
    cerrado: bool = False
    hora_apertura: time | None = None
    hora_cierre: time | None = None

    @model_validator(mode="after")
    def _validar_horas(self) -> "HorarioDia":
        if not self.cerrado:
            if self.hora_apertura is None or self.hora_cierre is None:
                raise ValueError("Si el día no está cerrado, hace falta apertura y cierre")
            if self.hora_apertura >= self.hora_cierre:
                raise ValueError("La hora de apertura debe ser antes que la de cierre")
        return self


class HorarioSemana(BaseModel):
    """Los 7 días, para guardar todos juntos."""

    dias: list[HorarioDia] = Field(min_length=7, max_length=7)
