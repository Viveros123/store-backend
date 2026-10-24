"""Endpoints SaaS para CU01-CU07 actuales."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.core.deps import SessionDep, require_roles
from app.modules.identidad.models import RolNombre, Usuario
from app.modules.saas import service
from app.modules.saas.models import Plan
from app.modules.saas.schemas import (
    CambioPlanIn,
    CambioPlanOut,
    CambioPlanPreviewOut,
    EmpresaCreate,
    EmpresaOut,
    EmpresaPage,
    EmpresaUpdate,
    HistorialCambioPlanOut,
    PlanConsumoOut,
    PlanOut,
    PlanUpdate,
    SuscripcionGestionIn,
    SuscripcionOut,
)

router = APIRouter(tags=["saas"])

SuperAdmin = Annotated[
    Usuario, Depends(require_roles(RolNombre.SUPERADMINISTRADOR))
]
AdminConsulta = Annotated[
    Usuario,
    Depends(
        require_roles(
            RolNombre.ADMINISTRADOR,
            allow_inactive_empresa=True,
        )
    ),
]
PlanActor = Annotated[
    Usuario, Depends(require_roles(RolNombre.ADMINISTRADOR))
]


def _empresa_objetivo(actor: Usuario, empresa_id: int | None) -> int:
    if actor.empresa_id is None:
        if empresa_id is None:
            raise HTTPException(422, "Debe indicar la empresa")
        return empresa_id
    if empresa_id is not None and empresa_id != actor.empresa_id:
        raise HTTPException(403, "No puede operar sobre otra empresa")
    return actor.empresa_id


@router.get("/empresas", response_model=EmpresaPage)
def listar_empresas(
    session: SessionDep,
    _: SuperAdmin,
    q: str | None = Query(default=None),
    activa: bool | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    items, total = service.list_empresas(
        session, q=q, activa=activa, page=page, size=size
    )
    return EmpresaPage(
        items=[service.to_empresa_out(session, item) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "/empresas", response_model=EmpresaOut, status_code=status.HTTP_201_CREATED
)
def registrar_empresa(data: EmpresaCreate, session: SessionDep, actor: SuperAdmin):
    empresa = service.create_empresa(session, data, actor_id=actor.id)
    return service.to_empresa_out(session, empresa)


@router.get("/empresas/{empresa_id}", response_model=EmpresaOut)
def obtener_empresa(empresa_id: int, session: SessionDep, _: SuperAdmin):
    return service.to_empresa_out(session, service.empresa_or_404(session, empresa_id))


@router.patch("/empresas/{empresa_id}", response_model=EmpresaOut)
def actualizar_empresa(
    empresa_id: int, data: EmpresaUpdate, session: SessionDep, _: SuperAdmin
):
    empresa = service.update_empresa(session, empresa_id, data)
    return service.to_empresa_out(session, empresa)


@router.get("/planes", response_model=list[PlanOut])
def listar_planes(
    session: SessionDep, actor: PlanActor, solo_activos: bool = False
):
    if actor.empresa_id is not None:
        solo_activos = True
    return [
        service.to_plan_out(session, plan)
        for plan in service.list_planes(session, solo_activos=solo_activos)
    ]


@router.get("/planes/{plan_id}", response_model=PlanOut)
def obtener_plan(plan_id: int, session: SessionDep, _: SuperAdmin):
    plan = session.get(Plan, plan_id)
    if plan is None:
        from fastapi import HTTPException

        raise HTTPException(404, "Plan no encontrado")
    return service.to_plan_out(session, plan)


@router.put("/planes/{plan_id}", response_model=PlanOut)
def actualizar_plan(
    plan_id: int, data: PlanUpdate, session: SessionDep, _: SuperAdmin
):
    return service.to_plan_out(session, service.update_plan(session, plan_id, data))


@router.get("/suscripciones", response_model=list[SuscripcionOut])
def listar_suscripciones(
    session: SessionDep, _: SuperAdmin, q: str | None = Query(default=None)
):
    return [
        service.to_suscripcion_out(session, item)
        for item in service.list_suscripciones(session, q=q)
    ]


@router.post("/suscripciones", response_model=SuscripcionOut)
def gestionar_suscripcion(
    data: SuscripcionGestionIn, session: SessionDep, actor: SuperAdmin
):
    item = service.gestionar_suscripcion(session, data, actor_id=actor.id)
    return service.to_suscripcion_out(session, item)


@router.get("/suscripciones/mi-plan", response_model=PlanConsumoOut)
def mi_plan_y_consumo(session: SessionDep, admin: AdminConsulta):
    if admin.empresa_id is None:
        from fastapi import HTTPException

        raise HTTPException(403, "El usuario no está asociado a una empresa")
    return service.get_plan_consumo(session, admin.empresa_id)


@router.post(
    "/suscripciones/validar-cambio", response_model=CambioPlanPreviewOut
)
def validar_cambio_plan(
    data: CambioPlanIn, session: SessionDep, actor: PlanActor
):
    empresa_id = _empresa_objetivo(actor, data.empresa_id)
    return service.preview_cambio_plan(session, empresa_id, data)


@router.put("/suscripciones/cambiar-plan", response_model=CambioPlanOut)
def cambiar_o_renovar_plan(
    data: CambioPlanIn,
    session: SessionDep,
    actor: PlanActor,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=80,
            description="Identificador único del intento de cambio o renovación",
        ),
    ],
):
    empresa_id = _empresa_objetivo(actor, data.empresa_id)
    return service.cambiar_o_renovar_plan(
        session,
        empresa_id,
        data,
        actor_id=actor.id,
        clave_idempotencia=idempotency_key,
    )


@router.get(
    "/suscripciones/historial", response_model=list[HistorialCambioPlanOut]
)
def historial_cambios(
    session: SessionDep,
    actor: PlanActor,
    empresa_id: int | None = Query(default=None),
):
    return service.historial_cambios_plan(
        session, _empresa_objetivo(actor, empresa_id)
    )
