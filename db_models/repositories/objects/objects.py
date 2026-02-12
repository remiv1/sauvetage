"""
Module pour les dépôts des objets vendus par la librairie. Contient les classes :
    - ObjectsRepository : Contient les méthodes pour interagir avec les données des objets
                          vendus par la librairie.
"""

from typing import Any, Sequence, Optional, Dict, List
from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects.objects import (
    GeneralObjects, Books, OtherObjects, ObjectTags, Metadatas, MediaFiles)
from db_models.repositories.objects import (BooksRepository, OtherObjectsRepository,
                                            MetadatasRepository, ObjectTagsRepository,
                                            MediaRepository)

class ObjectsRepository(BaseRepository):
    """
    Dépôt de données pour les objets vendus par la librairie.
    Contient les méthodes :
    - get_all : pour récupérer tous les objets.
    - get_by_ref : pour récupérer un objet par une référence (id, ean13, etc.).
    - create : pour créer un nouvel objet.
    - update : pour mettre à jour un objet existant.
    - update_complete : pour mettre à jour un objet avec tous ses éléments liés
                        (books, other_objects, metadata, object_tags, media).
    - delete : pour supprimer un objet (soft delete).
    """
    def __init__(self, *args: Any, **kwargs: str) -> None:
        """Initialise le dépôt de données pour les objets vendus par la librairie."""
        super().__init__(*args, **kwargs)
        self.model = GeneralObjects
        self._kwargs = tuple(column.name for column in self.model.__table__.columns)
        self.book_repo = BooksRepository(self.session)
        self.other_object_repo = OtherObjectsRepository(self.session)
        self.metadata_repo = MetadatasRepository(self.session)
        self.object_tags_repo = ObjectTagsRepository(self.session)
        self.media_repo = MediaRepository(self.session)

    def _get_global_select(self):
        """Retourne une requête de base pour les objets, avec tous les éléments liés."""
        return (select(self.model).where(self.model.is_active == True)   # pylint: disable=singleton-comparison
                .options(joinedload(self.model.supplier),
                         joinedload(self.model.books),
                         joinedload(self.model.other_objects),
                         joinedload(self.model.inventory_movements),
                         joinedload(self.model.metadata),
                         joinedload(self.model.object_tags)))

    def get_all(self) -> Sequence["GeneralObjects"]:
        """
        Récupère tous les objets actifs avec tous les éléments liés :
        (supplier, books, other_objects, inventory_movements, metadata, object_tags).
        Returns:
            List[GeneralObjects]: Une liste de tous les objets actifs avec leurs éléments liés.
        """
        stmt = self._get_global_select()

        return self.session.execute(stmt).unique().scalars().all()

    def get_by_ref(self, reference: str | int) -> "GeneralObjects":
        """Récupère un objet par une référence (id ou ean13)."""
        stmt = self._get_global_select().where(or_(
            self.model.id == reference, self.model.ean13 == reference))
        return self.session.execute(stmt).scalar_one_or_none()

    def create_object(self, **kwargs: Any) -> "GeneralObjects":
        """
        Crée un nouvel objet général.
        Les champs requis pour créer un objet général sont :
        (supplier_id, general_object_type, ean13, name, description, price)
        """
        # Levée d'une exception si des champs requis sont manquants
        if not all(k in kwargs for k in self._kwargs):
            raise ValueError(f"Tous les champs sont nécessaires : {', '.join(self._kwargs)}")

        # Création de l'objet général avec les champs requis
        general_object = GeneralObjects(**kwargs)

        # Ajout de l'objet à la session et flush pour obtenir l'id généré
        try:
            self.session.add(general_object)
            self.session.flush()
            return general_object
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Error creating object: {str(e)}") from e

    def create_object_complete(self, *, general_object: GeneralObjects,
                               book: Optional[Books]=None,
                               other_object: Optional[OtherObjects]=None,
                               object_tags: Optional[List[ObjectTags]]=None,
                               metadata: Optional[List[Metadatas]]=None,
                               media: Optional[List[MediaFiles]]=None) -> GeneralObjects:
        """
        Crée un nouvel objet avec tous ses éléments liés
        (books, other_objects, metadata, object_tags, media).
        """
        try:
            if book:
                general_object = self.create_object(**book.to_dict())
            if other_object:
                other_object.general_object_id = general_object.id
                self.other_object_repo.create(other_object.to_dict())
            if object_tags:
                for ot in object_tags:
                    ot.general_object_id = general_object.id
                self.object_tags_repo.create_list([ot.to_dict() for ot in object_tags])
            if metadata:
                for m in metadata:
                    m.general_object_id = general_object.id
                self.metadata_repo.create_list([m.to_dict() for m in metadata])
            if media:
                for m in media:
                    m.general_object_id = general_object.id
                general_object.media_files.extend(media)
            self.session.add(general_object)
            self.session.flush()
            return general_object
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Error creating complete object: {str(e)}") from e

    def commit_object(self) -> None:
        """
        Commit les changements liés à un objet (création, mise à jour, suppression).
        En cas d'erreur lors du commit, la transaction est rollbackée et une exception est levée.
        """
        try:
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Error committing object changes: {str(e)}") from e

    def update_object(self, *, update_payload: Dict[str, Any],
                      general_object: Optional[GeneralObjects] = None,
                      id_object: Optional[int] = None):
        """
        Met à jour un objet existant.
        Passer en arguments soit l'id de l'objet à mettre à jour, soit l'objet lui-même.
        Les champs à mettre à jour sont passés en arguments dans le payload.
        format du payload :
            ```json
            update_payload = {
                "general": {"name": "Nouveau titre", "price": 12.9},
                "book": {"author": "X", "pages": 320},
                "other_object": {"some_field": "val"},
                "metadata": {"semistructured_data": {...}},
                "object_tags": ["tag1", "tag2"],
                "media": [
                    {"metadata_id": 1, "file_name": "cover.jpg", "is_principal": True},
                ],
            }
            ```
        """
        # Levée d'une exception si le payloadde mise à jour est manquant
        if not update_payload:
            raise ValueError("update_payload must be provided for update.")
        general_object = self._resolve_general_object(general_object, id_object)

        if "general" in update_payload:
            self.update(general_object, update_payload["general"])
        if "book" in update_payload:
            self.book_repo.update(update_payload["book"], book=general_object.books)
        if "other_object" in update_payload:
            self.other_object_repo.update(update_payload["other_object"],
                                          other_object=general_object.other_objects)
        if "metadata" in update_payload:
            self.metadata_repo.update_list([update_payload["metadata"]],
                                           metadatas=general_object.metadata)
        if "object_tags" in update_payload:
            self.object_tags_repo.update_list(update_payload["object_tags"],
                                              object_tags=general_object.object_tags)
        if "media" in update_payload:
            self.media_repo.update_list(update_payload["media"], medias=general_object.media_files)

        self.session.commit()

    def update(self, general_object: GeneralObjects, general_payload: Dict[str, Any]):
        """
        Met à jour les champs généraux d'un objet.
        Les champs généraux d'un objet sont :
        - supplier_id,
        - general_object_type,
        - ean13,
        - name,
        - description,
        - price
        """
        for key, value in general_payload.items():
            setattr(general_object, key, value)

    def _resolve_general_object(self,
                                general_object: Optional[GeneralObjects],
                                id_object: Optional[int]) -> GeneralObjects:
        """Cherche et retourne l'objet complet s'il n'est pas fourni."""
        if general_object is None and id_object is not None:
            general_object = self.get_by_ref(id_object)
        if general_object is None:
            raise ValueError("Mentionnez l'objet ou son identifiant pour la mise à jour.")
        return general_object

    def delete(self, object_id: int):
        """Supprime un objet (soft delete)."""
        obj = self.get_by_ref(object_id)
        if not obj:
            raise ValueError(f"Object with id {object_id} not found.")
        obj.is_active = False
        self.session.commit()
