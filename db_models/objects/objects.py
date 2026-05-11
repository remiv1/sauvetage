"""Module contenant les modèles pour les objets mise en vente."""

from datetime import datetime, timezone
from typing import Any, Dict
from typing import Optional
from sqlalchemy import (
    Integer,
    String,
    Numeric,
    DateTime,
    ForeignKey,
    JSON,
    Boolean,
)
from sqlalchemy.orm import relationship, mapped_column, Mapped
from db_models import WorkingBase
from db_models.objects import QueryMixin
from db_models.services.utils import slugify

CASCADE_OPTIONS = "all, delete-orphan"
GENERAL_OBJECT_PK = "app_schema.general_objects.id"


class GeneralObjects(WorkingBase, QueryMixin):
    """
    Modèle pour les objets généraux mis en vente.
    
    Attributs :
    - id : Identifiant unique de l'objet (clé primaire)
    - id_wpwc : Identifiant de l'objet dans WooCommerce (nullable, unique)
    - supplier_id : Identifiant du fournisseur de l'objet (clé étrangère vers suppliers.id)
    - general_object_type : Type d'objet (ex: book, other)
    - ean13 : Code EAN13 de l'objet (unique, non nullable)
    - name : Nom de l'objet (non nullable)
    - description : Description de l'objet (nullable)
    - price : Prix de l'objet (non nullable, valeur par défaut = 0.0)
    - purchase_price : Prix d'achat de l'objet (nullable, valeur par défaut = 0.0)
    - vat_rate_id : Code TVA associé à l'objet (nullable, référence la table vat_rates)
    - created_at : Date de création de l'objet
    - updated_at : Date de dernière mise à jour de l'objet
    - last_inventory_timestamp : Dernier inventaire
    - is_active : Indique si l'objet est actif pour la vente
    """

    __tablename__ = "general_objects"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique de l'objet",
    )
    id_wpwc: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        unique=True,
        comment="Identifiant de l'objet dans WooCommerce (si synchronisé)",
    )

    # Données de base
    supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.suppliers.id"),
        nullable=False,
        comment="Identifiant du fournisseur de l'objet",
    )
    general_object_type: Mapped[str] = mapped_column(
        String, nullable=False, comment="Type d'objet"
    )
    ean13: Mapped[str] = mapped_column(
        String, unique=True, nullable=False,
        comment="Code EAN13 de l'objet"
    )
    name: Mapped[str] = mapped_column(String, nullable=False, comment="Nom de l'objet")
    description: Mapped[str] = mapped_column(String, comment="Description de l'objet")
    price: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0.0,
        comment="Prix de l'objet"
    )
    purchase_price: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=True, default=0.0,
        comment="Prix d'achat de l'objet"
    )
    vat_rate_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("app_schema.vat_rates.id"),
        nullable=True,
        comment="Code TVA associé à l'objet (référence la table vat_rates)",
    )

    # Méta-données de suivi
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
    last_inventory_timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Dernier inventaire",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Indique si l'objet est actif pour la vente"
    )

    # Relations
    supplier = relationship("Suppliers", back_populates="objects")
    vat_rate = relationship("VatRate", back_populates="general_objects")
    book = relationship(
        "Books",
        uselist=False,
        back_populates="general_object",
        cascade=CASCADE_OPTIONS
    )
    other_object = relationship(
        "OtherObjects",
        uselist=False,
        back_populates="general_object",
        cascade=CASCADE_OPTIONS,
    )
    inventory_movements = relationship(
        "InventoryMovements", back_populates="general_object", cascade=CASCADE_OPTIONS
    )
    obj_metadatas = relationship(
        "ObjMetadatas", back_populates="general_object", cascade=CASCADE_OPTIONS, uselist=False
    )
    object_tags = relationship(
        "ObjectTags", back_populates="general_object", cascade=CASCADE_OPTIONS
    )
    media_files = relationship(
        "MediaFiles", back_populates="general_object", cascade=CASCADE_OPTIONS
    )
    order_lines = relationship(
        "OrderLine", back_populates="general_object", cascade=CASCADE_OPTIONS
    )
    orderin_lines = relationship(
        "OrderInLine", back_populates="general_object", cascade=CASCADE_OPTIONS
    )
    dilicom_referencial = relationship(
        "DilicomReferencial",
        uselist=False,
        back_populates="general_object",
        cascade=CASCADE_OPTIONS,
    )

    def __repr__(self) -> str:
        return (
            f"<GeneralObject(id={self.id}, supplier_id={self.supplier_id}, "
            f"general_object_type={self.general_object_type}, ean13={self.ean13}, "
            f"name={self.name}, price={self.price})>"
        )

    def to_dict(self, is_woo_commerce: bool = False) -> Dict[str, Any]:
        """Convertit l'objet GeneralObject en dictionnaire."""
        if is_woo_commerce:
            value_dict: dict[str, Any] = {
                "name": self.name,
                "slug": slugify(self.name),
                "type": "simple",
                "status": "publish" if self.is_active else "draft",
                "description": self.description,
                "sku": self.id,
                "global_unique_id": self.ean13,
                "regular_price": str(self.price),
                "sale_price": str(self.price) if self.price > 0 else None,
                "tax_class": self.vat_rate.name if self.vat_rate else None,
            }
        else:
            value_dict = {
                "id": self.id,
                "supplier_id": self.supplier_id,
                "general_object_type": self.general_object_type,
                "ean13": self.ean13,
                "name": self.name,
                "description": self.description,
                "price": self.price,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "last_inventory_timestamp": (
                    self.last_inventory_timestamp.isoformat()
                    if self.last_inventory_timestamp
                    else None
                ),
                "is_active": self.is_active,
            }
        return value_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeneralObjects":
        """Crée un objet GeneralObject à partir d'un dictionnaire."""
        return cls(**data)


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

    # Données spécifiques aux livres
    author: Mapped[str] = mapped_column(String, nullable=True, comment="Auteur du livre")
    diffuser: Mapped[str] = mapped_column(String, nullable=True, comment="Diffuseur du livre")
    editor: Mapped[str] = mapped_column(String, nullable=True, comment="Éditeur du livre")
    genre: Mapped[str] = mapped_column(String, nullable=True, comment="Genre du livre")
    publication_year: Mapped[int] = mapped_column(
        Integer, nullable=True, comment="Année de publication du livre"
    )
    pages: Mapped[int] = mapped_column(Integer, nullable=True, comment="Nombre de pages du livre")

    # Meta-données de suivi
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

    # Relations
    general_object = relationship("GeneralObjects", back_populates="book")

    def __repr__(self) -> str:
        return f"<Book(id={self.id})>"

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

    # Meta-données de suivi
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
    # Relations
    general_object = relationship("GeneralObjects", back_populates="other_object")

    def __repr__(self) -> str:
        return f"<OtherObject(id={self.id})>"

    def to_dict(self, is_woo_commerce: bool = False) -> Dict[str, Any]:
        """Convertit l'objet OtherObject en dictionnaire."""
        if is_woo_commerce:
            value_dict = {}
        else:
            value_dict = {
                "id": self.id,
                "general_object_id": self.general_object_id,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }
        return value_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OtherObjects":
        """Crée un objet OtherObject à partir d'un dictionnaire."""
        return cls(**data)


