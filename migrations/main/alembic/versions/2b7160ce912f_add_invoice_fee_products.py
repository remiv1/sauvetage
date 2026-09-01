"""Ajoute les produits de frais de facturation.

Revision ID: 2b7160ce912f
Revises: 0412b4a7f5c4
Create Date: 2026-09-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2b7160ce912f"
down_revision: Union[str, Sequence[str], None] = "0412b4a7f5c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crée les produits de frais et rattache les lignes de port existantes."""
    op.create_table(
        "invoice_fee_products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fee_type", sa.String(length=50), nullable=False),
        sa.Column("vat_rate_id", sa.Integer(), nullable=False),
        sa.Column("henrri_id", sa.Integer(), nullable=True),
        sa.Column("reference", sa.String(length=14), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["vat_rate_id"],
            ["app_schema.vat_rates.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("henrri_id"),
        sa.UniqueConstraint("reference"),
        sa.UniqueConstraint(
            "fee_type",
            "vat_rate_id",
            name="uq_invoice_fee_products_type_vat_rate",
        ),
        schema="app_schema",
    )
    op.add_column(
        "order_lines",
        sa.Column(
            "invoice_fee_product_id",
            sa.Integer(),
            nullable=True,
            comment="Produit de frais associé à la ligne de commande",
        ),
        schema="app_schema",
    )
    op.create_foreign_key(
        "fk_order_lines_invoice_fee_product_id",
        "order_lines",
        "invoice_fee_products",
        ["invoice_fee_product_id"],
        ["id"],
        source_schema="app_schema",
        referent_schema="app_schema",
    )

    op.execute(
        """
        INSERT INTO app_schema.invoice_fee_products (
            fee_type,
            vat_rate_id,
            reference,
            description,
            created_at,
            updated_at
        )
        SELECT DISTINCT
            'shipping',
            order_line.vat_rate_id,
            'PORT-' || order_line.vat_rate_id,
            'Frais de port (TVA ' || vat_rate.rate || ' %)',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM app_schema.order_lines AS order_line
        JOIN app_schema.vat_rates AS vat_rate ON vat_rate.id = order_line.vat_rate_id
        WHERE order_line.is_shipping_fee
        """
    )
    op.execute(
        """
        UPDATE app_schema.order_lines AS order_line
        SET invoice_fee_product_id = fee_product.id
        FROM app_schema.invoice_fee_products AS fee_product
        WHERE order_line.is_shipping_fee
          AND fee_product.fee_type = 'shipping'
          AND fee_product.vat_rate_id = order_line.vat_rate_id
        """
    )

    op.execute(
        "ALTER TABLE app_schema.order_lines DROP CONSTRAINT IF EXISTS "
        "check_shipping_fee_or_general_object_id_not_null"
    )
    op.create_check_constraint(
        "check_order_line_product_source",
        "order_lines",
        "(NOT is_shipping_fee AND general_object_id IS NOT NULL "
        "AND invoice_fee_product_id IS NULL) OR "
        "(is_shipping_fee AND general_object_id IS NULL "
        "AND invoice_fee_product_id IS NOT NULL)",
        schema="app_schema",
    )


def downgrade() -> None:
    """Supprime les produits de frais de facturation."""
    op.drop_constraint(
        "check_order_line_product_source",
        "order_lines",
        schema="app_schema",
        type_="check",
    )
    op.create_check_constraint(
        "check_shipping_fee_or_general_object_id_not_null",
        "order_lines",
        "is_shipping_fee OR general_object_id IS NOT NULL",
        schema="app_schema",
    )
    op.drop_constraint(
        "fk_order_lines_invoice_fee_product_id",
        "order_lines",
        schema="app_schema",
        type_="foreignkey",
    )
    op.drop_column("order_lines", "invoice_fee_product_id", schema="app_schema")
    op.drop_table("invoice_fee_products", schema="app_schema")