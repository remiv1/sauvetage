"""Modèle des métadonnées d'objets."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, mapped_column, Mapped
from db_models import WorkingBase
from db_models.services.utils import slugify
from ..common import QueryMixin
from .object_constants import GENERAL_OBJECT_PK, DESCRIPTION_FK


class ObjMetadatas(WorkingBase, QueryMixin):
    """Modèle pour les métadonnées associées aux objets."""

    __tablename__ = "obj_metadatas"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique de la métadonnée",
    )
    general_object_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(GENERAL_OBJECT_PK),
        comment=DESCRIPTION_FK,
    )
    semistructured_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON, comment="Données au format JSON"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création de la métadonnée",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière MàJ de la métadonnée",
    )

    general_object = relationship("GeneralObjects", back_populates="obj_metadatas")

    def __repr__(self) -> str:
        return f"<ObjMetadata(id={self.id}, general_object_id={self.general_object_id})>"

    def to_dict_for_woo_commerce(self) -> Optional[dict[str, Any]]:
        """Convertit l'objet ObjMetadata en dictionnaire formaté pour WooCommerce."""
        if not self.semistructured_data:
            return {"attributes": []}

        attributes: list[dict[str, Any]] = []
        for index, (key, value) in enumerate(self.semistructured_data.items()):
            current_values = value if isinstance(value, list) else [value]
            attributes.append(
                {
                    "name": str(key),
                    "options": [str(item) for item in current_values],
                    "visible": True,
                    "position": index,
                    "slug": slugify(str(key)),
                }
            )
        return {"attributes": attributes}

    def to_dict(self) -> Optional[dict[str, Any]]:
        """Convertit l'objet ObjMetadata en dictionnaire."""
        return {
            "id": self.id,
            "general_object_id": self.general_object_id,
            "semistructured_data": self.semistructured_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObjMetadatas":
        """Crée un objet ObjMetadata à partir d'un dictionnaire."""
        return cls(**data)
