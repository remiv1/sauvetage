"""
Module pour la gestion des métadonnées des objets généraux.
Ce module contient la classe `ObjMetadatasRepository` qui fournit des méthodes pour créer et mettre
à jour les métadonnées associées aux objets généraux.
"""

import json
from typing import Any, Dict, Optional, List
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import ObjMetadatas

class ObjMetadatasRepository(BaseRepository):
    """
    Dépôt des données pour la gestion des métadonnées des objets généraux.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.model = ObjMetadatas
        # Récupération dynamique des colonnes du modèle
        self._kwargs = tuple(column.name for column in self.model.__table__.columns)


    def create(self, obj_metadata_data: Dict[str, Any]):
        """
        Création d'une nouvelle métadonnée.
        Les champs requis pour créer une métadonnée sont :
            - general_object_id
            - semistructured_data
        Les champs supplémentaires ne sont pas autorisés et entraîneront une exception.
        La méthode retourne l'objet Métadatas créé.
        En cas d'erreur lors de la création, une exception SQLAlchemyError est levée.
        """
        # Vérification des champs attendus pour la création d'une métadonnée
        extra_keys = set(obj_metadata_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")

        # Création de l'objet Métadatas avec les champs spécifiques aux métadonnées
        obj_metadata = self.model(**obj_metadata_data)
        try:
            self.session.add(obj_metadata)
            self.session.flush()
            return obj_metadata
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la création de la métadonnée : {str(e)}") from e


    def create_list(self, obj_metadata_data_list: List[Dict[str, Any]]) -> List[ObjMetadatas]:
        """Crée une liste de métadonnées à partir d'une liste de dictionnaires de données."""
        obj_metadatas: List[ObjMetadatas] = []
        for obj_metadata_data in obj_metadata_data_list:
            obj_metadatas.append(self.create(obj_metadata_data))
        return obj_metadatas


    def update_one(self, update_data: Dict[str, Any], obj_metadata: Optional[ObjMetadatas]=None,
                   obj_metadata_id: Optional[int]=None) -> ObjMetadatas:
        """Mise àjour d'une métadonnée existante."""
        # Vérification des champs attendus pour la mise à jour d'une métadonnée
        extra_keys = set(update_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")

        # Récupération de la métadonnée à mettre à jour
        if obj_metadata_id is None and obj_metadata is None:
            raise ValueError("Fournir un identifiant ou un objet pour la mise à jour.")
        if obj_metadata is None:
            obj_metadata = self.session.query(self.model).filter_by(id=obj_metadata_id).first()
            if not obj_metadata:
                raise ValueError(f"Métadonnée avec id {obj_metadata_id} non trouvée.")

        # Mise à jour des champs pour la métadonnée
        for key, value in update_data.items():
            if key == "semistructured_data" and isinstance(value, str):
                value = json.loads(value)
            setattr(obj_metadata, key, value)
        try:
            self.session.flush()
            return obj_metadata
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la mise à jour des métadonnée : {str(e)}") from e


    def update_list(self, update_data_list: List[Dict[str, Any]],
                    obj_metadata_ids: Optional[List[int]] = None,
                    obj_metadatas: Optional[List[ObjMetadatas]] = None) -> List[ObjMetadatas]:
        """Mise à jour d'une liste de métadonnées existantes."""
        obj_metadatas_return: List[ObjMetadatas] = []
        for update_data in update_data_list:
            data_id = update_data.get("id")
            if data_id is None:
                raise ValueError("Manque le champ 'id' de la métadonnée à mettre à jour.")
            selected_obj_metadata_id = next((mid for mid in obj_metadata_ids if mid == data_id), None) \
                                    if obj_metadata_ids else None
            selected_obj_metadata = next((m for m in obj_metadatas if m.id == selected_obj_metadata_id), None) \
                                    if obj_metadatas else None
            obj_metadatas_return.append(self.update_one(update_data, obj_metadata=selected_obj_metadata,
                                             obj_metadata_id=selected_obj_metadata_id))
        return obj_metadatas_return


    def save_from_form(self,
                       form: Any,
                       general_object_id: int,
                       instance: Optional[ObjMetadatas] = None) -> ObjMetadatas:
        """
        Sauvegarde une métadonnée à partir d'un formulaire.
        Si instance est fourni, met à jour la métadonnée existante, sinon en crée une nouvelle.
        """
        if instance is None:
            instance = ObjMetadatas()
            self.session.add(instance)
        data = form.data
        items = data.get("items")
        instance.semistructured_data = {
            it["key"]: it.get("value")
            for it in items
            if isinstance(it, dict) and it.get("key")
        }
        instance.general_object_id = general_object_id
        return instance
