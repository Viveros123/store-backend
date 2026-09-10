"""Modelos del módulo Catálogo: datos base de las prendas.

CU5 — Categorías, Tallas y Colores.
CU6 — Temporadas y Colecciones.
"""

from datetime import date

from sqlmodel import Field, SQLModel, UniqueConstraint


class TallaTipo:
    ROPA = "Ropa"
    CALZADO = "Calzado"
    OTRO = "Otro"
    TODOS = (ROPA, CALZADO, OTRO)


class Categoria(SQLModel, table=True):
    __tablename__ = "categoria"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=80, unique=True, index=True)
    descripcion: str | None = Field(default=None, max_length=300)
    activo: bool = Field(default=True)


class Talla(SQLModel, table=True):
    __tablename__ = "talla"
    __table_args__ = (UniqueConstraint("valor", "tipo", name="uq_talla_valor_tipo"),)

    id: int | None = Field(default=None, primary_key=True)
    valor: str = Field(max_length=10)          # S, M, L, 42, ...
    tipo: str = Field(max_length=20)           # Ropa / Calzado / Otro
    activo: bool = Field(default=True)


class Color(SQLModel, table=True):
    __tablename__ = "color"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=40, unique=True, index=True)
    codigo_hex: str | None = Field(default=None, max_length=7)  # #RRGGBB
    activo: bool = Field(default=True)


class Temporada(SQLModel, table=True):
    __tablename__ = "temporada"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=60, unique=True, index=True)
    fecha_inicio: date | None = Field(default=None)
    fecha_fin: date | None = Field(default=None)
    activo: bool = Field(default=True)


class Coleccion(SQLModel, table=True):
    __tablename__ = "coleccion"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=80, index=True)
    descripcion: str | None = Field(default=None, max_length=300)
    temporada_id: int = Field(foreign_key="temporada.id")
    activo: bool = Field(default=True)
