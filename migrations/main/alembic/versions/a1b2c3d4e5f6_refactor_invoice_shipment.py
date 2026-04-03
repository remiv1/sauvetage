"""refactor_invoice_shipment

Revision ID: a1b2c3d4e5f6
Revises: d5c197e3ea75
Create Date: 2026-04-03 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd5c197e3ea75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Restructure invoice/shipment: add order_id FK, create line tables, drop old FKs."""

    # 1. Add order_id to invoices
    op.add_column(  # pylint: disable=no-member
        'invoices',
        sa.Column('order_id', sa.Integer(), nullable=True, comment='Commande parente'),
        schema='app_schema',
    )
    op.create_foreign_key(  # pylint: disable=no-member
        'fk_invoices_order_id',
        'invoices', 'orders',
        ['order_id'], ['id'],
        source_schema='app_schema',
        referent_schema='app_schema',
    )

    # 2. Add order_id to shipments
    op.add_column(  # pylint: disable=no-member
        'shipments',
        sa.Column('order_id', sa.Integer(), nullable=True, comment='Commande parente'),
        schema='app_schema',
    )
    op.create_foreign_key(  # pylint: disable=no-member
        'fk_shipments_order_id',
        'shipments', 'orders',
        ['order_id'], ['id'],
        source_schema='app_schema',
        referent_schema='app_schema',
    )

    # 3. Create invoice_lines table
    op.create_table(  # pylint: disable=no-member
        'invoice_lines',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('app_schema.invoices.id'), nullable=False),
        sa.Column('order_line_id', sa.Integer(), sa.ForeignKey('app_schema.order_lines.id'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, comment='Quantité facturée'),
        schema='app_schema',
    )

    # 4. Create shipment_lines table
    op.create_table(  # pylint: disable=no-member
        'shipment_lines',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('shipment_id', sa.Integer(), sa.ForeignKey('app_schema.shipments.id'), nullable=False),
        sa.Column('order_line_id', sa.Integer(), sa.ForeignKey('app_schema.order_lines.id'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, comment='Quantité expédiée'),
        schema='app_schema',
    )

    # 5. Drop old FKs and columns on order_lines
    # Drop FK constraints first (naming convention: may vary)
    op.drop_constraint(  # pylint: disable=no-member
        'order_lines_invoice_id_fkey', 'order_lines',
        type_='foreignkey', schema='app_schema',
    )
    op.drop_constraint(  # pylint: disable=no-member
        'order_lines_shipment_id_fkey', 'order_lines',
        type_='foreignkey', schema='app_schema',
    )
    op.drop_column('order_lines', 'invoice_id', schema='app_schema')  # pylint: disable=no-member
    op.drop_column('order_lines', 'shipment_id', schema='app_schema')  # pylint: disable=no-member


def downgrade() -> None:
    """Reverse: restore old FKs, drop line tables, remove order_id columns."""

    # 1. Re-add invoice_id, shipment_id to order_lines
    op.add_column(  # pylint: disable=no-member
        'order_lines',
        sa.Column('invoice_id', sa.Integer(), nullable=True),
        schema='app_schema',
    )
    op.add_column(  # pylint: disable=no-member
        'order_lines',
        sa.Column('shipment_id', sa.Integer(), nullable=True),
        schema='app_schema',
    )
    op.create_foreign_key(  # pylint: disable=no-member
        'order_lines_invoice_id_fkey',
        'order_lines', 'invoices',
        ['invoice_id'], ['id'],
        source_schema='app_schema',
        referent_schema='app_schema',
    )
    op.create_foreign_key(  # pylint: disable=no-member
        'order_lines_shipment_id_fkey',
        'order_lines', 'shipments',
        ['shipment_id'], ['id'],
        source_schema='app_schema',
        referent_schema='app_schema',
    )

    # 2. Drop line tables
    op.drop_table('shipment_lines', schema='app_schema')  # pylint: disable=no-member
    op.drop_table('invoice_lines', schema='app_schema')  # pylint: disable=no-member

    # 3. Drop order_id from invoices and shipments
    op.drop_constraint('fk_invoices_order_id', 'invoices', type_='foreignkey', schema='app_schema')  # pylint: disable=no-member
    op.drop_column('invoices', 'order_id', schema='app_schema')  # pylint: disable=no-member
    op.drop_constraint('fk_shipments_order_id', 'shipments', type_='foreignkey', schema='app_schema')  # pylint: disable=no-member
    op.drop_column('shipments', 'order_id', schema='app_schema')  # pylint: disable=no-member
