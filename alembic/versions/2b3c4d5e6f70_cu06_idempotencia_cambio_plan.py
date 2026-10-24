"""CU06: idempotencia y vigencia del historial de cambios de plan.

Revision ID: 2b3c4d5e6f70
Revises: 1a2b3c4d5e6f
Create Date: 2026-10-23

Las columnas son opcionales para conservar íntegros los registros anteriores.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "2b3c4d5e6f70"
down_revision: Union[str, Sequence[str], None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "historial_cambio_plan",
        sa.Column(
            "clave_idempotencia",
            sqlmodel.sql.sqltypes.AutoString(80),
            nullable=True,
        ),
    )
    op.add_column(
        "historial_cambio_plan",
        sa.Column("fecha_inicio_nueva", sa.Date(), nullable=True),
    )
    op.add_column(
        "historial_cambio_plan",
        sa.Column("fecha_vencimiento_nueva", sa.Date(), nullable=True),
    )
    op.create_index(
        "ix_historial_cambio_plan_clave_idempotencia",
        "historial_cambio_plan",
        ["clave_idempotencia"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_historial_cambio_plan_clave_idempotencia",
        table_name="historial_cambio_plan",
    )
    op.drop_column("historial_cambio_plan", "fecha_vencimiento_nueva")
    op.drop_column("historial_cambio_plan", "fecha_inicio_nueva")
    op.drop_column("historial_cambio_plan", "clave_idempotencia")
