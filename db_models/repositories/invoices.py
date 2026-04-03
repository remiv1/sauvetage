"""Module de dépôt pour la gestion des factures."""

from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import Invoice


class InvoiceRepository(BaseRepository):
    """
    Dépôt des données pour la gestion des factures.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.model = Invoice
        self._kwargs = tuple(column.name for column in self.model.__table__.columns)

    def create(self, invoice_data: Dict[str, Any]):
        """
        Création d'une nouvelle facture.
        Les champs requis pour créer une facture sont définis dans le modèle Invoices.
        """
        extra_keys = set(invoice_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")

        invoice = self.model(**invoice_data)
        try:
            self.session.add(invoice)
            self.session.commit()
            return invoice
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la création de la facture : {str(e)}"
            ) from e

    def update(
        self,
        update_data: Dict[str, Any],
        invoice_id: Optional[int] = None,
        invoice: Optional[Invoice] = None,
    ) -> Invoice:
        """
        Mise à jour d'une facture existante.
        """
        if set(update_data.keys()) - set(self._kwargs):
            extra_keys = set(update_data.keys()) - set(self._kwargs)
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")

        if invoice_id is None and invoice is None:
            raise ValueError("Fournir un identifiant ou un objet pour la mise à jour.")

        if invoice is None:
            invoice = self.session.query(self.model).filter_by(id=invoice_id).first()
            if not invoice:
                raise ValueError(f"Facture avec id {invoice_id} non trouvée.")

        for key, value in update_data.items():
            setattr(invoice, key, value)

        try:
            self.session.commit()
            return invoice
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la mise à jour de la facture : {str(e)}"
            ) from e

    def get_by_id(self, invoice_id: int) -> Optional[Invoice]:
        """Récupère une facture par son identifiant avec ses lignes de commande.
        Args:
            invoice_id: L'identifiant de la facture.
        Returns:
            Invoice ou None.
        """
        stmt = (
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .options(selectinload(Invoice.order_lines))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def sync_to_henrri(self, invoice: Invoice) -> Dict[str, Any]:
        """Stub pour la synchronisation future avec l'API Henrri.

        TODO: Implémenter après le 15 avril — appel API Henrri pour
        créer/mettre à jour la facture dans le système comptable.

        Args:
            invoice: La facture à synchroniser.
        Returns:
            Dict avec le statut de la synchronisation.
        """
        raise NotImplementedError(
            "Synchronisation Henrri non encore implémentée. "
            "Prévu pour après le 15 avril."
        )
