"""Ajout de la colonne wpwc_slug sur app_schema.vat_rates

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-05-20

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c4d5e6f7a8b9"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vat_rates",
        sa.Column(
            "wpwc_slug",
            sa.String(),
            nullable=True,
            comment="Slug de la classe de taxe WooCommerce (ex: 'standard', 'taux-reduit')",
        ),
        schema="app_schema",
    )


def downgrade() -> None:
    op.drop_column("vat_rates", "wpwc_slug", schema="app_schema")
