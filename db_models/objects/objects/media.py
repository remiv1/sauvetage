"""Modèles des médias liés aux objets."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, mapped_column, Mapped
from db_models import WorkingBase
from ..common import QueryMixin
from .object_constants import GENERAL_OBJECT_PK


class MediaFiles(WorkingBase, QueryMixin):
    """
    Modèle pour les fichiers médias associés aux métadonnées.
    Attributs :
    - id : Identifiant unique du fichier média (clé primaire)
    - wpwc_id : Identifiant du fichier média dans WooCommerce (nullable, unique)
    - general_object_id : Identifiant de la métadonnée associée
    - file_type : Type du fichier média (ex: image/jpeg)
    - alt_text : Texte alternatif pour le fichier média
    - file_link : Lien vers le fichier média (URL externe ou nom de fichier local)
    - is_local : Indique si le fichier est stocké localement sur le volume
    - uploaded_at : Date de téléchargement du fichier média
    - is_principal : Indique si c'est l'image principale
    - general_object : Relation vers l'objet général associé (relation avec GeneralObjects)
    """

    __tablename__ = "media_files"
    __table_args__ = {"schema": "app_schema"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identifiant unique du fichier média",
    )
    wpwc_id: Mapped[Optional[int]] = mapped_column(
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
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Date de téléchargement du fichier média",
    )
    is_principal: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Indique si c'est l'image principale"
    )

    general_object = relationship("GeneralObjects", back_populates="media_files")
    access_tokens = relationship("MediaAccessToken", back_populates="media_file")

    def __repr__(self) -> str:
        return (
            f"<MediaFile(id={self.id}, general_object_id={self.general_object_id}, "
            f"file_link={self.file_link}, is_principal={self.is_principal})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet MediaFile en dictionnaire."""
        return {
            "id": self.id,
            "general_object_id": self.general_object_id,
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


class MediaAccessToken(WorkingBase):
    """Jeton d'accès temporaire permettant à WooCommerce de télécharger une image.

    Le token pointe vers un média local précis via ``media_file_id``.
    Cela évite de dépendre du nom du fichier en tant que clé de sécurité et
    permet de servir le bon fichier même si le token n'est pas identique au
    nom de fichier physique.
    """

    __tablename__ = "media_access_tokens"
    __table_args__ = {"schema": "app_schema"}

    token: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        comment="Jeton de sécurité utilisé dans l'URL publique WooCommerce",
    )
    media_file_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app_schema.media_files.id"),
        nullable=False,
        comment="Média local associé à ce jeton",
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

    media_file = relationship("MediaFiles")

    def __repr__(self) -> str:
        return (
            f"<MediaAccessToken(token={self.token}, media_file_id={self.media_file_id}, "
            f"valid_until={self.valid_until}, used_at={self.used_at})>"
        )

    def is_valid(self) -> bool:
        """Retourne True si le jeton est utilisable : non consommé et non expiré."""
        now = datetime.now(timezone.utc)
        valid_until = self.valid_until
        if valid_until.tzinfo is None:
            valid_until = valid_until.replace(tzinfo=timezone.utc)
        return self.used_at is None and now <= valid_until
