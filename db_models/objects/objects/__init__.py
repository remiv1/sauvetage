"""Package contenant les modèles d'objets découpés par domaine."""

from .books import Books
from .general_objects import GeneralObjects, ObjectPrices
from .media import MediaAccessToken, MediaFiles
from .metadatas import ObjMetadatas
from .other_objects import OtherObjects
from .sync_logs import ObjectSyncLog
from .tags import ObjectTags, Tags
from .variations import ObjectVariations

__all__ = [
    "GeneralObjects",
    "ObjectPrices",
    "ObjectVariations",
    "Books",
    "OtherObjects",
    "Tags",
    "ObjectTags",
    "ObjMetadatas",
    "MediaFiles",
    "ObjectSyncLog",
    "MediaAccessToken",
]
