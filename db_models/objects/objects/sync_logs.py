"""Journal de synchronisation des objets."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import mapped_column, Mapped
from db_models import WorkingBase


class ObjectSyncLog(WorkingBase):
    """Journal de synchronisation WooCommerce pour les objets, tags, images et TVA."""

    __tablename__ = "object_sync_logs"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type d'entité : object, tag, picture, vat_rate",
    )
    entity_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="ID local de l'entité dans la base de données",
    )
    external_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="ID de l'entité dans le système externe (ex : WooCommerce)",
    )
    external_system: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Système externe : wpwc, henrri, …",
    )
    sync_direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Direction : inbound, outbound",
    )
    operation: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Opération : create, update, delete, batch",
    )
    sync_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Statut : success, error",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        comment="Message d'erreur en cas d'échec",
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date et heure de la synchronisation",
    )

    def __repr__(self) -> str:
        return (
            f"<ObjectSyncLog(id={self.id}, entity_type={self.entity_type}, "
            f"entity_id={self.entity_id}, external_system={self.external_system}, "
            f"operation={self.operation}, sync_status={self.sync_status})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet ObjectSyncLog en dictionnaire."""
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "external_id": self.external_id,
            "external_system": self.external_system,
            "sync_direction": self.sync_direction,
            "operation": self.operation,
            "sync_status": self.sync_status,
            "error_message": self.error_message,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }
