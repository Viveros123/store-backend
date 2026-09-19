"""Modelos del módulo IA — historial del chatbot (CU30) y reportes
generados (CU31/CU32)."""

from datetime import datetime, timezone

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class TipoInteraccion:
    CHATBOT = "CHATBOT"


class TipoReporte:
    GENERAL = "GENERAL"  # ventas + stock (reporte por voz, CU32)
    VENTAS = "VENTAS"
    INVENTARIO = "INVENTARIO"


class FormatoSolicitud:
    VOZ = "VOZ"  # CU32
    FORMULARIO = "FORMULARIO"  # CU31


class HistorialInteraccion(SQLModel, table=True):
    __tablename__ = "historial_interaccion"

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="usuario.id", index=True)
    tipo: str = Field(default=TipoInteraccion.CHATBOT, max_length=30)
    # Primer producto que el asistente mencionó en su respuesta (si hubo).
    producto_id: int | None = Field(default=None, foreign_key="producto.id")
    consulta: str
    respuesta: str
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReporteGenerado(SQLModel, table=True):
    __tablename__ = "reporte_generado"

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    tipo_reporte: str = Field(max_length=30)
    # Filtros con los que se armó el reporte (fechas, sucursal, umbral, etc.).
    parametros: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    formato_solicitud: str = Field(max_length=10)
    fecha_generacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
