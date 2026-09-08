"""Motor de base de datos y dependencia de sesión para los endpoints."""

from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import settings

engine = create_engine(
    settings.sqlalchemy_url,
    echo=False,          # poner True para ver el SQL generado durante el desarrollo
    pool_pre_ping=True,  # verifica la conexión antes de usarla (útil con Neon serverless)
)


def get_session() -> Generator[Session, None, None]:
    """Se inyecta en los endpoints con Depends(get_session)."""
    with Session(engine) as session:
        yield session
