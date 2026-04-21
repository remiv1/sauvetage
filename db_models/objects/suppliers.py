"""Module de définition du modèle de données pour les fournisseurs."""

from typing import Dict, Any
from datetime import datetime, timezone
from sqlalchemy import Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship, mapped_column, Mapped
from db_models import WorkingBase


class Suppliers(WorkingBase):
    """Modèle pour les fournisseurs."""

    __tablename__ = "suppliers"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique du fournisseur",
    )

    # Données de base du fournisseur
    name: Mapped[str] = mapped_column(
        String, nullable=False, comment="Nom du fournisseur"
    )
    gln13: Mapped[str] = mapped_column(
        String, unique=True, comment="Code GLN du fournisseur"
    )
    siren_siret: Mapped[str] = mapped_column(
        String, nullable=True, comment="Numéro SIREN ou SIRET du fournisseur"
    )
    vat_number: Mapped[str] = mapped_column(
        String, unique=True, nullable=True, comment="Numéro de TVA intracom fournisseur"
    )
    address: Mapped[str] = mapped_column(
        String, nullable=True, comment="Adresse complète du fournisseur"
    )
    contact_email: Mapped[str] = mapped_column(
        String, nullable=True, comment="Email de contact du fournisseur"
    )
    contact_phone: Mapped[str] = mapped_column(
        String, nullable=True, comment="Téléphone de contact du fournisseur"
    )
    contact_fax: Mapped[str] = mapped_column(
        String, nullable=True, comment="Fax de contact du fournisseur"
    )
    web_site: Mapped[str] = mapped_column(
        String, nullable=True, comment="Site web du fournisseur"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Indique si le fournisseur est actif"
    )
    edi_active: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Indique si le fournisseur est actif pour l'EDI"
    )
    collect_days: Mapped[str] = mapped_column(
        String, nullable=True, comment="Jours de collecte des commandes (ex: '12345' pour LMMJV)"
    )
    cutoff_time: Mapped[str] = mapped_column(
        String, nullable=True, comment="Heure limite de PEC des commandes pour le jour même."
    )

    # Méta-données de suivi
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création du fournisseur",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière MàJ du fournisseur",
    )

    # Relations
    objects = relationship("GeneralObjects", back_populates="supplier")
    orderin = relationship("OrderIn", back_populates="supplier")
    dilicom_referencial = relationship("DilicomReferencial", back_populates="supplier")

    def __repr__(self) -> str:
        return (
            f"<Supplier(id={self.id}, name={self.name}, contact_email={self.contact_email}, "
            f"contact_phone={self.contact_phone}, is_active={self.is_active})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet Supplier en dictionnaire."""
        return {
            "id": self.id,
            "name": self.name,
            "gln13": self.gln13,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Suppliers":
        """Crée un objet Supplier à partir d'un dictionnaire."""
        return cls(**data)
