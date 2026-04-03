"""Module de dépôt pour la gestion des factures."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import Invoice, InvoiceLine


class InvoiceRepository(BaseRepository):
    """Dépôt des données pour la gestion des factures."""

    def generate_reference(self) -> str:
        """Génère une référence unique au format FAC-YYMM-00001."""
        now = datetime.now(timezone.utc)
        yymm = now.strftime("%y%m")
        pattern = f"FAC-{yymm}-%"
        last_ref = self.session.execute(
            select(Invoice.reference)
            .where(Invoice.reference.like(pattern))
            .order_by(Invoice.reference.desc())
            .limit(1)
        ).scalar()
        if last_ref:
            last_num = int(last_ref.split("-")[-1])
            next_num = last_num + 1
        else:
            next_num = 1
        return f"FAC-{yymm}-{next_num:05d}"

    def create_invoice(
        self,
        *,
        order_id: int,
        line_items: list[Dict[str, Any]],
        create_source: str = "web",
    ) -> Invoice:
        """Crée une facture avec ses lignes.
        Args:
            order_id: ID de la commande parente.
            line_items: Liste de dicts {order_line_id, quantity, unit_price, discount, vat_rate}.
            create_source: Source de création.
        Returns:
            Invoice créée.
        """
        total_ht = 0.0
        total_vat = 0.0
        for item in line_items:
            price = float(item["unit_price"]) * item["quantity"]
            disc = price * float(item.get("discount", 0)) / 100
            ht = price - disc
            total_ht += ht
            total_vat += ht * float(item["vat_rate"]) / 100

        invoice = Invoice(
            order_id=order_id,
            reference=self.generate_reference(),
            total_amount=round(total_ht, 2),
            vat_amount=round(total_vat, 2),
            create_source=create_source,
        )
        try:
            self.session.add(invoice)
            self.session.flush()  # get invoice.id

            for item in line_items:
                inv_line = InvoiceLine(
                    invoice_id=invoice.id,
                    order_line_id=item["order_line_id"],
                    quantity=item["quantity"],
                )
                self.session.add(inv_line)

            self.session.commit()
            return invoice
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la création de la facture : {e.orig}"
            ) from e

    def get_by_id(self, invoice_id: int) -> Optional[Invoice]:
        """Récupère une facture par son identifiant avec ses lignes."""
        stmt = (
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .options(selectinload(Invoice.lines))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_order_id(self, order_id: int) -> list[Invoice]:
        """Récupère toutes les factures d'une commande."""
        stmt = (
            select(Invoice)
            .where(Invoice.order_id == order_id)
            .options(selectinload(Invoice.lines))
            .order_by(Invoice.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def sync_to_henrri(self, invoice: Invoice) -> Dict[str, Any]:
        """Stub pour la synchronisation future avec l'API Henrri.

        TODO: Implémenter après le 15 avril — appel API Henrri pour
        créer/mettre à jour la facture dans le système comptable.
        """
        raise NotImplementedError(
            "Synchronisation Henrri non encore implémentée. "
            "Prévu pour après le 15 avril."
        )
