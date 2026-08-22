"""Ajoute le lien entre une commande et son retour.

Revision ID: a412c8d947e3
Revises: 9d9f9187d96f
Create Date: 2026-08-22 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a412c8d947e3"
down_revision: Union[str, Sequence[str], None] = "9d9f9187d96f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ajoute le lien unique de la commande de retour vers sa commande d'origine."""
    op.add_column(
        "orders",
        sa.Column("return_of_order_id", sa.Integer(), nullable=True),
        schema="app_schema",
    )
    op.create_foreign_key(
        "orders_return_of_order_id_fkey",
        "orders",
        "orders",
        ["return_of_order_id"],
        ["id"],
        source_schema="app_schema",
        referent_schema="app_schema",
    )
    op.create_unique_constraint(
        "orders_return_of_order_id_key",
        "orders",
        ["return_of_order_id"],
        schema="app_schema",
    )


def downgrade() -> None:
    """Supprime le lien entre les commandes de retour et leur commande d'origine."""
    op.drop_constraint(
        "orders_return_of_order_id_key",
        "orders",
        schema="app_schema",
        type_="unique",
    )
    op.drop_constraint(
        "orders_return_of_order_id_fkey",
        "orders",
        schema="app_schema",
        type_="foreignkey",
    )
    op.drop_column("orders", "return_of_order_id", schema="app_schema")