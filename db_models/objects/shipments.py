"""Modèle de données pour les envois."""

from typing import Any, Dict
from datetime import datetime, timezone
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import String, Integer, DateTime
from db_models import WorkingBase
from db_models.objects import QueryMixin

CASCADE_OPTIONS = "all, delete-orphan"


class Shipment(WorkingBase, QueryMixin):
    """Modèle de données pour un envoi."""

    __tablename__ = "shipments"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(14), unique=True, nullable=False)
    carrier: Mapped[str] = mapped_column(String(50), nullable=False)
    tracking_number: Mapped[str] = mapped_column(String(50), nullable=True)

    # Metadonnées audit
    create_source: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Source de l'envoi"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création de l'envoi",
    )
    update_source: Mapped[str] = mapped_column(
        String(50), nullable=True, comment="Source de la dernière mise à jour"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date dernière mise à jour de l'envoi",
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="Dernière synchronisation"
    )

    # Relations
    order_lines = relationship("OrderLine", back_populates="shipment")

    def __repr__(self) -> str:
        return (
            f"<Shipment(id={self.id}, reference={self.reference}, carrier={self.carrier}, "
            f"tracking_number={self.tracking_number})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet Shipment en dictionnaire."""
        return {
            "id": self.id,
            "reference": self.reference,
            "carrier": self.carrier,
            "tracking_number": self.tracking_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Shipment":
        """Crée un objet Shipment à partir d'un dictionnaire."""
        return cls(
            reference=data.get("reference", ""),
            carrier=data.get("carrier", ""),
            tracking_number=data.get("tracking_number"),
        )