class Tags(WorkingBase, QueryMixin):
    """
    Modèle pour les tags associés aux objets.
    Un tag peut être associé à plusieurs objets, et un objet peut avoir plusieurs tags.
    
    Attributs :
    - id : Identifiant unique du tag (clé primaire)
    - id_wpwc : Identifiant du tag dans WooCommerce (nullable, unique)
    - name : Nom du tag (unique, non nullable)
    - description : Description du tag (nullable)
    - created_at : Date de création du tag (non nullable, valeur par défaut = date actuelle)
    - updated_at : Date de dernière mise à jour du tag (non nullable,
                    valeur par défaut = date actuelle,
                    mise à jour automatique à chaque modification)
    - object_tags : Relation vers les associations entre objets et tags
                    (relation bidirectionnelle avec ObjectTags)
    """

    __tablename__ = "tags"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique du tag",
    )
    id_wpwc: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        unique=True,
        comment="Identifiant du tag dans WooCommerce (si synchronisé)",
    )
    name: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, comment="Nom du tag"
    )
    description: Mapped[str] = mapped_column(String, comment="Description du tag")

    # Meta-données de suivi
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

    # Relations
    object_tags = relationship(
        "ObjectTags", back_populates="tag", cascade=CASCADE_OPTIONS
    )

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name={self.name})>"

    def to_dict(self, is_woo_commerce: bool = False) -> Dict[str, Any]:
        """Convertit l'objet Tag en dictionnaire."""
        if is_woo_commerce:
            value_dict = {
                "id": self.id_wpwc,
            }
        else:
            value_dict = {
                "id": self.id,
                "name": self.name,
                "description": self.description,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }
        return value_dict

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
        comment="Identifiant de l'objet général associé",
    )
    tag_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.tags.id"),
        nullable=False,
        comment="Identifiant du tag associé",
    )

    # Meta-données de suivi
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

    # Relations
    general_object = relationship("GeneralObjects", back_populates="object_tags")
    tag = relationship("Tags", back_populates="object_tags")

    def __repr__(self) -> str:
        return (
            f"<ObjectTag(id={self.id}, general_object_id={self.general_object_id}, "
            f"tag_id={self.tag_id})>"
        )

    def to_dict(self, is_woo_commerce: bool = False) -> Dict[str, Any]:
        """Convertit l'objet ObjectTag en dictionnaire."""
        if is_woo_commerce:
            value_dict = {
                "id": self.tag.id_wpwc,
            }
        else:
            value_dict = {
                "id": self.id,
                "general_object_id": self.general_object_id,
                "tag_id": self.tag_id,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }
        return value_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObjectTags":
        """Crée un objet ObjectTag à partir d'un dictionnaire."""
        return cls(**data)


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
        comment="Identifiant de l'objet général associé",
    )

    # Données semi-structurées au format JSON
    semistructured_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON, comment="Données au format JSON"
    )

    # Meta-données de suivi
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

    # Relations
    general_object = relationship("GeneralObjects", back_populates="obj_metadatas")

    def __repr__(self) -> str:
        return (
            f"<ObjMetadata(id={self.id}, general_object_id={self.general_object_id})>"
        )

    def to_dict(self, is_woo_commerce: bool = False) -> Optional[dict[str, Any]]:
        """Convertit l'objet ObjMetadata en dictionnaire."""
        if is_woo_commerce:
            value_dict = {
                "meta_data": [{k: v} for k, v in self.semistructured_data.items()]
                } if self.semistructured_data else None
        else:
            value_dict = {
                "id": self.id,
                "general_object_id": self.general_object_id,
                "semistructured_data": self.semistructured_data,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }
        return value_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObjMetadatas":
        """Crée un objet ObjMetadata à partir d'un dictionnaire."""
        return cls(**data)


