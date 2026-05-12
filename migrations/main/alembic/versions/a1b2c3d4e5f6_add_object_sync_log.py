"""add object_sync_logs table

Revision ID: a1b2c3d4e5f6
Revises: 9d6b456d2f1b
Create Date: 2026-05-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9d6b456d2f1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'object_sync_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            'entity_type',
            sa.String(length=50),
            nullable=False,
            comment="Type d'entité : object, tag, picture, vat_rate",
        ),
        sa.Column(
            'entity_id',
            sa.Integer(),
            nullable=True,
            comment='ID local de l\'entité dans la base de données',
        ),
        sa.Column(
            'wpwc_id',
            sa.Integer(),
            nullable=True,
            comment='ID de l\'entité dans WooCommerce',
        ),
        sa.Column(
            'operation',
            sa.String(length=20),
            nullable=False,
            comment='Opération : create, update, delete',
        ),
        sa.Column(
            'sync_status',
            sa.String(length=20),
            nullable=False,
            comment='Statut : success, error',
        ),
        sa.Column(
            'error_message',
            sa.String(),
            nullable=True,
            comment='Message d\'erreur en cas d\'échec',
        ),
        sa.Column(
            'synced_at',
            sa.DateTime(),
            nullable=False,
            comment='Date et heure de la synchronisation',
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='app_schema',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('object_sync_logs', schema='app_schema')
