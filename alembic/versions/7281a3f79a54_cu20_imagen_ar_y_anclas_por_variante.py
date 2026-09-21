"""cu20 imagen ar y anclas por variante

Revision ID: 7281a3f79a54
Revises: f903284f7fd6
Create Date: 2026-09-20 23:55:57.282629

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '7281a3f79a54'
down_revision: Union[str, Sequence[str], None] = 'f903284f7fd6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('producto_variante', sa.Column('imagen_ar_url', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True))
    op.add_column('producto_variante', sa.Column('ancla_izq_x', sa.Numeric(precision=6, scale=4), nullable=True))
    op.add_column('producto_variante', sa.Column('ancla_izq_y', sa.Numeric(precision=6, scale=4), nullable=True))
    op.add_column('producto_variante', sa.Column('ancla_der_x', sa.Numeric(precision=6, scale=4), nullable=True))
    op.add_column('producto_variante', sa.Column('ancla_der_y', sa.Numeric(precision=6, scale=4), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('producto_variante', 'ancla_der_y')
    op.drop_column('producto_variante', 'ancla_der_x')
    op.drop_column('producto_variante', 'ancla_izq_y')
    op.drop_column('producto_variante', 'ancla_izq_x')
    op.drop_column('producto_variante', 'imagen_ar_url')
