"""add_discount

Revision ID: d5c197e3ea75
Revises: 839badf54ef3
Create Date: 2026-04-03 11:47:59.767828

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5c197e3ea75'
down_revision: Union[str, Sequence[str], None] = '839badf54ef3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(  # pylint: disable=no-member
        'order_lines',
        sa.Column(
            'discount',
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default='0',
            comment='Remise en pourcentage'
        ),
        schema='app_schema',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('order_lines', 'discount', schema='app_schema')  # pylint: disable=no-member
    # ### end Alembic commands ###
