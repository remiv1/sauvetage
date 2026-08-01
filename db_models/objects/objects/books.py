"""Modèle des livres."""

from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, mapped_column, Mapped
from db_models import WorkingBase
from ..common import QueryMixin
from .object_constants import GENERAL_OBJECT_PK


class Books(WorkingBase, QueryMixin):
    """
    Modèle pour les livres mis en vente.
    Attributs :
    - id : Identifiant unique du livre (clé primaire)
    - general_object_id : Identifiant de l'objet général associé
    - author : Auteur du livre
    - diffuser : Distributeur du livre
    - editor : Éditeur du livre
    - genre : Genre du livre
    - publication_year : Année de publication du livre
    - pages : Nombre de pages du livre
    - created_at : Date de création du livre
    - updated_at : Date de dernière mise à jour du livre
    """

    __tablename__ = "books"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique du livre",
    )
    general_object_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(GENERAL_OBJECT_PK),
        nullable=False,
        comment="Identifiant objet associé",
    )
    author: Mapped[str] = mapped_column(String, nullable=True, comment="Auteur du livre")
    diffuser: Mapped[str] = mapped_column(String, nullable=True, comment="Diffuseur du livre")
    editor: Mapped[str] = mapped_column(String, nullable=True, comment="Éditeur du livre")
    genre: Mapped[str] = mapped_column(String, nullable=True, comment="Genre du livre")
    publication_year: Mapped[int] = mapped_column(
        Integer, nullable=True, comment="Année de publication du livre"
    )
    pages: Mapped[int] = mapped_column(Integer, nullable=True, comment="Nombre de pages du livre")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création du livre",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Date de dernière mise à jour du livre",
    )

    general_object = relationship("GeneralObjects", back_populates="book")

    def __repr__(self) -> str:
        return f"<Book(id={self.id})>"

    def to_dict_for_woo_commerce(self) -> Dict[str, Any]:
        """Convertit l'objet Book en dictionnaire formaté pour WooCommerce."""
        return {
            "attributes": [
                {
                    "name": "Auteur",
                    "options": [self.author] if self.author else [],
                    "visible": True,
                    "position": 0,
                    "slug": "auteur",
                },
                {
                    "name": "Éditeur",
                    "options": [self.editor] if self.editor else [],
                    "visible": True,
                    "position": 1,
                    "slug": "editeur",
                },
                {
                    "name": "Genre",
                    "options": [self.genre] if self.genre else [],
                    "visible": True,
                    "position": 2,
                    "slug": "genre",
                },
                {
                    "name": "Année de publication",
                    "options": [self.publication_year] if self.publication_year else [],
                    "visible": True,
                    "position": 3,
                    "slug": "annee-de-publication",
                },
                {
                    "name": "Nombre de pages",
                    "options": [self.pages] if self.pages else [],
                    "visible": True,
                    "position": 4,
                    "slug": "nombre-de-pages",
                },
            ]
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet Book en dictionnaire."""
        return {
            "id": self.id,
            "general_object_id": self.general_object_id,
            "author": self.author,
            "diffuser": self.diffuser,
            "editor": self.editor,
            "genre": self.genre,
            "publication_year": self.publication_year,
            "pages": self.pages,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Books":
        """Crée un objet Book à partir d'un dictionnaire."""
        return cls(**data)
