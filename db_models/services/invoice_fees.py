"""Gestion des produits utilisés exclusivement pour les frais de facturation."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from db_models.objects import InvoiceFeeProduct, VatRate


def get_or_create_invoice_fee_product(
    session: Session,
    *,
    fee_type: str,
    vat_rate: VatRate,
) -> InvoiceFeeProduct:
    """Retourne le produit de frais correspondant, en le créant si nécessaire.

    Args:
        session: Session SQLAlchemy courante.
        fee_type: Type fonctionnel du frais.
        vat_rate: Taux de TVA rattaché au produit de frais.

    Returns:
        Produit de frais unique pour le type et le taux de TVA.
    """
    existing = session.execute(
        select(InvoiceFeeProduct).where(
            InvoiceFeeProduct.fee_type == fee_type,
            InvoiceFeeProduct.vat_rate_id == vat_rate.id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    if fee_type != "shipping":
        raise ValueError(f"Type de frais de facturation non pris en charge : {fee_type}.")

    now = datetime.now(timezone.utc)
    statement = (
        insert(InvoiceFeeProduct)
        .values(
            fee_type=fee_type,
            vat_rate_id=vat_rate.id,
            reference=f"PORT-{vat_rate.id}",
            description=f"Frais de port (TVA {vat_rate.rate:g} %)",
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_nothing(
            constraint="uq_invoice_fee_products_type_vat_rate"
        )
        .returning(InvoiceFeeProduct.id)
    )
    created_id = session.execute(statement).scalar_one_or_none()
    if created_id is not None:
        return session.get_one(InvoiceFeeProduct, created_id)

    return session.execute(
        select(InvoiceFeeProduct).where(
            InvoiceFeeProduct.fee_type == fee_type,
            InvoiceFeeProduct.vat_rate_id == vat_rate.id,
        )
    ).scalar_one()
