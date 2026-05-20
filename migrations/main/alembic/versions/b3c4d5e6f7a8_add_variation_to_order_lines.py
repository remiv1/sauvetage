"""add_variation_to_order_lines

Revision ID: b3c4d5e6f7a8
Revises: 055e2cae2b21
Create Date: 2026-05-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = '055e2cae2b21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ajout de la colonne object_variation_id sur order_lines."""
    op.add_column(
        'order_lines',
        sa.Column(
            'object_variation_id',
            sa.Integer(),
            nullable=True,
            comment="Variation de produit sélectionnée pour cette ligne (FK object_variations)",
        ),
        schema='app_schema',
    )
    op.create_foreign_key(
        'order_lines_object_variation_id_fkey',
        'order_lines',
        'object_variations',
        ['object_variation_id'],
        ['id'],
        source_schema='app_schema',
        referent_schema='app_schema',
    )


def downgrade() -> None:
    """Suppression de la colonne object_variation_id sur order_lines."""
    op.drop_constraint(
        'order_lines_object_variation_id_fkey',
        'order_lines',
        schema='app_schema',
        type_='foreignkey',
    )
    op.drop_column('order_lines', 'object_variation_id', schema='app_schema')
