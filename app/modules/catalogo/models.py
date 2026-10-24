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
    __table_args__ = (
        UniqueConstraint("empresa_id", "nombre", name="uq_categoria_empresa_nombre"),
    )

    id: int | None = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    nombre: str = Field(max_length=80, index=True)
    descripcion: str | None = Field(default=None, max_length=300)
    activo: bool = Field(default=True)


class Talla(SQLModel, table=True):
    __tablename__ = "talla"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id", "valor", "tipo", name="uq_talla_empresa_valor_tipo"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    valor: str = Field(max_length=10)          # S, M, L, 42, ...
    tipo: str = Field(max_length=20)           # Ropa / Calzado / Otro
    activo: bool = Field(default=True)


class Color(SQLModel, table=True):
    __tablename__ = "color"
    __table_args__ = (
        UniqueConstraint("empresa_id", "nombre", name="uq_color_empresa_nombre"),
    )

    id: int | None = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    nombre: str = Field(max_length=40, index=True)
    codigo_hex: str | None = Field(default=None, max_length=7)  # #RRGGBB
    activo: bool = Field(default=True)


class Temporada(SQLModel, table=True):
    __tablename__ = "temporada"
    __table_args__ = (
        UniqueConstraint("empresa_id", "nombre", name="uq_temporada_empresa_nombre"),
    )

    id: int | None = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    nombre: str = Field(max_length=60, index=True)
    fecha_inicio: date | None = Field(default=None)
    fecha_fin: date | None = Field(default=None)
    activo: bool = Field(default=True)


class Coleccion(SQLModel, table=True):
    __tablename__ = "coleccion"

    id: int | None = Field(default=None, primary_key=True)
    empresa_id: int = Field(foreign_key="empresa.id", index=True)
    nombre: str = Field(max_length=80, index=True)
    descripcion: str | None = Field(default=None, max_length=300)
    temporada_id: int = Field(foreign_key="temporada.id")
    activo: bool = Field(default=True)
