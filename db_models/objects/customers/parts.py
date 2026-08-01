"""Modèle des données clients particuliers."""

from __future__ import annotations

from typing import Any
from datetime import datetime
from sqlalchemy.orm import mapped_column, relationship, Mapped
from sqlalchemy import Integer, String, DateTime, ForeignKey
from db_models import WorkingBase
from db_models.objects.common import QueryMixin
from db_models.objects.customers.constants import CUSTOMER_PK


class CustomerParts(WorkingBase, QueryMixin):
    """
    Modèle des données spécifiques aux clients particuliers.
    """

    __tablename__ = "customer_parts"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="Identifiant Part unique"
    )
    contact_henrri_id: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        comment="Identifiant de contact Henrri",
    )
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(CUSTOMER_PK),
        nullable=False,
        unique=True,
        comment="Id client associé à part",
    )
    civil_title: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="Civilité (ex: M., Mme, Dr)"
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    customer = relationship("Customers", back_populates="part", uselist=False)

    def __repr__(self) -> str:
        return (
            f"<CustomerPart(id={self.id}, customer_id={self.customer_id}, "
            f"first_name={self.first_name}, last_name={self.last_name})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerPart en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "civil_title": self.civil_title,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "date_of_birth": (
                self.date_of_birth.isoformat() if self.date_of_birth else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerParts":
        """Crée un objet CustomerPart à partir d'un dictionnaire."""
        date_of_birth = data.get("date_of_birth")
        return cls(
            customer_id=data.get("customer_id", 0),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            date_of_birth=(
                datetime.fromisoformat(date_of_birth) if date_of_birth else None
            ),
        )
