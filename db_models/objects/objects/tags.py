"""Modèles des tags et de leur association aux objets."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, mapped_column, Mapped
from db_models import WorkingBase
from ..common import QueryMixin
from .object_constants import CASCADE_OPTIONS, GENERAL_OBJECT_PK, DESCRIPTION_FK


class Tags(WorkingBase, QueryMixin):
    """
    Modèle pour les tags associés aux objets.
    Un tag peut être associé à plusieurs objets, et un objet peut avoir plusieurs tags.
    """

    __tablename__ = "tags"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique du tag",
    )
    wpwc_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        unique=True,
        comment="Identifiant du tag dans WooCommerce (si synchronisé)",
    )
    name: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, comment="Nom du tag"
    )
    description: Mapped[str] = mapped_column(String, comment="Description du tag")
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Indique si le tag est actif"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création du tag",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière MàJ du tag",
    )

    object_tags = relationship(
        "ObjectTags", back_populates="tag", cascade=CASCADE_OPTIONS
    )

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name={self.name})>"

    def to_dict(self, is_woo_commerce: bool = False) -> Dict[str, Any]:
        """Convertit l'objet Tag en dictionnaire."""
        if is_woo_commerce:
            return {"id": self.wpwc_id}
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tags":
        """Crée un objet Tag à partir d'un dictionnaire."""
        return cls(**data)


class ObjectTags(WorkingBase, QueryMixin):
    """Modèle pour l'association entre les objets et les tags."""

    __tablename__ = "object_tags"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique de l'association objet-tag",
    )
    general_object_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(GENERAL_OBJECT_PK),
        nullable=False,
        comment=DESCRIPTION_FK,
    )
    tag_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.tags.id"),
        nullable=False,
        comment="Identifiant du tag associé",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création de l'association",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière MàJ de l'association",
    )

    general_object = relationship("GeneralObjects", back_populates="object_tags")
    tag = relationship("Tags", back_populates="object_tags")

    def __repr__(self) -> str:
        return (
            f"<ObjectTag(id={self.id}, general_object_id={self.general_object_id}, "
            f"tag_id={self.tag_id})>"
        )

    def to_dict_for_woo_commerce(self) -> Dict[str, Optional[int]]:
        """Convertit l'objet ObjectTag en dictionnaire formaté pour WooCommerce."""
        return {"id": self.tag.wpwc_id}

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet ObjectTag en dictionnaire."""
        return {
            "id": self.id,
            "general_object_id": self.general_object_id,
            "tag_id": self.tag_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObjectTags":
        """Crée un objet ObjectTag à partir d'un dictionnaire."""
        return cls(**data)
