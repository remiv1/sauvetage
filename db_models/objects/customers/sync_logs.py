"""Journal de synchronisation des clients."""

from __future__ import annotations

from typing import Any
from datetime import datetime, timezone
from sqlalchemy.orm import mapped_column, relationship, Mapped
from sqlalchemy import Integer, String, DateTime, Text, ForeignKey
from db_models import WorkingBase
from db_models.objects.customers.constants import CUSTOMER_PK


class CustomerSyncLog(WorkingBase):
    """Journal de synchronisation des clients avec les systèmes externes."""

    __tablename__ = "customer_sync_logs"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(CUSTOMER_PK), nullable=False
    )
    sync_direction: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Direction : inbound, outbound"
    )
    sync_status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Statut : success, failed, pending"
    )
    operation: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Opération : create, update, delete"
    )
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_system: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Système externe : wpwc, henrri, …"
    )
    fields_synced: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    customer = relationship("Customers", back_populates="sync_logs")

    def __repr__(self) -> str:
        return (
            f"<CustomerSyncLog(id={self.id}, customer_id={self.customer_id}, "
            f"external_system={self.external_system}, operation={self.operation}, "
            f"sync_status={self.sync_status})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerSyncLog en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "external_system": self.external_system,
            "sync_direction": self.sync_direction,
            "operation": self.operation,
            "sync_status": self.sync_status,
            "external_id": self.external_id,
            "fields_synced": self.fields_synced,
            "error_message": self.error_message,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerSyncLog":
        """Crée un objet CustomerSyncLog à partir d'un dictionnaire."""
        return cls(
            customer_id=data.get("customer_id", 0),
            external_system=data.get("external_system", ""),
            sync_direction=data.get("sync_direction", "inbound"),
            operation=data.get("operation", "create"),
            sync_status=data.get("sync_status", "pending"),
            external_id=data.get("external_id"),
            fields_synced=data.get("fields_synced"),
            error_message=data.get("error_message"),
        )
