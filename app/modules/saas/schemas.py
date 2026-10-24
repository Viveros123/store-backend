"""Contratos HTTP del módulo SaaS (CU38-CU42)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.modules.saas.models import EstadoSuscripcion


class AdminInicialIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    apellido: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    telefono: str | None = Field(default=None, max_length=20)


class EmpresaCreate(BaseModel):
    identificador: str = Field(
        min_length=3, max_length=50, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    nombre: str = Field(min_length=2, max_length=120)
    razon_social: str | None = Field(default=None, max_length=150)
    administrador: AdminInicialIn
    plan_id: int
    fecha_inicio: date = Field(default_factory=date.today)
    vigencia_meses: int = Field(default=1, ge=1, le=120)

    @field_validator("identificador")
    @classmethod
    def normalizar_identificador(cls, value: str) -> str:
        return value.strip().lower()


class EmpresaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    razon_social: str | None = Field(default=None, max_length=150)
    activa: bool | None = None


class EmpresaOut(BaseModel):
    id: int
    identificador: str
    nombre: str
    razon_social: str | None
    activa: bool
    fecha_registro: datetime
    fecha_actualizacion: datetime
    plan_nombre: str | None = None
    suscripcion_estado: str | None = None
    fecha_vencimiento: date | None = None


class EmpresaPage(BaseModel):
    items: list[EmpresaOut]
    total: int
    page: int
    size: int


class LimitePlanIn(BaseModel):
    codigo: str = Field(min_length=2, max_length=50, pattern=r"^[A-Z0-9_]+$")
    valor_maximo: int = Field(ge=0)


class FuncionalidadPlanIn(BaseModel):
    codigo: str = Field(min_length=2, max_length=50, pattern=r"^[A-Z0-9_]+$")
    habilitada: bool = True


class LimitePlanOut(LimitePlanIn):
    id: int


class FuncionalidadPlanOut(FuncionalidadPlanIn):
    id: int


class PlanUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=60)
    descripcion: str | None = Field(default=None, max_length=300)
    precio_mensual: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    activo: bool | None = None
    limites: list[LimitePlanIn] | None = None
    funcionalidades: list[FuncionalidadPlanIn] | None = None

    @model_validator(mode="after")
    def validar_codigos_unicos(self) -> "PlanUpdate":
        for campo in ("limites", "funcionalidades"):
            valores = getattr(self, campo)
            if valores is not None:
                codigos = [item.codigo for item in valores]
                if len(codigos) != len(set(codigos)):
                    raise ValueError(f"No se permiten códigos duplicados en {campo}")
        return self


class PlanOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    descripcion: str | None
    precio_mensual: Decimal
    activo: bool
    fecha_creacion: datetime
    limites: list[LimitePlanOut]
    funcionalidades: list[FuncionalidadPlanOut]


class SuscripcionGestionIn(BaseModel):
    empresa_id: int
    plan_id: int
    fecha_inicio: date = Field(default_factory=date.today)
    vigencia_meses: int = Field(default=1, ge=1, le=120)
    estado: str = EstadoSuscripcion.ACTIVA
    observacion: str | None = Field(default=None, max_length=255)

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, value: str) -> str:
        value = value.upper()
        if value not in EstadoSuscripcion.TODOS:
            raise ValueError("Estado de suscripción inválido")
        return value


class SuscripcionOut(BaseModel):
    id: int
    empresa_id: int
    empresa_nombre: str
    plan_id: int
    plan_nombre: str
    fecha_inicio: date
    fecha_vencimiento: date
    estado: str
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class ConsumoOut(BaseModel):
    codigo: str
    etiqueta: str
    utilizado: int | None
    limite: int
    porcentaje: float | None
    nivel: str
    error: str | None = None


class PlanConsumoOut(BaseModel):
    empresa_id: int
    empresa_nombre: str
    plan: PlanOut
    suscripcion: SuscripcionOut
    dias_restantes: int
    funcionalidades: list[FuncionalidadPlanOut]
    consumos: list[ConsumoOut]


class CambioPlanIn(BaseModel):
    empresa_id: int | None = None
    plan_id: int
    vigencia_meses: int = Field(default=1, ge=1, le=120)
    observacion: str | None = Field(default=None, max_length=255)


class IncompatibilidadPlanOut(BaseModel):
    codigo: str
    etiqueta: str
    utilizado: int | None
    limite: int
    mensaje: str


class CambioPlanPreviewOut(BaseModel):
    empresa_id: int
    suscripcion_id: int
    plan_actual: PlanOut
    plan_nuevo: PlanOut
    tipo_cambio: str
    fecha_inicio_nueva: date
    fecha_vencimiento_nueva: date
    compatible: bool
    incompatibilidades: list[IncompatibilidadPlanOut]


class CambioPlanOut(BaseModel):
    suscripcion: SuscripcionOut
    tipo_cambio: str
    plan_anterior_id: int
    plan_anterior_nombre: str
    plan_nuevo_id: int
    plan_nuevo_nombre: str
    fecha_inicio_nueva: date
    fecha_vencimiento_nueva: date
    idempotente: bool = False


class HistorialCambioPlanOut(BaseModel):
    id: int
    suscripcion_id: int
    plan_anterior_id: int | None
    plan_anterior_nombre: str | None
    plan_nuevo_id: int
    plan_nuevo_nombre: str
    usuario_id: int
    tipo_cambio: str
    observacion: str | None
    fecha_inicio_nueva: date | None
    fecha_vencimiento_nueva: date | None
    fecha_cambio: datetime
