from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import SessionDep, require_roles
from app.modules.identidad.models import RolNombre, Usuario

from .schemas import DatosOfflineOut
from .service import preparar_datos

router = APIRouter(prefix="/offline", tags=["offline"])

OfflineUser = Annotated[
    Usuario,
    Depends(
        require_roles(
            RolNombre.CLIENTE,
            RolNombre.ADMINISTRADOR,
            RolNombre.ENCARGADO,
            RolNombre.CAJERO,
        )
    ),
]


@router.get("/preparar-datos", response_model=DatosOfflineOut)
def preparar_datos_offline(
    session: SessionDep,
    usuario: OfflineUser,
    sucursal_id: int | None = Query(default=None),
):
    return preparar_datos(session, usuario, sucursal_id)
