"""Modèle des données clients professionnels."""

from __future__ import annotations

from typing import Any
from sqlalchemy.orm import mapped_column, relationship, Mapped
from sqlalchemy import Integer, String, ForeignKey
from db_models import WorkingBase
from db_models.objects.common import QueryMixin
from db_models.objects.customers.constants import CUSTOMER_PK


class CustomerPros(WorkingBase, QueryMixin):
    """Modèle des données spécifiques aux clients professionnels."""

    __tablename__ = "customer_pros"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="Identifiant unique"
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
        comment="Identifiant du client associé",
    )
    company_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Nom de l'entreprise"
    )
    siret_number: Mapped[str | None] = mapped_column(
        String(14), nullable=False, unique=True, comment="Numéro SIRET de l'entreprise"
    )
    vat_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        unique=True,
        comment="Numéro de TVA intracommunautaire",
    )

    customer = relationship("Customers", back_populates="pro", uselist=False)

    def __repr__(self) -> str:
        return (
            f"<CustomerPro(id={self.id}, customer_id={self.customer_id}, "
            f"company_name={self.company_name})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerPro en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "company_name": self.company_name,
            "siret_number": self.siret_number,
            "vat_number": self.vat_number,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerPros":
        """Crée un objet CustomerPro à partir d'un dictionnaire."""
        return cls(
            customer_id=data.get("customer_id", 0),
            company_name=data.get("company_name", ""),
            siret_number=data.get("siret_number"),
            vat_number=data.get("vat_number"),
        )
