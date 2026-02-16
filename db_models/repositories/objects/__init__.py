"""Génération de dépôts pour les objets généraux et leurs métadonnées associées."""

from .books import BooksRepository  # type: ignore
from .objects import ObjectsRepository  # type: ignore
from .other_objects import OtherObjectsRepository # type: ignore
from .obj_metadatas import ObjMetadatasRepository  # type: ignore
from .object_tags import ObjectTagsRepository # type: ignore
from .media import MediaRepository # type: ignore
