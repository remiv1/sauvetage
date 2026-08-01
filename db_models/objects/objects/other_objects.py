"""Modèle des autres objets."""

from datetime import datetime, timezone
from typing import Dict
from sqlalchemy import Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship, mapped_column, Mapped
from db_models import WorkingBase
from ..common import QueryMixin
from .object_constants import GENERAL_OBJECT_PK


class OtherObjects(WorkingBase, QueryMixin):
    """
    Modèle pour les autres objets mis en vente.
    Attributs :
    - id : Identifiant unique de l'autre objet (clé primaire)
    - general_object_id : Identifiant de l'objet général associé
    - created_at : Date de création de l'objet autre
    - updated_at : Date de dernière mise à jour de l'objet autre
    """

    __tablename__ = "other_objects"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique de l'autre objet",
    )
    general_object_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(GENERAL_OBJECT_PK),
        nullable=False,
        comment="Id de l'objet général associé",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création de l'objet autre",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière MàJ de l'objet autre",
    )

    general_object = relationship("GeneralObjects", back_populates="other_object")

    def __repr__(self) -> str:
        return f"<OtherObject(id={self.id})>"

    def to_dict_for_woo_commerce(self) -> Dict[str, list]:
        """Convertit l'objet OtherObject en dictionnaire formaté pour WooCommerce."""
        return {"attributes": []}

    def to_dict(self, is_woo_commerce: bool = False) -> Dict[str, object]:
        """Convertit l'objet OtherObject en dictionnaire."""
        if is_woo_commerce:
            return {}
        return {
            "id": self.id,
            "general_object_id": self.general_object_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "OtherObjects":
        """Crée un objet OtherObject à partir d'un dictionnaire."""
        return cls(**data)
