"""Modèle des adresses clients."""

from __future__ import annotations

from typing import Any
from datetime import datetime, timezone
from sqlalchemy.orm import mapped_column, relationship, Mapped
from sqlalchemy import Integer, String, DateTime, Boolean, ForeignKey
from db_models import WorkingBase
from db_models.objects.common import QueryMixin
from db_models.objects.customers.constants import CUSTOMER_PK


class CustomerAddresses(WorkingBase, QueryMixin):
    """Modèle des adresses clients."""

    __tablename__ = "customer_addresses"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="Identifiant unique"
    )
    henrri_id: Mapped[int] = mapped_column(
        Integer, nullable=True, comment="Identifiant HENRRI associé"
    )
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(CUSTOMER_PK),
        nullable=False,
        comment="Identifiant du client associé",
    )
    address_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Nom d'adresse (ex: home, work)"
    )
    address_line1: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Ligne d'adresse 1"
    )
    address_line2: Mapped[str] = mapped_column(
        String(200), nullable=True, comment="Ligne d'adresse 2"
    )
    city: Mapped[str] = mapped_column(String(100), nullable=False, comment="Ville")
    state: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="État/Région"
    )
    postal_code: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Code postal"
    )
    country: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Pays", default="France"
    )
    is_billing: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Indique si c'est une adresse de facturation",
    )
    is_shipping: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Indique si c'est une adresse de livraison",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Indique si l'adresse est active ou supprimée",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création de l'adresse",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière mise à jour",
    )

    customer = relationship("Customers", back_populates="addresses")

    def __repr__(self) -> str:
        return (
            f"<CustomerAddress(id={self.id}, customer_id={self.customer_id}, "
            f"address_name={self.address_name}, address_line1={self.address_line1}, "
            f"address_line2={self.address_line2}, city={self.city}, country={self.country})>"
        )

    def __hash__(self) -> int:
        return hash((
            self.customer_id,
            self.address_name,
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.postal_code,
            self.country,
        ))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CustomerAddresses):
            return False
        return (
            self.customer_id == other.customer_id
            and self.address_name == other.address_name
            and self.address_line1 == other.address_line1
            and self.address_line2 == other.address_line2
            and self.city == other.city
            and self.state == other.state
            and self.postal_code == other.postal_code
            and self.country == other.country
        )

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet CustomerAddress en dictionnaire."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "address_name": self.address_name,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "is_active": self.is_active,
            "is_billing": self.is_billing,
            "is_shipping": self.is_shipping,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_dict_henrri(self) -> dict[str, Any]:
        """Convertit l'objet CustomerAddress en dictionnaire Henrri."""
        return {
            "id": self.henrri_id,
            "address": self.address_line1 + "\n" + self.address_line2,
            "city": self.city,
            "post_code": self.postal_code,
            "is_post_code_shared": True,
            "country": self.country,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomerAddresses":
        """Crée un objet CustomerAddress à partir d'un dictionnaire."""
        return cls(
            customer_id=data.get("customer_id", 0),
            address_name=data.get("address_name"),
            address_line1=data.get("address_line1", ""),
            address_line2=data.get("address_line2", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            postal_code=data.get("postal_code", ""),
            country=data.get("country", ""),
            is_billing=data.get("is_billing", True),
            is_shipping=data.get("is_shipping", False),
        )
