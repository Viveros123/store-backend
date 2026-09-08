"""Configuración de la aplicación, leída desde variables de entorno / archivo .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = "FashionStore API"

    # Base de datos
    database_url: str

    # Seguridad / JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    @property
    def sqlalchemy_url(self) -> str:
        """SQLAlchemy necesita el driver explícito. Neon entrega 'postgresql://',
        acá lo normalizamos a 'postgresql+psycopg://' (psycopg v3)."""
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


settings = Settings()