class MediaFiles(WorkingBase, QueryMixin):
    """Modèle pour les fichiers médias associés aux métadonnées."""

    __tablename__ = "media_files"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique du fichier média",
    )
    id_wpwc: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        unique=True,
        comment="Identifiant du fichier média dans WooCommerce (si synchronisé)",
    )
    general_object_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(GENERAL_OBJECT_PK),
        nullable=False,
        comment="Identifiant de la métadonnée associée",
    )
    file_name: Mapped[str] = mapped_column(
        String, nullable=False, comment="Nom du fichier média"
    )
    file_type: Mapped[str] = mapped_column(
        String, nullable=False, comment="Type du fichier média (ex: image/jpeg)"
    )
    alt_text: Mapped[str] = mapped_column(
        String, nullable=True, comment="Texte alternatif pour le fichier média"
    )
    file_link: Mapped[str] = mapped_column(
        String,
        nullable=True,
        comment="Lien vers le fichier média (URL externe ou nom de fichier local)"
    )
    is_local: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Indique si le fichier est stocké localement sur le volume"
    )

    # Meta-données de suivi
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de téléchargement du fichier média",
    )
    is_principal: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Indique si c'est l'image principale"
    )

    # Relations
    general_object = relationship("GeneralObjects", back_populates="media_files")

    def __repr__(self) -> str:
        return (
            f"<MediaFile(id={self.id}, general_object_id={self.general_object_id}, "
            f"file_name={self.file_name})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet MediaFile en dictionnaire."""
        return {
            "id": self.id,
            "general_object_id": self.general_object_id,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "alt_text": self.alt_text,
            "file_link": self.file_link,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "is_principal": self.is_principal,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MediaFiles":
        """Crée un objet MediaFile à partir d'un dictionnaire."""
        return cls(**data)


class ObjectSyncLog(WorkingBase):
    """Journal de synchronisation WooCommerce pour les objets, tags, images et TVA."""

    __tablename__ = "object_sync_logs"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Type d'entité synchronisée
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type d'entité : object, tag, picture, vat_rate",
    )
    # ID local de l'entité dans la base (nullable pour flexibilité)
    entity_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="ID local de l'entité dans la base de données",
    )
    # ID de l'entité dans le système externe (peut être absent en cas d'erreur)
    external_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="ID de l'entité dans le système externe (ex : WooCommerce)",
    )
    # Système externe concerné
    external_system: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Système externe : wpwc, henrri, …",
    )
    # Direction de la synchronisation
    sync_direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Direction : inbound, outbound",
    )

    # Opération effectuée
    operation: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Opération : create, update, delete, batch",
    )

    # Résultat de la synchronisation
    sync_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Statut : success, error",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        comment="Message d'erreur en cas d'échec",
    )

    # Horodatage
    synced_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date et heure de la synchronisation",
    )

    def __repr__(self) -> str:
        return (
            f"<ObjectSyncLog(id={self.id}, entity_type={self.entity_type}, "
            f"entity_id={self.entity_id}, external_system={self.external_system}, "
            f"operation={self.operation}, sync_status={self.sync_status})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet ObjectSyncLog en dictionnaire."""
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "external_id": self.external_id,
            "external_system": self.external_system,
            "sync_direction": self.sync_direction,
            "operation": self.operation,
            "sync_status": self.sync_status,
            "error_message": self.error_message,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }


class MediaAccessToken(WorkingBase):
    """Jeton d'accès temporaire permettant à WooCommerce de télécharger une image.

    Chaque jeton est à usage unique et expire 1 heure après sa création.
    Le champ ``token`` est le nom du fichier (UUID.webp) stocké sur le volume,
    ce qui permet à WooCommerce de l'enregistrer sous ce même nom.
    """

    __tablename__ = "media_access_tokens"
    __table_args__ = {"schema": "app_schema"}

    token: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        comment="Nom du fichier image (UUID.webp) — sert d'identifiant de jeton",
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de création du jeton",
    )
    valid_until: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Date d'expiration du jeton (valid_from + 1 heure)",
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Date de consommation du jeton (None = pas encore utilisé)",
    )

    def __repr__(self) -> str:
        return (
            f"<MediaAccessToken(token={self.token}, valid_until={self.valid_until}, "
            f"used_at={self.used_at})>"
        )

    def is_valid(self) -> bool:
        """Retourne True si le jeton est utilisable : non consommé et non expiré."""
        now = datetime.now(timezone.utc)
        valid_until = self.valid_until
        if valid_until.tzinfo is None:
            valid_until = valid_until.replace(tzinfo=timezone.utc)
        return self.used_at is None and now <= valid_until
