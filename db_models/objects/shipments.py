"""Modèle de données pour les envois."""

from typing import Any, Dict
from datetime import datetime, timezone
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import String, Integer, ForeignKey, DateTime
from db_models import WorkingBase
from db_models.objects import QueryMixin


class Shipment(WorkingBase, QueryMixin):
    """Modèle de données pour un envoi."""

    __tablename__ = "shipments"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.orders.id"),
        nullable=False,
        comment="Commande parente",
    )
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
    order = relationship("Order", back_populates="shipments")
    lines = relationship(
        "ShipmentLine", back_populates="shipment", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Shipment(id={self.id}, reference={self.reference}, carrier={self.carrier}, "
            f"tracking_number={self.tracking_number})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet Shipment en dictionnaire."""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "reference": self.reference,
            "carrier": self.carrier,
            "tracking_number": self.tracking_number,
            "lines": [ln.to_dict() for ln in self.lines] if self.lines else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Shipment":
        """Crée un objet Shipment à partir d'un dictionnaire."""
        return cls(
            order_id=data.get("order_id"),
            reference=data.get("reference", ""),
            carrier=data.get("carrier", ""),
            tracking_number=data.get("tracking_number"),
        )


class ShipmentLine(WorkingBase, QueryMixin):
    """Ligne d'envoi — lie une ligne de commande à un envoi avec une quantité."""

    __tablename__ = "shipment_lines"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shipment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("app_schema.shipments.id"), nullable=False
    )
    order_line_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("app_schema.order_lines.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Quantité expédiée"
    )

    # Relations
    shipment = relationship("Shipment", back_populates="lines")
    order_line = relationship("OrderLine", back_populates="shipment_lines")

    def __repr__(self) -> str:
        return (
            f"<ShipmentLine(id={self.id}, shipment_id={self.shipment_id}, "
            + f"order_line_id={self.order_line_id}, quantity={self.quantity})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet ShipmentLine en dictionnaire."""
        return {
            "id": self.id,
            "shipment_id": self.shipment_id,
            "order_line_id": self.order_line_id,
            "quantity": self.quantity,
        }
