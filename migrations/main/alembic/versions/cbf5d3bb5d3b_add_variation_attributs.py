"""Ajoute l'attribut porté par les variations d'un produit.

Revision ID: cbf5d3bb5d3b
Revises: c85e31b742a1
Create Date: 2026-08-24 15:14:09.013223
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "cbf5d3bb5d3b"
down_revision: Union[str, Sequence[str], None] = "c85e31b742a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ajoute le nom de l'attribut de variation au produit parent."""
    op.add_column(
        "general_objects",
        sa.Column(
            "object_variation_attribut",
            sa.String(),
            nullable=True,
            comment="Nom de l'attribut porté par les variations WooCommerce",
        ),
    )


def downgrade() -> None:
    """Supprime le nom de l'attribut de variation du produit parent."""
    op.drop_column("general_objects", "object_variation_attribut")