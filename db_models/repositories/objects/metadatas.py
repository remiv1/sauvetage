"""
Module pour la gestion des métadonnées des objets généraux.
Ce module contient la classe `MetadatasRepository` qui fournit des méthodes pour créer et mettre
à jour les métadonnées associées aux objets généraux.
"""

import json
from typing import Any, Dict, Optional, List
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects.objects import Metadatas

class MetadatasRepository(BaseRepository):
    """
    Dépôt des données pour la gestion des métadonnées des objets généraux.
    """
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.model = Metadatas
        # Récupération dynamique des colonnes du modèle
        self._kwargs = tuple(column.name for column in self.model.__table__.columns)

    def create(self, metadata_data: Dict[str, Any]):
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
        extra_keys = set(metadata_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")

        # Création de l'objet Métadatas avec les champs spécifiques aux métadonnées
        metadata = self.model(**metadata_data)
        try:
            self.session.add(metadata)
            self.session.flush()
            return metadata
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la création de la métadonnée : {str(e)}") from e

    def create_list(self, metadata_data_list: List[Dict[str, Any]]) -> List[Metadatas]:
        """Crée une liste de métadonnées à partir d'une liste de dictionnaires de données."""
        metadatas: List[Metadatas] = []
        for metadata_data in metadata_data_list:
            metadatas.append(self.create(metadata_data))
        return metadatas

    def update_one(self, update_data: Dict[str, Any], metadata: Optional[Metadatas]=None,
                   metadata_id: Optional[int]=None) -> Metadatas:
        """Mise àjour d'une métadonnée existante."""
        # Vérification des champs attendus pour la mise à jour d'une métadonnée
        extra_keys = set(update_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")

        # Récupération de la métadonnée à mettre à jour
        if metadata_id is None and metadata is None:
            raise ValueError("Fournir un identifiant ou un objet pour la mise à jour.")
        if metadata is None:
            metadata = self.session.query(self.model).filter_by(id=metadata_id).first()
            if not metadata:
                raise ValueError(f"Métadonnée avec id {metadata_id} non trouvée.")

        # Mise à jour des champs pour la métadonnée
        for key, value in update_data.items():
            if key == "semistructured_data":
                # Transformer la valeur en JSON si ce n'est pas déjà une chaîne JSON
                if not isinstance(value, str):
                    value = json.dumps(value)
            setattr(metadata, key, value)
        try:
            self.session.flush()
            return metadata
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la mise à jour des métadonnée : {str(e)}") from e

    def update_list(self, update_data_list: List[Dict[str, Any]],
                    metadata_ids: Optional[List[int]] = None,
                    metadatas: Optional[List[Metadatas]] = None) -> List[Metadatas]:
        """Mise à jour d'une liste de métadonnées existantes."""
        metadatas_return: List[Metadatas] = []
        for update_data in update_data_list:
            data_id = update_data.get("id")
            if data_id is None:
                raise ValueError("Manque le champ 'id' de la métadonnée à mettre à jour.")
            selected_metadata_id = next((mid for mid in metadata_ids if mid == data_id), None) \
                                    if metadata_ids else None
            selected_metadata = next((m for m in metadatas if m.id == selected_metadata_id), None) \
                                    if metadatas else None
            metadatas_return.append(self.update_one(update_data, metadata=selected_metadata,
                                             metadata_id=selected_metadata_id))
        return metadatas_return
