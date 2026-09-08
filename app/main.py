"""Punto de entrada de la API de FashionStore."""

from fastapi import FastAPI

from app.core.config import settings
from app.routers import health

app = FastAPI(title=settings.project_name)

app.include_router(health.router)


@app.get("/", tags=["root"])
def root() -> dict:
    return {"message": settings.project_name, "docs": "/docs"}
