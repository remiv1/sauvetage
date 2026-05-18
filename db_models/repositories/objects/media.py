"""Module de gestion des médias d'objets."""

import os
import logging
from typing import Any, Dict, Optional, List, Sequence
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import MediaFiles
from db_models.services.pictures import read_upload_from_entry, save_picture_to_disk

logger = logging.getLogger(__name__)

class MediaRepository(BaseRepository):
    """
    Module de gestion des médias liés aux objets généraux.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.model = MediaFiles
        self._kwargs = tuple(column.name for column in self.model.__table__.columns)

    def get_all(self, general_object_id: Optional[int] = None) -> Sequence[MediaFiles]:
        """Récupère tous les médias, ou ceux liés à un objet général spécifique."""
        stmt = select(MediaFiles)
        if general_object_id is not None:
            stmt = stmt.filter_by(general_object_id=general_object_id)
        return self.session.execute(stmt).scalars().all()

    def create(self, media_data: Dict[str, Any]) -> MediaFiles:
        """Création d'un objet média à partir des données fournies."""
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

    def update_one(
        self,
        media_data: Dict[str, Any],
        media: Optional[MediaFiles] = None,
        media_id: Optional[int] = None,
    ) -> MediaFiles:
        """Mise à jour d'un média existant avec les données fournies."""
        # Vérification des champs attendus pour la mise à jour d'un média
        extra_keys = set(media_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")

        # Récupération du média à mettre à jour
        if media_id is None and media is None:
            raise ValueError("Fournir un identifiant ou un objet pour la mise à jour.")
        if media is None:
            stmt = select(self.model).where(self.model.id == media_id)
            media = self.session.execute(stmt).scalars().first()
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
            raise ValueError(
                f"Erreur lors de la mise à jour du média : {str(e)}"
            ) from e

    def update_list(
        self,
        media_data_list: List[Dict[str, Any]],
        media_ids: Optional[List[int]] = None,
        medias: Optional[List[MediaFiles]] = None,
    ) -> List[MediaFiles]:
        """Mise à jour d'une liste de médias existants."""
        medias_return: List[MediaFiles] = []
        for media_data in media_data_list:
            data_id = media_data.get("id")
            if data_id is None:
                raise ValueError(
                    "Chaque média à mettre à jour doit avoir un champ 'id'."
                )
            selected_media_id = (
                next((mid for mid in media_ids if mid == data_id), None)
                if media_ids
                else None
            )
            selected_media = (
                next((m for m in medias if m.id == selected_media_id), None)
                if medias
                else None
            )
            medias_return.append(
                self.update_one(
                    media_data, media=selected_media, media_id=selected_media_id
                )
            )
        return medias_return

    def save_from_form(
        self,
        form: Any,
        general_object_id: int,
        parent_instance: Optional[Any] = None,
    ) -> None:
        """
        Synchronise les médias d'un objet à partir des données du formulaire.
        - Si un fichier est uploadé (FileField non vide), le sauvegarde sur le
          volume partagé et stocke son nom dans file_link (is_local=True).
        - Sinon, si file_link est rempli, le stocke tel quel (is_local=False).
        - Supprime les médias non présents dans le formulaire.

        Le répertoire de dépôt est lu depuis la variable d'env MEDIA_UPLOAD_DIR.
        """
        upload_dir = os.environ.get("MEDIA_UPLOAD_DIR", "")
        existing = {
            str(obj.id): obj
            for obj in getattr(parent_instance, "media_files", [])
        }
        received_ids: set = set()
        collection = getattr(parent_instance, "media_files")

        for entry in form.media_files:
            obj, entry_id = self._get_or_create_media(
                entry, existing, general_object_id, collection
            )
            if entry_id:
                received_ids.add(entry_id)
            self._apply_scalar_fields(obj, entry)
            self._apply_file_or_link(obj, entry, upload_dir)

        self._delete_removed(existing, received_ids, collection)

        try:
            self.session.flush()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la sauvegarde des médias : {str(e)}") from e

    # ------------------------------------------------------------------
    # Méthodes privées
    # ------------------------------------------------------------------

    def _get_or_create_media(
        self,
        entry: Any,
        existing: Dict[str, Any],
        general_object_id: int,
        collection: Any,
    ) -> tuple:
        """Retourne (objet MediaFiles, entry_id) en créant l'objet si nécessaire."""
        id_field = entry._fields.get("id")
        entry_id = id_field.data if id_field else None
        if entry_id and entry_id in existing:
            return existing[entry_id], entry_id
        obj = MediaFiles()
        obj.general_object_id = general_object_id
        collection.append(obj)
        return obj, None

    @staticmethod
    def _apply_scalar_fields(obj: Any, entry: Any) -> None:
        """Copie les champs texte simples du formulaire vers l'objet."""
        obj.file_name = entry._fields["file_name"].data or ""
        obj.file_type = entry._fields["file_type"].data or ""
        alt_field = entry._fields.get("alt_text")
        obj.alt_text = alt_field.data if alt_field else None

    def _apply_file_or_link(self, obj: Any, entry: Any, upload_dir: str) -> None:
        """Définit file_link et is_local selon le contenu uploadé ou l'URL saisie."""
        content, original_filename = read_upload_from_entry(entry)
        if not original_filename:
            raise ValueError("Le champ de fichier doit avoir un nom de fichier original.")
        if content and upload_dir:
            obj.file_link = save_picture_to_disk(content, original_filename, upload_dir)
            obj.is_local = True
            return
        link_field = entry._fields.get("file_link")
        link_value = link_field.data if link_field else None
        if link_value:
            obj.file_link = link_value
            obj.is_local = False

    def _delete_removed(
        self, existing: Dict[str, Any], received_ids: set, collection: Any
    ) -> None:
        """Supprime les médias présents en base mais absents du formulaire.

        Si le média est stocké localement (is_local=True), le fichier physique
        est également supprimé du volume partagé.
        """
        upload_dir = os.environ.get("MEDIA_UPLOAD_DIR", "")
        for obj_id, obj in existing.items():
            if obj_id not in received_ids:
                if obj.is_local and obj.file_link and upload_dir:
                    file_path = os.path.join(upload_dir, obj.file_link)
                    try:
                        os.remove(file_path)
                    except OSError:
                        logger.warning("Impossible de supprimer le fichier local : %s", file_path)
                collection.remove(obj)
                self.session.delete(obj)
