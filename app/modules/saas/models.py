"""Modelos persistentes del módulo SaaS (CU01-CU07 actuales)."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel, UniqueConstraint


class EstadoSuscripcion:
    ACTIVA = "ACTIVA"
    SUSPENDIDA = "SUSPENDIDA"
    VENCIDA = "VENCIDA"
    CANCELADA = "CANCELADA"

    TODOS = (ACTIVA, SUSPENDIDA, VENCIDA, CANCELADA)


class CodigoLimite:
    MAX_SUCURSALES = "MAX_SUCURSALES"
    MAX_USUARIOS = "MAX_USUARIOS"
    MAX_REPORTES_IA_MES = "MAX_REPORTES_IA_MES"


class CodigoFuncionalidad:
    PWA_OFFLINE = "PWA_OFFLINE"
    REPORTES_CONVENCIONALES = "REPORTES_CONVENCIONALES"
    REPORTES_IA = "REPORTES_IA"
    REPORTES_MULTISUCURSAL = "REPORTES_MULTISUCURSAL"


class Empresa(SQLModel, table=True):
    __tablename__ = "empresa"

    id: int | None = Field(default=None, primary_key=True)
    identificador: str = Field(max_length=50, unique=True, index=True)
    nombre: str = Field(max_length=120, index=True)
    razon_social: str | None = Field(default=None, max_length=150)
    activa: bool = Field(default=True, index=True)
    fecha_registro: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    fecha_actualizacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Plan(SQLModel, table=True):
    __tablename__ = "plan"

    id: int | None = Field(default=None, primary_key=True)
    codigo: str = Field(max_length=30, unique=True, index=True)
    nombre: str = Field(max_length=60)
    descripcion: str | None = Field(default=None, max_length=300)
    precio_mensual: Decimal = Field(max_digits=10, decimal_places=2, ge=0)
    activo: bool = Field(default=True, index=True)
    fecha_creacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class LimitePlan(SQLModel, table=True):
    __tablename__ = "limite_plan"
    __table_args__ = (
        UniqueConstraint("plan_id", "codigo", name="uq_limite_plan_codigo"),
    )

    id: int | None = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="plan.id", index=True)
    codigo: str = Field(max_length=50)
    valor_maximo: int = Field(ge=0)


class FuncionalidadPlan(SQLModel, table=True):
    __tablename__ = "funcionalidad_plan"
    __table_args__ = (
        UniqueConstraint(
            "plan_id", "codigo", name="uq_funcionalidad_plan_codigo"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="plan.id", index=True)
    codigo: str = Field(max_length=50)
    habilitada: bool = Field(default=True)


class Suscripcion(SQLModel, table=True):
    __tablename__ = "suscripcion"

    id: int | None = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    plan_id: int = Field(foreign_key="plan.id", index=True)
    fecha_inicio: date
    fecha_vencimiento: date
    estado: str = Field(default=EstadoSuscripcion.ACTIVA, max_length=20, index=True)
    fecha_creacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    fecha_actualizacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class HistorialCambioPlan(SQLModel, table=True):
    __tablename__ = "historial_cambio_plan"

    id: int | None = Field(default=None, primary_key=True)
    suscripcion_id: int = Field(foreign_key="suscripcion.id", index=True)
    plan_anterior_id: int | None = Field(default=None, foreign_key="plan.id")
    plan_nuevo_id: int = Field(foreign_key="plan.id")
    usuario_id: int = Field(foreign_key="usuario.id")
    tipo_cambio: str = Field(max_length=20)
    observacion: str | None = Field(default=None, max_length=255)
    # CU06: la clave evita repetir el cambio si el cliente reenvía la misma
    # solicitud. Es opcional para conservar el historial del primer parcial.
    clave_idempotencia: str | None = Field(
        default=None, max_length=80, unique=True, index=True
    )
    fecha_inicio_nueva: date | None = None
    fecha_vencimiento_nueva: date | None = None
    fecha_cambio: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
