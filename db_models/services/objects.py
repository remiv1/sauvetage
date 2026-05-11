"""
Fonctions utilitaires pour synchroniser les collections d'objets liés à un GeneralObject
(ex: tags, métadonnées, médias) à partir des données d'un formulaire WTForms.

Ce module implémente le pattern de synchronisation pour les relations 1→N bidirectionnelles,
permettant de maintenir la cohérence entre les données de formulaire WTForms et les objets
SQLAlchemy persistants en base de données.
"""

from typing import Any, Iterable, Type
from db_models.objects import GeneralObjects


def sync_collection(
    parent: GeneralObjects,
    general_object_id: int,
    attr_name: str,
    form_fieldlist: Iterable,
    model_class: Type[Any],
    session: Any,
) -> None:
    """
    Synchronise une relation 1→N entre un parent SQLAlchemy et une FieldList WTForms.
    """
    existing = {str(obj.id): obj for obj in getattr(parent, attr_name)}
    received_ids = set()
    collection = getattr(parent, attr_name)

    # 1. Mise à jour + création
    for entry in form_fieldlist:
        # entry.id est une propriété WTForms qui retourne l'id HTML — on passe par _fields
        id_field = entry._fields.get("id")
        entry_id = id_field.data if id_field else None

        if entry_id and entry_id in existing:
            obj = existing[entry_id]
            received_ids.add(entry_id)
        else:
            obj = model_class()
            obj.general_object_id = general_object_id
            collection.append(obj)

        for name, field in entry._fields.items():
            if name not in ("id", "csrf_token", "file_data"):
                setattr(obj, name, field.data)

    # 2. Suppression des objets non retournés
    for obj_id, obj in existing.items():
        if obj_id not in received_ids:
            collection.remove(obj)
            session.delete(obj)
