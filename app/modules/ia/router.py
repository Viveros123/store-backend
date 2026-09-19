"""Endpoints del módulo IA — CU29 (recomendador), CU30 (chatbot),
CU32 (reporte por comando de voz)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import SessionDep, require_roles
from app.modules.ia import service
from app.modules.ia.schemas import (
    ChatIn,
    ChatOut,
    RecomendacionesOut,
    ReporteVozIn,
    ReporteVozOut,
)
from app.modules.identidad.models import RolNombre, Usuario

router = APIRouter(prefix="/ia", tags=["ia"])

ClienteUser = Annotated[Usuario, Depends(require_roles(RolNombre.CLIENTE))]
AdminUser = Annotated[Usuario, Depends(require_roles(RolNombre.ADMINISTRADOR))]


@router.get("/recomendaciones", response_model=RecomendacionesOut)
def recomendaciones(session: SessionDep, user: ClienteUser):  # CU29
    items = service.recomendar_productos(session, user.id)
    return RecomendacionesOut(items=items)


@router.post("/chat", response_model=ChatOut)
def chat(data: ChatIn, session: SessionDep, user: ClienteUser):  # CU30
    resultado = service.chat_asistente(
        session, user.id, data.mensaje, [h.model_dump() for h in data.historial]
    )
    return ChatOut(**resultado)


@router.post("/reportes/voz", response_model=ReporteVozOut)
def reporte_por_voz(data: ReporteVozIn, session: SessionDep, user: AdminUser):  # CU32
    reporte = service.generar_reporte_voz(session, user.id, data.texto)
    return ReporteVozOut(consulta=data.texto, reporte=reporte)
