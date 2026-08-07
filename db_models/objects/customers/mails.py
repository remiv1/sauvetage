"""Modèle des emails clients."""

from __future__ import annotations

from typing import Any
from datetime import datetime, timezone
from sqlalchemy.orm import mapped_column, relationship, Mapped
from sqlalchemy import Integer, String, DateTime, Boolean, ForeignKey
from db_models import WorkingBase
from db_models.objects.common import QueryMixin
from db_models.objects.customers.constants import CUSTOMER_PK


class CustomerMails(WorkingBase, QueryMixin):
    """Modèle des emails clients."""

    __tablename__ = "customer_mails"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant email unique",
    )
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(CUSTOMER_PK),
        nullable=False,
        comment="Id client associé à cet email",
    )
    email_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Nom de l'e-mail (ex: perso, pro)"
    )
    email: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, comment="Adresse e-mail du client"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Indique si l'e-mail est actif ou supprimé",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création de l'e-mail",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière mise à jour de l'e-mail",
    )

    customer = relationship("Customers", back_populates="emails")

    def __repr__(self) -> str:
        return f"<CustomerMail(id={self.id}, customer_id={self.customer_id}, email={self.email})>"

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerMail en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "email_name": self.email_name,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerMails":
        """Crée un objet CustomerMail à partir d'un dictionnaire."""
        return cls(
            customer_id=data.get("customer_id", 0),
            email_name=data.get("email_name"),
            email=data.get("email", ""),
            is_active=data.get("is_active", True),
        )
