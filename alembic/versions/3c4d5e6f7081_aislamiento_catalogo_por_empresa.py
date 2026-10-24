"""Aislamiento por empresa del catálogo heredado.

Revision ID: 3c4d5e6f7081
Revises: 2b3c4d5e6f70
Create Date: 2026-10-24

Los registros del primer parcial se conservan y se asignan a FashionStore
Principal antes de volver obligatoria la empresa.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3c4d5e6f7081"
down_revision: Union[str, Sequence[str], None] = "2b3c4d5e6f70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLAS = (
    "categoria",
    "talla",
    "color",
    "temporada",
    "coleccion",
    "proveedor",
    "producto",
    "producto_variante",
    "promocion",
)


def upgrade() -> None:
    for tabla in _TABLAS:
        op.add_column(tabla, sa.Column("empresa_id", sa.Integer(), nullable=True))
        op.create_index(f"ix_{tabla}_empresa_id", tabla, ["empresa_id"], unique=False)
        op.create_foreign_key(
            f"fk_{tabla}_empresa_id", tabla, "empresa", ["empresa_id"], ["id"]
        )
        op.execute(
            f"UPDATE {tabla} SET empresa_id = "
            "(SELECT id FROM empresa WHERE identificador = 'fashionstore-principal')"
        )
        op.alter_column(tabla, "empresa_id", existing_type=sa.Integer(), nullable=False)

    # Las claves naturales pasan a ser únicas dentro de cada empresa.
    op.drop_index("ix_categoria_nombre", table_name="categoria")
    op.create_index("ix_categoria_nombre", "categoria", ["nombre"], unique=False)
    op.create_unique_constraint(
        "uq_categoria_empresa_nombre", "categoria", ["empresa_id", "nombre"]
    )

    op.drop_constraint("uq_talla_valor_tipo", "talla", type_="unique")
    op.create_unique_constraint(
        "uq_talla_empresa_valor_tipo",
        "talla",
        ["empresa_id", "valor", "tipo"],
    )

    op.drop_index("ix_color_nombre", table_name="color")
    op.create_index("ix_color_nombre", "color", ["nombre"], unique=False)
    op.create_unique_constraint(
        "uq_color_empresa_nombre", "color", ["empresa_id", "nombre"]
    )

    op.drop_index("ix_temporada_nombre", table_name="temporada")
    op.create_index("ix_temporada_nombre", "temporada", ["nombre"], unique=False)
    op.create_unique_constraint(
        "uq_temporada_empresa_nombre", "temporada", ["empresa_id", "nombre"]
    )

    op.drop_index("ix_producto_variante_sku", table_name="producto_variante")
    op.create_index(
        "ix_producto_variante_sku", "producto_variante", ["sku"], unique=False
    )
    op.create_unique_constraint(
        "uq_variante_empresa_sku",
        "producto_variante",
        ["empresa_id", "sku"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_variante_empresa_sku", "producto_variante", type_="unique"
    )
    op.drop_index("ix_producto_variante_sku", table_name="producto_variante")
    op.create_index(
        "ix_producto_variante_sku", "producto_variante", ["sku"], unique=True
    )

    op.drop_constraint(
        "uq_temporada_empresa_nombre", "temporada", type_="unique"
    )
    op.drop_index("ix_temporada_nombre", table_name="temporada")
    op.create_index("ix_temporada_nombre", "temporada", ["nombre"], unique=True)

    op.drop_constraint("uq_color_empresa_nombre", "color", type_="unique")
    op.drop_index("ix_color_nombre", table_name="color")
    op.create_index("ix_color_nombre", "color", ["nombre"], unique=True)

    op.drop_constraint("uq_talla_empresa_valor_tipo", "talla", type_="unique")
    op.create_unique_constraint(
        "uq_talla_valor_tipo", "talla", ["valor", "tipo"]
    )

    op.drop_constraint("uq_categoria_empresa_nombre", "categoria", type_="unique")
    op.drop_index("ix_categoria_nombre", table_name="categoria")
    op.create_index("ix_categoria_nombre", "categoria", ["nombre"], unique=True)

    for tabla in reversed(_TABLAS):
        op.drop_constraint(f"fk_{tabla}_empresa_id", tabla, type_="foreignkey")
        op.drop_index(f"ix_{tabla}_empresa_id", table_name=tabla)
        op.drop_column(tabla, "empresa_id")
