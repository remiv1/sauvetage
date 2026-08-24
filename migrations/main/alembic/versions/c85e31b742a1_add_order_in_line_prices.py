"""Ajoute les composantes financières des lignes fournisseur.

Revision ID: c85e31b742a1
Revises: b91f6d48aa32
Create Date: 2026-08-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c85e31b742a1"
down_revision: Union[str, Sequence[str], None] = "b91f6d48aa32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remplace les colonnes financières par une table de composantes."""
    op.create_table(
        "order_in_line_prices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "order_in_line_id",
            sa.Integer(),
            nullable=False,
            comment="ID de la ligne physique de commande fournisseur",
        ),
        sa.Column(
            "unit_price",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Composante du prix d'achat unitaire HT en euros",
        ),
        sa.Column(
            "vat_rate",
            sa.Numeric(precision=10, scale=3),
            nullable=False,
            comment="Taux de TVA historique de la composante",
        ),
        sa.Column(
            "position",
            sa.Integer(),
            nullable=False,
            comment="Ordre d'affichage de la composante",
        ),
        sa.ForeignKeyConstraint(
            ["order_in_line_id"],
            ["app_schema.order_in_lines.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "order_in_line_id",
            "position",
            name="uq_order_in_line_prices_line_position",
        ),
        schema="app_schema",
    )
    op.drop_column("order_in_lines", "vat_rate", schema="app_schema")
    op.drop_column("order_in_lines", "unit_price", schema="app_schema")


def downgrade() -> None:
    """Rétablit le format financier historique à composante unique."""
    op.add_column(
        "order_in_lines",
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=True),
        schema="app_schema",
    )
    op.add_column(
        "order_in_lines",
        sa.Column("vat_rate", sa.Numeric(10, 3), nullable=True),
        schema="app_schema",
    )
    op.execute(
        """
        UPDATE app_schema.order_in_lines AS line
        SET unit_price = price.unit_price,
            vat_rate = price.vat_rate
        FROM app_schema.order_in_line_prices AS price
        WHERE price.order_in_line_id = line.id
          AND price.position = 0
        """
    )
    op.execute(
        """
        UPDATE app_schema.order_in_lines
        SET unit_price = COALESCE(unit_price, 0),
            vat_rate = COALESCE(vat_rate, 0)
        """
    )
    op.alter_column(
        "order_in_lines", "unit_price", nullable=False, schema="app_schema"
    )
    op.alter_column(
        "order_in_lines", "vat_rate", nullable=False, schema="app_schema"
    )
    op.drop_table("order_in_line_prices", schema="app_schema")