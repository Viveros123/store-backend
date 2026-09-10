"""Lógica de negocio del módulo Identidad."""

from fastapi import HTTPException, status
from sqlmodel import Session, func, or_, select

from app.core.security import hash_password, verify_password
from app.modules.identidad.models import Rol, RolNombre, Usuario
from app.modules.identidad.schemas import (
    CambioPasswordIn,
    ClienteRegistroIn,
    MiCuentaUpdate,
    UsuarioCreate,
    UsuarioOut,
    UsuarioUpdate,
)


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def get_rol_by_nombre(session: Session, nombre: str) -> Rol | None:
    return session.exec(select(Rol).where(Rol.nombre == nombre)).first()


def get_usuario_by_email(session: Session, email: str) -> Usuario | None:
    return session.exec(select(Usuario).where(Usuario.email == email)).first()


def to_usuario_out(session: Session, usuario: Usuario) -> UsuarioOut:
    rol = session.get(Rol, usuario.rol_id)
    return UsuarioOut(
        id=usuario.id,
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        email=usuario.email,
        telefono=usuario.telefono,
        rol_id=usuario.rol_id,
        rol=rol.nombre if rol else None,
        sucursal_id=usuario.sucursal_id,
        proveedor_id=usuario.proveedor_id,
        activo=usuario.activo,
        fecha_registro=usuario.fecha_registro,
    )


# --------------------------------------------------------------------------- #
#  Autenticación
# --------------------------------------------------------------------------- #
def registrar_cliente(session: Session, data: ClienteRegistroIn) -> Usuario:
    """CU1 — alta pública de un cliente."""
    if get_usuario_by_email(session, data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta registrada con ese email",
        )
    rol_cliente = session.exec(
        select(Rol).where(Rol.nombre == RolNombre.CLIENTE)
    ).first()
    if rol_cliente is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="El rol Cliente no está configurado (ejecutar el seed)",
        )

    usuario = Usuario(
        nombre=data.nombre,
        apellido=data.apellido,
        email=str(data.email),
        password_hash=hash_password(data.password),
        telefono=data.telefono,
        rol_id=rol_cliente.id,
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


def actualizar_mi_cuenta(
    session: Session, usuario: Usuario, data: MiCuentaUpdate
) -> Usuario:
    """CU2 — actualiza los datos propios del usuario."""
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(usuario, campo, valor)
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


def cambiar_password(
    session: Session, usuario: Usuario, data: CambioPasswordIn
) -> None:
    """CU2 — cambia la propia contraseña verificando la actual."""
    if not verify_password(data.password_actual, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta",
        )
    usuario.password_hash = hash_password(data.password_nueva)
    session.add(usuario)
    session.commit()


def authenticate(session: Session, email: str, password: str) -> Usuario:
    usuario = get_usuario_by_email(session, email)
    if not usuario or not verify_password(password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta está desactivada",
        )
    return usuario


# --------------------------------------------------------------------------- #
#  CU3 — Gestionar Usuarios y Roles
# --------------------------------------------------------------------------- #
def list_roles(session: Session) -> list[Rol]:
    return session.exec(select(Rol).order_by(Rol.nombre)).all()


def list_usuarios(
    session: Session,
    *,
    q: str | None = None,
    rol_id: int | None = None,
    activo: bool | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Usuario], int]:
    filtros = []
    if q:
        patron = f"%{q.strip().lower()}%"
        filtros.append(
            or_(
                func.lower(Usuario.nombre).like(patron),
                func.lower(Usuario.apellido).like(patron),
                func.lower(Usuario.email).like(patron),
            )
        )
    if rol_id is not None:
        filtros.append(Usuario.rol_id == rol_id)
    if activo is not None:
        filtros.append(Usuario.activo == activo)

    base = select(Usuario)
    for f in filtros:
        base = base.where(f)

    total = session.exec(
        select(func.count()).select_from(base.subquery())
    ).one()

    items = session.exec(
        base.order_by(Usuario.id).offset((page - 1) * size).limit(size)
    ).all()
    return items, total


def _validar_rol(session: Session, rol_id: int) -> None:
    if session.get(Rol, rol_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El rol {rol_id} no existe",
        )


def _validar_sucursal(session: Session, sucursal_id: int | None) -> None:
    if sucursal_id is None:
        return
    from app.modules.sucursales.models import Sucursal

    if session.get(Sucursal, sucursal_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La sucursal {sucursal_id} no existe",
        )


def _validar_proveedor(session: Session, proveedor_id: int | None) -> None:
    if proveedor_id is None:
        return
    from app.modules.proveedores.models import Proveedor

    if session.get(Proveedor, proveedor_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El proveedor {proveedor_id} no existe",
        )


def create_usuario(session: Session, data: UsuarioCreate) -> Usuario:
    if get_usuario_by_email(session, data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email",
        )
    _validar_rol(session, data.rol_id)
    _validar_sucursal(session, data.sucursal_id)
    _validar_proveedor(session, data.proveedor_id)

    usuario = Usuario(
        nombre=data.nombre,
        apellido=data.apellido,
        email=str(data.email),
        password_hash=hash_password(data.password),
        telefono=data.telefono,
        rol_id=data.rol_id,
        sucursal_id=data.sucursal_id,
        proveedor_id=data.proveedor_id,
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


def update_usuario(
    session: Session,
    usuario_id: int,
    data: UsuarioUpdate,
    *,
    actor_id: int,
) -> Usuario:
    usuario = session.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )

    cambios = data.model_dump(exclude_unset=True)

    # El admin no puede quitarse a sí mismo el acceso.
    if usuario_id == actor_id:
        if cambios.get("activo") is False:
            raise HTTPException(400, "No podés desactivar tu propia cuenta")
        if "rol_id" in cambios and cambios["rol_id"] != usuario.rol_id:
            raise HTTPException(400, "No podés cambiar tu propio rol")

    if "email" in cambios and cambios["email"]:
        otro = get_usuario_by_email(session, cambios["email"])
        if otro and otro.id != usuario_id:
            raise HTTPException(409, "Ya existe un usuario con ese email")
        usuario.email = str(cambios["email"])
    if "rol_id" in cambios and cambios["rol_id"] is not None:
        _validar_rol(session, cambios["rol_id"])
        usuario.rol_id = cambios["rol_id"]
    if "sucursal_id" in cambios:
        _validar_sucursal(session, cambios["sucursal_id"])
    if "proveedor_id" in cambios:
        _validar_proveedor(session, cambios["proveedor_id"])
    if "password" in cambios and cambios["password"]:
        usuario.password_hash = hash_password(cambios["password"])

    for campo in ("nombre", "apellido", "telefono", "sucursal_id", "proveedor_id", "activo"):
        if campo in cambios:
            setattr(usuario, campo, cambios[campo])

    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario
