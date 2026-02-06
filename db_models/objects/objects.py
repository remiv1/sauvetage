"""Module contenant les modèles pour les objets mise en vente."""

from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, JSON, LargeBinary, Boolean
from sqlalchemy.orm import relationship, mapped_column, Mapped
from db_models import WorkingBase
from db_models.objects import QueryMixin

CASCADE_OPTIONS = "all, delete-orphan"
GENERAL_OBJECT_PK = "general_objects.id"
METADATA_PK = "metadatas.id"

class GeneralObjects(WorkingBase, QueryMixin):
    """Modèle pour les objets généraux mis en vente."""
    __tablename__ = 'general_objects'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant unique de l'objet")

    # Données de base
    supplier_id: Mapped[int] = mapped_column(Integer, ForeignKey('suppliers.id'), nullable=False,
                                            comment="Identifiant du fournisseur de l'objet")
    general_object_type: Mapped[str] = mapped_column(String, nullable=False, comment="Type d'objet")
    ean13: Mapped[str] = mapped_column(String, comment="Code EAN13 de l'objet")
    name: Mapped[str] = mapped_column(String, nullable=False, comment="Nom de l'objet")
    description: Mapped[str] = mapped_column(String, comment="Description de l'objet")
    price: Mapped[float] = mapped_column(Float, nullable=False, comment="Prix de l'objet")

    # Méta-données de suivi
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                        default=lambda: datetime.now(timezone.utc),
                                        comment="Date de création de l'objet")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc),
                                                 comment="Date de dernière mise à jour de l'objet")
    last_inventory_timestamp: Mapped[datetime] = mapped_column(DateTime,
                                                               comment="Dernier inventaire")

    # Relations
    supplier = relationship("Suppliers", back_populates="objects")
    books = relationship("Books", back_populates="general_object", cascade=CASCADE_OPTIONS)
    other_objects = relationship("OtherObjects", back_populates="general_object",
                                 cascade=CASCADE_OPTIONS)
    inventory_movements = relationship("InventoryMovements", back_populates="general_object",
                                    cascade=CASCADE_OPTIONS)
    metadata = relationship("Metadatas", back_populates="general_object",
                            cascade=CASCADE_OPTIONS)
    object_tags = relationship("ObjectTags", back_populates="general_object",
                               cascade=CASCADE_OPTIONS)

    def __repr__(self) -> str:
        return f"<GeneralObject(id={self.id}, supplier_id={self.supplier_id}, " \
               f"general_object_type={self.general_object_type}, ean13={self.ean13}, " \
               f"name={self.name}, price={self.price})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet GeneralObject en dictionnaire."""
        return {
            "id": self.id,
            "supplier_id": self.supplier_id,
            "general_object_type": self.general_object_type,
            "ean13": self.ean13,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_inventory_timestamp": self.last_inventory_timestamp.isoformat() \
                                        if self.last_inventory_timestamp else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeneralObjects":
        """Crée un objet GeneralObject à partir d'un dictionnaire."""
        return cls(
            supplier_id=data.get("supplier_id", 0),
            general_object_type=data.get("general_object_type", ""),
            ean13=data.get("ean13"),
            name=data.get("name", ""),
            description=data.get("description"),
            price=data.get("price", 0.0)
        )

class Books(WorkingBase, QueryMixin):
    """Modèle pour les livres mis en vente."""
    __tablename__ = 'books'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant unique du livre")
    general_object_id: Mapped[int] = mapped_column(Integer, ForeignKey(GENERAL_OBJECT_PK),
                                                   nullable=False,
                                                   comment="Identifiant objet associé")

    # Données spécifiques aux livres
    author: Mapped[str] = mapped_column(String, comment="Auteur du livre")
    publisher: Mapped[str] = mapped_column(String, comment="Éditeur du livre")
    diffuser: Mapped[str] = mapped_column(String, comment="Diffuseur du livre")
    editor: Mapped[str] = mapped_column(String, comment="Éditeur du livre")
    genre: Mapped[str] = mapped_column(String, comment="Genre du livre")
    publication_year: Mapped[int] = mapped_column(Integer, comment="Année de publication du livre")
    pages: Mapped[int] = mapped_column(Integer, comment="Nombre de pages du livre")

    # Meta-données de suivi
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 comment="Date de création du livre")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc),
                                                 comment="Date de dernière mise à jour du livre")

    # Relations
    general_object = relationship("GeneralObject", back_populates="book")

    def __repr__(self) -> str:
        return f"<Book(id={self.id})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet Book en dictionnaire."""
        return {
            "id": self.id,
            "general_object_id": self.general_object_id,
            "author": self.author,
            "publisher": self.publisher,
            "diffuser": self.diffuser,
            "editor": self.editor,
            "genre": self.genre,
            "publication_year": self.publication_year,
            "pages": self.pages,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Books":
        """Crée un objet Book à partir d'un dictionnaire."""
        return cls(
            general_object_id=data.get("general_object_id", 0),
            author=data.get("author"),
            publisher=data.get("publisher"),
            diffuser=data.get("diffuser"),
            editor=data.get("editor"),
            genre=data.get("genre"),
            publication_year=data.get("publication_year"),
            pages=data.get("pages")
        )

class OtherObjects(WorkingBase, QueryMixin):
    """Modèle pour les autres objets mis en vente."""
    __tablename__ = 'other_objects'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant unique de l'autre objet")
    general_object_id: Mapped[int] = mapped_column(Integer, ForeignKey(GENERAL_OBJECT_PK),
                                                   nullable=False,
                                                   comment="Id de l'objet général associé")

    # Meta-données de suivi
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 comment="Date de création de l'objet autre")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc),
                                                 comment="Date de dernière MàJ de l'objet autre")
    # Relations
    general_object = relationship("GeneralObject", back_populates="other_objects")

    def __repr__(self) -> str:
        return f"<OtherObject(id={self.id})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet OtherObject en dictionnaire."""
        return {
            "id": self.id,
            "general_object_id": self.general_object_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OtherObjects":
        """Crée un objet OtherObject à partir d'un dictionnaire."""
        return cls(
            general_object_id=data.get("general_object_id", 0)
        )

class Tags(WorkingBase, QueryMixin):
    """Modèle pour les tags associés aux objets."""
    __tablename__ = 'tags'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant unique du tag")
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True,
                                     comment="Nom du tag")
    description: Mapped[str] = mapped_column(String, comment="Description du tag")

    # Meta-données de suivi
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 comment="Date de création du tag")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc),
                                                 comment="Date de dernière MàJ du tag")

    # Relations
    object_tags = relationship("ObjectTags", back_populates="tag", cascade=CASCADE_OPTIONS)

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name={self.name})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet Tag en dictionnaire."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tags":
        """Crée un objet Tag à partir d'un dictionnaire."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description")
        )

class ObjectTags(WorkingBase, QueryMixin):
    """Modèle pour l'association entre les objets et les tags."""
    __tablename__ = 'object_tags'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant unique de l'association objet-tag")
    general_object_id: Mapped[int] = mapped_column(Integer, ForeignKey(GENERAL_OBJECT_PK),
                                                   nullable=False,
                                                   comment="Identifiant de l'objet général associé")
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey('tags.id'), nullable=False,
                                        comment="Identifiant du tag associé")

    # Meta-données de suivi
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 comment="Date de création de l'association")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc),
                                                 comment="Date de dernière MàJ de l'association")

    # Relations
    general_object = relationship("GeneralObject", back_populates="object_tags")
    tag = relationship("Tags", back_populates="object_tags")

    def __repr__(self) -> str:
        return f"<ObjectTag(id={self.id}, general_object_id={self.general_object_id}, " \
               f"tag_id={self.tag_id})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet ObjectTag en dictionnaire."""
        return {
            "id": self.id,
            "general_object_id": self.general_object_id,
            "tag_id": self.tag_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObjectTags":
        """Crée un objet ObjectTag à partir d'un dictionnaire."""
        return cls(
            general_object_id=data.get("general_object_id"),
            tag_id=data.get("tag_id")
        )

class Metadatas(WorkingBase, QueryMixin):
    """Modèle pour les métadonnées associées aux objets."""
    __tablename__ = 'metadatas'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant unique de la métadonnée")
    general_object_id: Mapped[int] = mapped_column(Integer, ForeignKey(GENERAL_OBJECT_PK),
                                                   comment="Identifiant de l'objet général associé")

    # Données semi-structurées au format JSON
    semistructured_data: Mapped[JSON] = mapped_column(JSON, comment="Données au format JSON")

    # Meta-données de suivi
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 comment="Date de création de la métadonnée")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc),
                                                 comment="Date de dernière MàJ de la métadonnée")

    # Relations
    general_object = relationship("GeneralObject", back_populates="metadata")
    media_files = relationship("MediaFiles", back_populates="metadata", cascade=CASCADE_OPTIONS)

    def __repr__(self) -> str:
        return f"<Metadata(id={self.id}, general_object_id={self.general_object_id})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet Metadata en dictionnaire."""
        return {
            "id": self.id,
            "general_object_id": self.general_object_id,
            "semistructured_data": self.semistructured_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Metadatas":
        """Crée un objet Metadata à partir d'un dictionnaire."""
        return cls(
            general_object_id=data.get("general_object_id"),
            semistructured_data=data.get("semistructured_data")
        )

class MediaFiles(WorkingBase, QueryMixin):
    """Modèle pour les fichiers médias associés aux métadonnées."""
    __tablename__ = 'media_files'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                    comment="Identifiant unique du fichier média")
    metadata_id: Mapped[int] = mapped_column(Integer, ForeignKey(METADATA_PK),
                                            nullable=False,
                                            comment="Identifiant de la métadonnée associée")
    file_name: Mapped[str] = mapped_column(String, nullable=False, comment="Nom du fichier média")
    file_type: Mapped[str] = mapped_column(String, comment="Type du fichier média (ex: image/jpeg)")
    alt_text: Mapped[str] = mapped_column(String, comment="Texte alternatif pour le fichier média")
    file_data: Mapped[bytes] = mapped_column(LargeBinary, comment="Données brutes du fichier média")

    # Meta-données de suivi
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc),
                                                 comment="Date de téléchargement du fichier média")
    is_principal: Mapped[bool] = mapped_column(Boolean, default=False,
                                            comment="Indique si c'est l'image principale")

    # Relations
    metadata = relationship("Metadatas", back_populates="media_files")
