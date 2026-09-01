"""Module de données pour les factures."""

from typing import Any, Dict, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import (
    String,
    Integer,
    ForeignKey,
    DateTime,
    Numeric,
    Text,
    UniqueConstraint,
    event,
)
from db_models import WorkingBase
from db_models.objects import QueryMixin

HENRRI_INVOICE_DOCUMENT_TYPE: dict[str, Any] = {
    "document_kind": "invoice",
    "id": 1,
    "is_accounting": True,
    "is_managed": True,
    "is_mandatory": True,
    "is_visible": True,
}
HENRRI_CREDIT_NOTE_DOCUMENT_TYPE: dict[str, Any] = {
    "document_kind": "creditNote",
    "id": 2,
    "is_accounting": True,
    "is_managed": True,
    "is_mandatory": True,
    "is_visible": True,
}


class InvoiceFeeProduct(WorkingBase, QueryMixin):
    """Produit de facturation associé à un type de frais et un taux de TVA."""

    __tablename__ = "invoice_fee_products"
    __table_args__ = (
        UniqueConstraint(
            "fee_type",
            "vat_rate_id",
            name="uq_invoice_fee_products_type_vat_rate",
        ),
        {"schema": "app_schema"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fee_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Type de frais facturé"
    )
    vat_rate_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.vat_rates.id"),
        nullable=False,
        comment="Taux de TVA du produit de frais",
    )
    henrri_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        unique=True,
        comment="Identifiant du produit de frais chez Henrri",
    )
    reference: Mapped[str] = mapped_column(
        String(14), nullable=False, unique=True, comment="Référence du produit de frais"
    )
    description: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Description du produit de frais"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création du produit de frais",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière mise à jour du produit de frais",
    )

    vat_rate = relationship("VatRate", back_populates="invoice_fee_products")
    order_lines = relationship("OrderLine", back_populates="invoice_fee_product")

    def to_dict_henrri(self) -> Dict[str, Any]:
        """Convertit le produit de frais au format attendu par Henrri."""
        vat_percent = float(self.vat_rate.rate)
        shipping_amount = 0.0
        shipping_lines = [
            line for line in self.order_lines if getattr(line, "is_shipping_fee", False)
        ]
        if shipping_lines:
            shipping_values = [
                abs(float(line.unit_price))
                for line in shipping_lines
                if line.unit_price is not None
            ]
            if shipping_values:
                shipping_amount = max(shipping_values)
        selling_price_with_tax = shipping_amount * (1 + vat_percent / 100)
        return {
            "id": self.henrri_id,
            "reference": self.reference,
            "description": self.description,
            "is_tax_included": False,
            "selling_price_without_tax": shipping_amount,
            "selling_price_with_tax": selling_price_with_tax,
            "purchase_price": 0.0,
            "vat_percent": vat_percent,
            "is_a_group": False,
            "item_category_id": 17,
            "unit_id": 16,
            "creation_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }


class Invoice(WorkingBase, QueryMixin):
    """Modèle de données pour une facture."""

    __tablename__ = "invoices"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.orders.id"),
        nullable=False,
        comment="Commande parente",
    )
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.customers.id"),
        nullable=False,
        comment="Client de la facture",
    )
    henrri_id: Mapped[str] = mapped_column(
        String(50), nullable=True, comment="ID externe de la facture (Henrri)"
    )
    reference: Mapped[str] = mapped_column(String(14), unique=True, nullable=False)
    total_amount: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, comment="Montant total de la facture"
    )
    vat_amount: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, comment="Montant de la TVA de la facture"
    )

    # Metadonnées audit
    create_source: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Source de la facture"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Date de création de la facture",
    )
    update_source: Mapped[str] = mapped_column(
        String(50), nullable=True, comment="Source de la dernière mise à jour"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date dernière mise à jour de la facture",
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="Dernière synchronisation"
    )

    # Relations
    customer = relationship("Customers", back_populates="invoices")
    order = relationship("Order", back_populates="invoices")
    lines = relationship(
        "InvoiceLine", back_populates="invoice", cascade="all, delete-orphan"
    )
    sync_logs = relationship("InvoiceSyncLog", back_populates="invoice", uselist=True)

    def __repr__(self) -> str:
        return (
            f"<Invoice(id={self.id}, reference={self.reference}, "
            + f"total_amount={self.total_amount})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet Invoice en dictionnaire."""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "reference": self.reference,
            "ext_id": self.henrri_id,
            "total_amount": float(self.total_amount),
            "vat_amount": float(self.vat_amount),
            "lines": [ln.to_dict() for ln in self.lines] if self.lines else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_dict_henrri(self) -> Dict[str, Any]:
        """
        Convertit l'objet Invoice en dictionnaire pour Henrri.
        
        Chez Henrri, une facture est un document, lui-même subdivisé en plusieurs éléments :
        un document et son type, un titre, une date, de totaux, les lignes qui y sont rattachées,
        d'éventuelles lignes de décoration, une client et son adresse, le contact rattaché.

        Returns:
            dict[str, Any]: Dictionnaire représentant la facture chez Henrri.

        Raises:
            ValueError: Si le client n'est pas encore synchronisé chez Henrri.
        """
        now_datetime = str(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        due_datetime = str(
            (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        )
        order_date = str(
            self.order.created_at.strftime("%Y-%m-%d")
            if self.order and self.order.created_at
            else now_datetime
        )
        if self.customer is None or self.customer.henrri_id is None:
            raise ValueError(
                f"Facture {self.reference} : le client doit être synchronisé "
                "chez Henrri avant la création du document."
            )
        customer_payload = self.customer.to_dict_henrri()
        customer_address = customer_payload.get("address") or {}
        document_type = (
            HENRRI_CREDIT_NOTE_DOCUMENT_TYPE
            if float(self.total_amount) < 0
            else HENRRI_INVOICE_DOCUMENT_TYPE
        )
        invoice = {
            "identity": self.reference,
            "finalized": False,
            "document_type_id": document_type["id"],
            "document_type": document_type,
            "title": f"Facture de la commande du {order_date}",
            "subtitle": f"Facture Editions Sauvetage du {now_datetime}",
            "price_before_tax": float(self.total_amount),
            "tax_amount": float(self.vat_amount),
            "price_after_tax": float(self.total_amount) + float(self.vat_amount),
            "due_label": due_datetime,
            "date": now_datetime,
            "validated": True,
            "validation_date": now_datetime,
            "customer_id": int(self.customer.henrri_id),
            "customer": customer_payload,
            "customer_address": customer_address,
            "lines": [line.to_dict_henrri() for line in self.lines] if self.lines else [],
            "bank_account_label": "Banque",
        }
        if self.henrri_id:
            invoice["id"] = int(self.henrri_id)
        return invoice

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Invoice":
        """Crée un objet Invoice à partir d'un dictionnaire."""
        return cls(**data)


class InvoiceLine(WorkingBase, QueryMixin):
    """Ligne de facture — lie une ligne de commande à une facture avec une quantité."""

    __tablename__ = "invoice_lines"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("app_schema.invoices.id"), nullable=False
    )
    henrri_id: Mapped[int] = mapped_column(
        Integer, nullable=True, comment="ID de la ligne de facture chez Henrri"
    )
    order_line_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("app_schema.order_lines.id"), nullable=False
    )
    reference: Mapped[str] = mapped_column(
        String(14), nullable=False, comment="Référence de la ligne de facture"
    )
    description: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Description de la ligne de facture"
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Quantité facturée"
    )
    unit_price: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, comment="Prix unitaire de la ligne de facture"
    )
    discount: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False,
        default=0.0, comment="Remise appliquée à la ligne de facture"
    )
    vat_rate: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, comment="Taux de TVA appliqué à la ligne de facture"
    )

    # Relations
    invoice = relationship("Invoice", back_populates="lines")
    order_line = relationship("OrderLine", back_populates="invoice_lines")

    def __repr__(self) -> str:
        return (
            f"<InvoiceLine(id={self.id}, invoice_id={self.invoice_id}, "
            + f"order_line_id={self.order_line_id}, quantity={self.quantity})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet InvoiceLine en dictionnaire."""
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "order_line_id": self.order_line_id,
            "quantity": self.quantity,
        }

    def to_dict_henrri(self) -> Dict[str, Any]:
        """Convertit l'objet InvoiceLine en dictionnaire pour Henrri."""
        item_id = None
        if self.order_line and self.order_line.is_shipping_fee:
            if self.order_line.invoice_fee_product:
                item_id = self.order_line.invoice_fee_product.henrri_id
        elif self.order_line and self.order_line.general_object:
            item_id = self.order_line.general_object.henrri_id
        document_id = (
            int(self.invoice.henrri_id)
            if self.invoice and self.invoice.henrri_id
            else None
        )
        payload: dict[str, Any] = {
            "id": self.henrri_id,
            "document_id": document_id,
            "reference": self.reference,
            "description": self.description,
            "selling_price_without_tax": float(self.unit_price),
            "vat_percent": float(self.vat_rate),
            "quantity": float(self.quantity),
            "is_tax_included": False,
            "are_elements_of_group_shown": False,
            "type_id": 3,
        }
        payload["item_id"] = item_id
        return payload


