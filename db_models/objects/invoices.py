"""Module de données pour les factures."""

from typing import Any, Dict
from datetime import datetime, timezone
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import String, Integer, ForeignKey, DateTime, Numeric, event
from db_models import WorkingBase
from db_models.objects import QueryMixin


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
    ext_id: Mapped[str] = mapped_column(
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
    order = relationship("Order", back_populates="invoices")
    lines = relationship(
        "InvoiceLine", back_populates="invoice", cascade="all, delete-orphan"
    )

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
            "ext_id": self.ext_id,
            "total_amount": float(self.total_amount),
            "vat_amount": float(self.vat_amount),
            "lines": [ln.to_dict() for ln in self.lines] if self.lines else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

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


@event.listens_for(Invoice, "before_delete")
def _prevent_invoice_delete(
    _mapper: Any, _connection: Any, _target: "Invoice"  # type: ignore
) -> None:
    raise ValueError("Une suppression de facture est interdite.")
