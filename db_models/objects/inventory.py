"""Modèle de données pour les mouvements d'inventaire."""

from typing import Dict, Any
from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship, mapped_column, Mapped
from db_models import WorkingBase
from db_models.objects import QueryMixin


class InventoryMovements(WorkingBase, QueryMixin):
    """Database model for Inventory Movements table."""

    __tablename__ = "inventory_movements"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    general_object_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.general_objects.id"),
        nullable=False,
        comment="ID de l'objet",
    )
    movement_type: Mapped[str] = mapped_column(
        String, nullable=False, comment="Type de mouvement (in/out/reserved/inventory)"
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Quantité du mouvement"
    )
    movement_timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date et heure du mouvement",
    )
    price_at_movement: Mapped[float] = mapped_column(
        Float, comment="Prix d'objet au moment du mouvement"
    )
    source: Mapped[str] = mapped_column(String, comment="Source du mouvement")
    destination: Mapped[str] = mapped_column(String, comment="Destination du mouvement")
    notes: Mapped[str] = mapped_column(
        String, comment="Notes supplémentaires sur le mouvement"
    )

    # Relations
    general_object = relationship(
        "GeneralObjects", back_populates="inventory_movements"
    )
    orderin_line = relationship(
        "OrderInLine", back_populates="inventory_movement", uselist=False
    )

    def __repr__(self) -> str:
        return (
            f"<InventoryMovement(id={self.id}, general_object_id={self.general_object_id}, "
            + f"movement_type={self.movement_type}, quantity={self.quantity}, "
            + f"movement_timestamp={self.movement_timestamp}, "
            + f"price_at_movement={self.price_at_movement})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet InventoryMovement en dictionnaire."""
        return {
            "id": self.id,
            "general_object_id": self.general_object_id,
            "movement_type": self.movement_type,
            "quantity": self.quantity,
            "movement_timestamp": (
                self.movement_timestamp.isoformat() if self.movement_timestamp else None
            ),
            "price_at_movement": self.price_at_movement,
            "source": self.source,
            "destination": self.destination,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InventoryMovements":
        """Crée un objet InventoryMovement à partir d'un dictionnaire."""
        movement_timestamp = data.get("movement_timestamp")
        if isinstance(movement_timestamp, str):
            movement_timestamp = datetime.fromisoformat(movement_timestamp)

        return cls(
            general_object_id=data.get("general_object_id", 0),
            movement_type=data.get("movement_type", ""),
            quantity=data.get("quantity", 0),
            movement_timestamp=movement_timestamp,
            price_at_movement=data.get("price_at_movement"),
            source=data.get("source"),
            destination=data.get("destination"),
            notes=data.get("notes"),
        )
