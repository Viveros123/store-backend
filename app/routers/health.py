"""Endpoints de salud: sirven para saber si la API y la base están vivas."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlmodel import Session

from app.core.db import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """La API está levantada."""
    return {"status": "ok"}


@router.get("/health/db")
def health_db(session: Session = Depends(get_session)) -> dict:
    """La API puede hablar con la base de datos."""
    session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
