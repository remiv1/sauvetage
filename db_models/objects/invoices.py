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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(14), unique=True, nullable=False)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False,
                                                 comment="Montant total de la facture")

    # Metadonnées audit
    create_source: Mapped[str] = mapped_column(String(50), nullable=False,
                                               comment="Source de la facture")
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 nullable=False,
                                                 comment="Date de création de la facture")
    update_source: Mapped[str] = mapped_column(String(50), nullable=False,
                                               comment="Source de la dernière mise à jour")
    updated_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc),
                                                 nullable=False,
                                                 comment="Date dernière mise à jour de la facture")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True,
                                                            comment="Dernière synchronisation")

    # Relations
    order_lines = relationship("OrderLine", back_populates="invoice")

    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, reference={self.reference}, " \
               + f"total_amount={self.total_amount})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet Invoice en dictionnaire."""
        return {
            "id": self.id,
            "reference": self.reference,
            "order_id": self.order_id,
            "total_amount": float(self.total_amount),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Invoice":
        """Crée un objet Invoice à partir d'un dictionnaire."""
        return cls(
            reference=data.get("reference", ""),
            order_id=data.get("order_id"),
            total_amount=data.get("total_amount", 0.0)
        )

@event.listens_for(Invoice, "before_delete")
def _prevent_invoice_delete(_mapper: Any, _connection: Any,    # type: ignore
                            _target: "Invoice") -> None:
    raise ValueError("Une suppression de facture est interdite.")
