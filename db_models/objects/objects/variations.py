"""Modèle des variations d'objets."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import Integer, String, Numeric, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, mapped_column, Mapped
from db_models import WorkingBase
from ..common import QueryMixin
from .object_constants import GENERAL_OBJECT_PK, DESCRIPTION_FK


class ObjectVariations(WorkingBase, QueryMixin):
    """
    Modèle pour les variations d'un objet général.
    Une variation partage les tags, images et métadonnées de son parent (GeneralObjects).
    La gestion des stocks se fait uniquement sur l'objet parent.

    Attributs :
    - id : Identifiant unique de la variation (clé primaire)
    - wpwc_id : Identifiant de la variation dans WooCommerce (nullable, unique)
    - general_object_id : FK vers l'objet parent (general_objects.id)
    - name : Nom de la variation
    - description : Description spécifique à la variation (nullable)
    - price : Prix de la variation
    - purchase_price : Prix d'achat de la variation (nullable)
    - created_at : Date de création
    - updated_at : Date de dernière mise à jour
    - is_active : Indique si la variation est active pour la vente
    """

    __tablename__ = "object_variations"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique de la variation d'objet",
    )
    wpwc_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        unique=True,
        comment="Identifiant de l'objet dans WooCommerce (si synchronisé)",
    )
    general_object_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(GENERAL_OBJECT_PK),
        nullable=False,
        comment=DESCRIPTION_FK,
    )
    name: Mapped[str] = mapped_column(String, nullable=False, comment="Nom de l'objet")
    description: Mapped[str] = mapped_column(String, comment="Description de l'objet")
    price: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0.0,
        comment="Prix de l'objet"
    )
    purchase_price: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True, default=0.0,
        comment="Prix d'achat de l'objet"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création de l'objet",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière mise à jour de l'objet",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Indique si l'objet est actif pour la vente"
    )

    general_object = relationship(
        "GeneralObjects",
        back_populates="object_variations",
        uselist=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ObjectVariations(id={self.id}, g_o_id={self.general_object_id}, "
            f"name={self.name}, price={self.price})>"
        )

    def to_dict_for_woo_commerce(self) -> Dict[str, Any]:
        """Convertit l'objet ObjectVariations en dictionnaire formaté pour WooCommerce."""
        return {
            "name": self.name,
            "description": self.description,
            "sku": self.id,
            "regular_price": str(self.price),
            "sale_price": str(self.price) if self.price > 0 else None,
            "manage_stock": "parent",
            "backorders": "notify",
        }

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet ObjectVariations en dictionnaire."""
        return {
            "id": self.id,
            "general_object_id": self.general_object_id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "purchase_price": self.purchase_price,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObjectVariations":
        """Crée un objet ObjectVariations à partir d'un dictionnaire."""
        return cls(**data)
