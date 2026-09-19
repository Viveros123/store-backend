"""Esquemas del módulo IA — CU29 (recomendador), CU30 (chatbot),
CU32 (reporte por comando de voz)."""

from decimal import Decimal

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
#  CU29 — Recibir Recomendaciones de Productos
# --------------------------------------------------------------------------- #
class ProductoRecomendadoOut(BaseModel):
    id: int
    nombre: str
    categoria: str | None
    temporada: str | None
    precio_base: Decimal
    precio_promocional: Decimal | None = None
    imagen_url: str | None
    motivo: str


class RecomendacionesOut(BaseModel):
    items: list[ProductoRecomendadoOut]


# --------------------------------------------------------------------------- #
#  CU30 — Consultar Asistente Virtual (Chatbot)
# --------------------------------------------------------------------------- #
class MensajeChat(BaseModel):
    rol: str  # "cliente" | "asistente"
    texto: str


class ChatIn(BaseModel):
    mensaje: str = Field(min_length=1, max_length=500)
    historial: list[MensajeChat] = Field(default_factory=list, max_length=20)


class ProductoMencionadoOut(BaseModel):
    id: int
    nombre: str
    precio_base: Decimal
    precio_promocional: Decimal | None = None
    imagen_url: str | None


class ChatOut(BaseModel):
    respuesta: str
    productos: list[ProductoMencionadoOut] = []
    carrito_actualizado: bool = False


# --------------------------------------------------------------------------- #
#  CU32 — Generar Reporte por Comando de Voz
# --------------------------------------------------------------------------- #
class ReporteVozIn(BaseModel):
    texto: str = Field(
        min_length=1, max_length=300, description="Transcripción del comando de voz"
    )


class ReporteVozOut(BaseModel):
    consulta: str
    reporte: str
