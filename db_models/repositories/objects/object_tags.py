"""Module de gestion de la liaison entre les objets généraux et les tags associés."""

from typing import Any, Dict, Optional, List
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import ObjectTags

class ObjectTagsRepository(BaseRepository):
    """Repository pour la gestion des tags liés aux objets généraux."""
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.model = ObjectTags
        self._kwargs = tuple(column.name for column in self.model.__table__.columns)

    def create(self, object_tag_data: Dict[str, Any]) -> ObjectTags:
        """
        Crée une nouvelle liaison entre un objet général et un tag."""
        # Levée d'une exception si des champs diffèrent des champs attendus pour une liaison
        extra_keys = set(object_tag_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")
        # Création de la liaison
        new_object_tag = ObjectTags(**object_tag_data)
        try:
            self.session.add(new_object_tag)
            self.session.flush()
            return new_object_tag
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la création de la liaison : {str(e)}") from e

    def create_list(self, object_tag_data_list: List[Dict[str, Any]]) -> List[ObjectTags]:
        """Crée une liste de liaisons entre des objets généraux et des tags."""
        object_tags: List[ObjectTags] = []
        for object_tag_data in object_tag_data_list:
            object_tags.append(self.create(object_tag_data))
        return object_tags

    def update_one(self, update_data: Dict[str, Any], object_tag: Optional[ObjectTags]=None,
                   object_tag_id: Optional[int]=None) -> ObjectTags:
        """Mise à jour d'une liaison existante."""
        # Vérification des champs attendus pour la mise à jour d'une liaison
        if set(update_data.keys()) - set(self._kwargs):
            extra_keys = set(update_data.keys()) - set(self._kwargs)
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")
        # Récupération de la liaison à mettre à jour
        if object_tag_id is None and object_tag is None:
            raise ValueError("Fournir un identifiant ou un objet pour la mise à jour.")
        if object_tag is None:
            object_tag = self.session.query(self.model).filter_by(id=object_tag_id).first()
        if not object_tag:
            raise ValueError(f"Liaison avec id {object_tag_id} non trouvée.")
        # Mise à jour des champs de la liaison
        for key, value in update_data.items():
            setattr(object_tag, key, value)
        try:
            self.session.flush()
            return object_tag
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la mise à jour de la liaison : {str(e)}") from e

    def update_list(self, update_data_list: List[Dict[str, Any]],
                    object_tag_ids: Optional[List[int]] = None,
                    object_tags: Optional[List[ObjectTags]] = None) -> List[ObjectTags]:
        """Mise à jour d'une liste de liaisons existantes."""
        object_tags_return: List[ObjectTags] = object_tags or []
        for update_data in update_data_list:
            data_id = update_data.get("id")
            if data_id is None:
                raise ValueError("Manque le champ 'id' de la liaison à mettre à jour.")
            selected_object_tag_id = next((oid for oid in object_tag_ids if oid == data_id), None) \
                                        if object_tag_ids else None
            selected_object_tag = next(
                              (ot for ot in object_tags if ot.id == selected_object_tag_id), None) \
                                        if object_tags else None
            object_tags_return.append(self.update_one(update_data, object_tag=selected_object_tag,
                                                      object_tag_id=selected_object_tag_id))
        return object_tags_return
