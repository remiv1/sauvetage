"""Repository pour les journaux de synchronisation avec les systèmes externes.

Couvre quatre entités :
- ObjectSyncLog  — objets, tags, images, TVA  ↔ WooCommerce
- CustomerSyncLog — clients                   ↔ WooCommerce / Henrri
- OrderSyncLog    — commandes                 ↔ WooCommerce
- InvoiceSyncLog  — factures                  ↔ Henrri
"""

from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import select

from db_models.objects import (
    ObjectSyncLog,
    CustomerSyncLog,
    OrderSyncLog,
    InvoiceSyncLog,
)
from db_models.repositories.base_repo import BaseRepository


class SyncLogRepository(BaseRepository):
    """Repository pour l'écriture et la lecture des journaux de synchronisation."""

    # ------------------------------------------------------------------ objects

    def log_object(
        self,
        *,
        entity_type: str,
        entity_id: Optional[int],
        external_id: Optional[str],
        external_system: str = "wpwc",
        sync_direction: str,
        operation: str,
        sync_status: str,
        error_message: Optional[str] = None,
    ) -> ObjectSyncLog:
        """Enregistre une entrée de synchronisation pour un objet WooCommerce.

        Args:
            entity_type: Type d'entité (object, tag, picture, vat_rate, …).
            entity_id: ID local de l'entité (None si inconnu).
            external_id: ID de l'entité dans le système externe.
            external_system: Système cible (défaut : "wpwc").
            sync_direction: "inbound" ou "outbound".
            operation: "create", "update", "delete", "batch".
            sync_status: "success", "failed", "pending", "error".
            error_message: Message en cas d'échec.
        Returns:
            L'instance ObjectSyncLog ajoutée à la session (non committée).
        """
        log = ObjectSyncLog(
            entity_type=entity_type,
            entity_id=entity_id,
            external_id=external_id,
            external_system=external_system,
            sync_direction=sync_direction,
            operation=operation,
            sync_status=sync_status,
            error_message=error_message,
            synced_at=datetime.now(timezone.utc),
        )
        self.session.add(log)
        return log

    def get_for_object(
        self, entity_type: str, entity_id: int
    ) -> Sequence[ObjectSyncLog]:
        """Retourne tous les logs d'un objet local, du plus récent au plus ancien."""
        stmt = (
            select(ObjectSyncLog)
            .where(
                ObjectSyncLog.entity_type == entity_type,
                ObjectSyncLog.entity_id == entity_id,
            )
            .order_by(ObjectSyncLog.synced_at.desc())
        )
        return self.session.execute(stmt).scalars().all()

    # ---------------------------------------------------------------- customers

    def log_customer(
        self,
        *,
        customer_id: int,
        external_id: Optional[str],
        external_system: str,
        sync_direction: str,
        operation: str,
        sync_status: str,
        error_message: Optional[str] = None,
        fields_synced: Optional[str] = None,
    ) -> CustomerSyncLog:
        """Enregistre une entrée de synchronisation pour un client.

        Args:
            customer_id: ID local du client.
            external_id: ID du client dans le système externe.
            external_system: "wpwc" ou "henrri".
            sync_direction: "inbound" ou "outbound".
            operation: "create", "update", "delete".
            sync_status: "success", "failed", "pending".
            error_message: Message en cas d'échec.
            fields_synced: JSON listant les champs synchronisés (optionnel).
        Returns:
            L'instance CustomerSyncLog ajoutée à la session (non committée).
        """
        log = CustomerSyncLog(
            customer_id=customer_id,
            external_id=external_id,
            external_system=external_system,
            sync_direction=sync_direction,
            operation=operation,
            sync_status=sync_status,
            error_message=error_message,
            fields_synced=fields_synced,
        )
        self.session.add(log)
        return log

    def get_for_customer(self, customer_id: int) -> Sequence[CustomerSyncLog]:
        """Retourne tous les logs d'un client, du plus récent au plus ancien."""
        stmt = (
            select(CustomerSyncLog)
            .where(CustomerSyncLog.customer_id == customer_id)
            .order_by(CustomerSyncLog.synced_at.desc())
        )
        return self.session.execute(stmt).scalars().all()

    # ------------------------------------------------------------------ orders

    def log_order(
        self,
        *,
        order_id: int,
        external_id: Optional[str],
        external_system: str = "wpwc",
        sync_direction: str,
        operation: str,
        sync_status: str,
        error_message: Optional[str] = None,
    ) -> OrderSyncLog:
        """Enregistre une entrée de synchronisation pour une commande.

        Args:
            order_id: ID local de la commande.
            external_id: ID de la commande dans le système externe.
            external_system: Système cible (défaut : "wpwc").
            sync_direction: "inbound" ou "outbound".
            operation: "create", "update", "delete".
            sync_status: "success", "failed", "pending".
            error_message: Message en cas d'échec.
        Returns:
            L'instance OrderSyncLog ajoutée à la session (non committée).
        """
        log = OrderSyncLog(
            order_id=order_id,
            external_id=external_id,
            external_system=external_system,
            sync_direction=sync_direction,
            operation=operation,
            sync_status=sync_status,
            error_message=error_message,
            synced_at=datetime.now(timezone.utc),
        )
        self.session.add(log)
        return log

    def get_for_order(self, order_id: int) -> Sequence[OrderSyncLog]:
        """Retourne tous les logs d'une commande, du plus récent au plus ancien."""
        stmt = (
            select(OrderSyncLog)
            .where(OrderSyncLog.order_id == order_id)
            .order_by(OrderSyncLog.synced_at.desc())
        )
        return self.session.execute(stmt).scalars().all()

    # ---------------------------------------------------------------- invoices

    def log_invoice(
        self,
        *,
        invoice_id: int,
        external_id: Optional[str],
        external_system: str = "henrri",
        sync_direction: str,
        operation: str,
        sync_status: str,
        error_message: Optional[str] = None,
    ) -> InvoiceSyncLog:
        """Enregistre une entrée de synchronisation pour une facture.

        Args:
            invoice_id: ID local de la facture.
            external_id: ID de la facture dans le système externe (ex : ID Henrri).
            external_system: Système cible (défaut : "henrri").
            sync_direction: "inbound" ou "outbound".
            operation: "create", "update", "delete".
            sync_status: "success", "failed", "pending".
            error_message: Message en cas d'échec.
        Returns:
            L'instance InvoiceSyncLog ajoutée à la session (non committée).
        """
        log = InvoiceSyncLog(
            invoice_id=invoice_id,
            external_id=external_id,
            external_system=external_system,
            sync_direction=sync_direction,
            operation=operation,
            sync_status=sync_status,
            error_message=error_message,
            synced_at=datetime.now(timezone.utc),
        )
        self.session.add(log)
        return log

    def get_for_invoice(self, invoice_id: int) -> Sequence[InvoiceSyncLog]:
        """Retourne tous les logs d'une facture, du plus récent au plus ancien."""
        stmt = (
            select(InvoiceSyncLog)
            .where(InvoiceSyncLog.invoice_id == invoice_id)
            .order_by(InvoiceSyncLog.synced_at.desc())
        )
        return self.session.execute(stmt).scalars().all()
