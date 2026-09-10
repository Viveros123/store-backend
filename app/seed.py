"""Datos iniciales: roles del sistema y usuario administrador.

Idempotente: se puede correr varias veces sin duplicar.
Uso:  python -m app.seed
"""

from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.core.security import hash_password
from app.modules.identidad.models import Rol, RolNombre, Usuario


def seed_roles(session: Session) -> None:
    existentes = {r.nombre for r in session.exec(select(Rol)).all()}
    creados = 0
    for nombre in RolNombre.TODOS:
        if nombre not in existentes:
            session.add(Rol(nombre=nombre))
            creados += 1
    session.commit()
    print(f"Roles: {creados} creados, {len(existentes)} ya existían.")


def seed_admin(session: Session) -> None:
    admin_rol = session.exec(
        select(Rol).where(Rol.nombre == RolNombre.ADMINISTRADOR)
    ).first()
    if admin_rol is None:
        raise RuntimeError("Falta el rol Administrador; corré seed_roles primero.")

    ya_existe = session.exec(
        select(Usuario).where(Usuario.email == settings.first_admin_email)
    ).first()
    if ya_existe:
        print(f"Admin '{settings.first_admin_email}' ya existe.")
        return

    session.add(
        Usuario(
            nombre=settings.first_admin_nombre,
            apellido=settings.first_admin_apellido,
            email=settings.first_admin_email,
            password_hash=hash_password(settings.first_admin_password),
            rol_id=admin_rol.id,
        )
    )
    session.commit()
    print(f"Admin '{settings.first_admin_email}' creado.")


def main() -> None:
    with Session(engine) as session:
        seed_roles(session)
        seed_admin(session)


if __name__ == "__main__":
    main()
