"""merge_heads_local

Revision ID: a8fd5b0eed0a
Revises: 124a562aab79, 3312b31d6cf2
Create Date: 2026-06-13 10:08:55.487261

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8fd5b0eed0a'
down_revision: Union[str, Sequence[str], None] = ('124a562aab79', '3312b31d6cf2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
