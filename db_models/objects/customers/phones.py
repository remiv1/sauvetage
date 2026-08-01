"""Modèle des téléphones clients."""

from __future__ import annotations

from typing import Any
from datetime import datetime, timezone
from sqlalchemy.orm import mapped_column, relationship, Mapped
from sqlalchemy import Integer, String, DateTime, Boolean, ForeignKey
from db_models import WorkingBase
from db_models.objects.common import QueryMixin
from db_models.objects.customers.constants import CUSTOMER_PK


class CustomerPhones(WorkingBase, QueryMixin):
    """Modèle des téléphones clients."""

    __tablename__ = "customer_phones"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant téléphone unique",
    )
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(CUSTOMER_PK),
        nullable=False,
        comment="Id client associé à ce téléphone",
    )
    phone_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Nom du téléphone (ex: mobile, fixe)"
    )
    phone_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, comment="Numéro de téléphone du client"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Indique si le téléphone est actif ou supprimé",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création du téléphone",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière MàJ du téléphone",
    )

    customer = relationship("Customers", back_populates="phones")

    def __repr__(self) -> str:
        return (
            f"<CustomerPhone(id={self.id}, customer_id={self.customer_id}, "
            f"phone_name={self.phone_name}, phone_number={self.phone_number})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerPhone en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "phone_name": self.phone_name,
            "phone_number": self.phone_number,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerPhones":
        """Crée un objet CustomerPhone à partir d'un dictionnaire."""
        return cls(
            customer_id=data.get("customer_id", 0),
            phone_name=data.get("phone_name"),
            phone_number=data.get("phone_number", ""),
            is_active=data.get("is_active", True),
        )
