"""Rattache les lignes de commande à leur taux de TVA.

Revision ID: b91f6d48aa32
Revises: a412c8d947e3
Create Date: 2026-08-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b91f6d48aa32"
down_revision: Union[str, Sequence[str], None] = "a412c8d947e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ajoute et renseigne le taux de TVA appliqué à chaque ligne de commande."""
    op.add_column(
        "order_lines",
        sa.Column("vat_rate_id", sa.Integer(), nullable=True),
        schema="app_schema",
    )
    op.execute(
        sa.text(
            """
            UPDATE app_schema.order_lines AS order_line
            SET vat_rate_id = vat_rate.id
            FROM app_schema.vat_rates AS vat_rate
            WHERE vat_rate.rate = order_line.vat_rate
              AND vat_rate.date_start <= CURRENT_TIMESTAMP
              AND (vat_rate.date_end IS NULL OR vat_rate.date_end > CURRENT_TIMESTAMP)
            """
        )
    )
    missing_count = op.get_bind().execute(
        sa.text(
            "SELECT count(*) FROM app_schema.order_lines WHERE vat_rate_id IS NULL"
        )
    ).scalar_one()
    if missing_count:
        raise RuntimeError(
            f"{missing_count} ligne(s) de commande n'ont aucun taux de TVA actif correspondant."
        )
    op.alter_column("order_lines", "vat_rate_id", nullable=False, schema="app_schema")
    op.create_foreign_key(
        "order_lines_vat_rate_id_fkey",
        "order_lines",
        "vat_rates",
        ["vat_rate_id"],
        ["id"],
        source_schema="app_schema",
        referent_schema="app_schema",
    )


def downgrade() -> None:
    """Supprime le rattachement de TVA des lignes de commande."""
    op.drop_constraint(
        "order_lines_vat_rate_id_fkey",
        "order_lines",
        schema="app_schema",
        type_="foreignkey",
    )
    op.drop_column("order_lines", "vat_rate_id", schema="app_schema")