@event.listens_for(Invoice, "before_delete")
def _prevent_invoice_delete(
    _mapper: Any, _connection: Any, _target: "Invoice"  # type: ignore
) -> None:
    raise ValueError("Une suppression de facture est interdite.")


class InvoiceSyncLog(WorkingBase):
    """Journal de synchronisation Henrri pour les factures."""

    __tablename__ = "invoice_sync_logs"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.invoices.id"),
        nullable=False,
        comment="Facture associée",
    )

    # Système externe et direction
    external_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="ID de la facture dans le système externe (ex : ID Henrri)",
    )
    external_system: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Système externe : henrri, …",
    )
    sync_direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Direction : inbound, outbound",
    )
    operation: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Opération : create, update, delete",
    )

    # Résultat
    sync_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Statut : success, failed, pending",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Message d'erreur en cas d'échec",
    )

    # Horodatage
    synced_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date et heure de la synchronisation",
    )

    invoice = relationship("Invoice", back_populates="sync_logs")

    def __repr__(self) -> str:
        return (
            f"<InvoiceSyncLog(id={self.id}, invoice_id={self.invoice_id}, "
            f"external_system={self.external_system}, operation={self.operation}, "
            f"sync_status={self.sync_status})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet InvoiceSyncLog en dictionnaire."""
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "external_id": self.external_id,
            "external_system": self.external_system,
            "sync_direction": self.sync_direction,
            "operation": self.operation,
            "sync_status": self.sync_status,
            "error_message": self.error_message,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }
