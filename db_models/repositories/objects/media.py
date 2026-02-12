"""Module de gestion des médias d'objets."""

from typing import Any, Dict, Optional, List
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects.objects import MediaFiles

class MediaRepository(BaseRepository):
    """Module de gestion des médias liés aux objets généraux."""
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.model = MediaFiles
        self._kwargs = tuple(column.name for column in self.model.__table__.columns)

    def create(self, media_data: Dict[str, Any]) -> MediaFiles:
        """Création d'un objet média à partir des données fournies. """
        extra_keys = set(media_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")
        new_media = MediaFiles(**media_data)
        try:
            self.session.add(new_media)
            self.session.flush()
            return new_media
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la création du média : {str(e)}") from e

    def create_list(self, media_data_list: List[Dict[str, Any]]) -> List[MediaFiles]:
        """Crée une liste de médias à partir d'une liste de dictionnaires de données."""
        medias: List[MediaFiles] = []
        for media_data in media_data_list:
            medias.append(self.create(media_data))
        return medias

    def update_one(self, media_data: Dict[str, Any], media: Optional[MediaFiles]=None,
               media_id: Optional[int]=None) -> MediaFiles:
        """Mise à jour d'un média existant avec les données fournies."""
        # Vérification des champs attendus pour la mise à jour d'un média
        extra_keys = set(media_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")

        # Récupération du média à mettre à jour
        if media_id is None and media is None:
            raise ValueError("Fournir un identifiant ou un objet pour la mise à jour.")
        if media is None:
            media = self.session.query(self.model).filter_by(id=media_id).first()
            if not media:
                raise ValueError(f"Média avec id {media_id} non trouvé.")

        # Mise à jour des champs du média
        for key, value in media_data.items():
            setattr(media, key, value)
        try:
            self.session.flush()
            return media
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la mise à jour du média : {str(e)}") from e

    def update_list(self, media_data_list: List[Dict[str, Any]],
                    media_ids: Optional[List[int]] = None,
                    medias: Optional[List[MediaFiles]] = None) -> List[MediaFiles]:
        """Mise à jour d'une liste de médias existants."""
        medias_return: List[MediaFiles] = []
        for media_data in media_data_list:
            data_id = media_data.get("id")
            if data_id is None :
                raise ValueError("Chaque média à mettre à jour doit avoir un champ 'id'.")
            selected_media_id = next((mid for mid in media_ids if mid == data_id), None) \
                                    if media_ids else None
            selected_media = next((m for m in medias if m.id == selected_media_id), None) \
                                    if medias else None
            medias_return.append(self.update_one(media_data, media=selected_media,
                                                 media_id=selected_media_id))
        return medias_return
