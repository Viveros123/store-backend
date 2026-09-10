"""Punto de entrada de la API de FashionStore."""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.deps import SessionDep

app = FastAPI(title=settings.project_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["root"])
def root() -> dict:
    return {"message": settings.project_name, "docs": "/docs"}


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def health_db(session: SessionDep) -> dict:
    session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


# --- Routers por módulo (se agregan a medida que avanzan los casos de uso) ---
from app.modules.identidad.router import router as identidad_router  # noqa: E402
from app.modules.proveedores.router import router as proveedores_router  # noqa: E402
from app.modules.sucursales.router import router as sucursales_router  # noqa: E402

app.include_router(identidad_router)
app.include_router(sucursales_router)
app.include_router(proveedores_router)
