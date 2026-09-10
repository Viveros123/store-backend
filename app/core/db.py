"""Motor de base de datos y sesión."""

from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import settings

engine = create_engine(
    settings.sqlalchemy_url,
    echo=False,          # True para ver el SQL generado durante el desarrollo
    pool_pre_ping=True,  # verifica la conexión antes de usarla (Neon serverless)
)


def get_session() -> Generator[Session, None, None]:
    """Dependencia para los endpoints: `session: Session = Depends(get_session)`."""
    with Session(engine) as session:
        yield session
