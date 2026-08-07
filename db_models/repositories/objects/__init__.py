"""Génération de dépôts pour les objets généraux et leurs métadonnées associées."""

from db_models.objects import (
    GeneralObjects,
    Books,
    OtherObjects,
    ObjMetadatas,
    ObjectTags,
    MediaFiles,
    MediaAccessToken,
    ObjectVariations,
)
from .books import BooksRepository
from .objects import ObjectsRepository
from .other_objects import OtherObjectsRepository
from .obj_metadatas import ObjMetadatasRepository
from .object_tags import ObjectTagsRepository
from .media import MediaRepository
from .media_access_token import MediaAccessTokenRepository
from .prices import PricesRepository
from .variations import VariationsRepository

__all__ = [
    "GeneralObjects",
    "Books",
    "OtherObjects",
    "ObjMetadatas",
    "ObjectTags",
    "MediaFiles",
    "MediaAccessToken",
    "ObjectVariations",
    "BooksRepository",
    "ObjectsRepository",
    "OtherObjectsRepository",
    "ObjMetadatasRepository",
    "ObjectTagsRepository",
    "MediaRepository",
    "MediaAccessTokenRepository",
    "PricesRepository",
    "VariationsRepository",
]
