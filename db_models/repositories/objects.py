"""
Module pour les dépôts des objets vendus par la librairie. Contient les classes :
    - ObjectsRepository : Contient les méthodes pour interagir avec les données des objets
                          vendus par la librairie.
"""

import json
from typing import Any, Sequence, Optional, Dict
from sqlalchemy import select, or_  # Ajout de l'import pour or_
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects.objects import (GeneralObjects, Books, OtherObjects, Metadatas, ObjectTags,
                                       MediaFiles, Tags)

class ObjectsRepository(BaseRepository):
    """
    Dépôt de données pour les objets vendus par la librairie.
    Contient les méthodes :
    - get_all : pour récupérer tous les objets.
    - get_by_ref : pour récupérer un objet par une référence (id, ean13, etc.).
    - get_by_spec : pour récupérer des objets par une spécificité (tags, genre, etc.).
    - get_by_type : pour récupérer les objets d'un type spécifique (DVD, CD, jeu, etc.).
    - get_price_range : pour récupérer des objets dans une fourchette de prix.
    - create : pour créer un nouvel objet.
    - update : pour mettre à jour un objet existant.
    - delete : pour supprimer un objet (soft delete).
    """
    def __init__(self, *args: Any, **kwargs: str) -> None:
        """Initialise le dépôt de données pour les objets vendus par la librairie."""
        super().__init__(*args, **kwargs)
        self.model = GeneralObjects

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
        - supplier
        - books
        - other_objects
        - inventory_movements
        - metadata
        - object_tags
        Returns:
            List[GeneralObjects]: Une liste de tous les objets actifs avec leurs éléments liés.
        """
        stmt = self._get_global_select()

        return self.session.execute(stmt).scalars().all()

    def get_by_ref(self, reference: str | int) -> "GeneralObjects":
        """Récupère un objet par une référence (id, ean13, etc.)."""
        stmt = self._get_global_select().where(or_(
            self.model.id == reference, self.model.ean13 == reference))
        return self.session.execute(stmt).scalar_one_or_none()

    def create_object(self, **kwargs: str) -> "GeneralObjects":
        """Crée un nouvel objet général."""

        # Levée d'une exception si des champs requis sont manquants
        _kwargs = ('supplier_id', 'general_object_type', 'ean13', 'name', 'description', 'price')
        if not all(k in kwargs for k in _kwargs):
            raise ValueError(f"Missing required fields: {', '.join(_kwargs)}")

        # Création de l'objet général avec les champs requis
        general_object = GeneralObjects(
            supplier_id=kwargs['supplier_id'],
            general_object_type=kwargs['general_object_type'],
            ean13=kwargs['ean13'],
            name=kwargs['name'],
            description=kwargs['description'],
            price=kwargs['price']
        )

        # Ajout de l'objet à la session et flush pour obtenir l'id généré
        try:
            self.session.add(general_object)
            self.session.flush()
            return general_object
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Error creating object: {str(e)}") from e

    def create_book(self, **kwargs: str) -> "Books":
        """Crée un nouvel objet de type livre."""

        # Levée d'une exception si des champs diffèrent des champs attendus pour un livre
        _kwargs = ('general_object_id', 'author', 'publisher', 'diffuser', 'editor', 'genre',
                   'publication_year', 'pages')
        extra_keys = set(kwargs) - set(_kwargs)
        if extra_keys:
            raise ValueError(f"Unexpected fields for book: {', '.join(sorted(extra_keys))}")

        # Création de l'objet livre avec les champs spécifiques aux livres
        book = Books(
            general_object_id=kwargs['general_object_id'],
            author=kwargs['author'],
            publisher=kwargs['publisher'],
            diffuser=kwargs['diffuser'],
            editor=kwargs['editor'],
            genre=kwargs['genre'],
            publication_year=kwargs['publication_year'],
            pages=kwargs['pages']
        )

        # Ajout de l'objet livre à la session et flush pour obtenir l'id généré
        try:
            self.session.add(book)
            self.session.flush()
            return book
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Error creating book: {str(e)}") from e

    def create_other_object(self, **kwargs: str) -> "OtherObjects":
        """Crée un nouvel objet de type autre (DVD, CD, jeu, etc.)."""
        # Levée d'une exception si des champs diffèrent des champs attendus pour un autre objet
        _kwargs = ('general_object_id',)
        extra_keys = set(kwargs) - set(_kwargs)
        if extra_keys:
            raise ValueError(f"Unexpected fields for other object: {', '.join(sorted(extra_keys))}")

        # Création de l'objet autre avec les champs spécifiques aux autres objets
        other_object = OtherObjects(
            general_object_id=kwargs['general_object_id']
        )

        # Ajout de l'objet autre à la session et flush pour obtenir l'id généré
        try:
            self.session.add(other_object)
            self.session.flush()
            return other_object
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Error creating other object: {str(e)}") from e

    def create_metadata(self, **kwargs: str) -> "Metadatas":
        """Crée une nouvelle métadonnée pour un objet."""
        # Levée d'une exception si des champs diffèrent des champs attendus pour une métadonnée
        _kwargs = ('general_object_id', 'semistructured_data')
        extra_keys = set(kwargs) - set(_kwargs)
        if extra_keys:
            raise ValueError(f"Unexpected fields for metadata: {', '.join(sorted(extra_keys))}")

        # Création de la métadonnée avec les champs spécifiques aux métadonnées
        data = json.dumps(kwargs['semistructured_data'])  # Convertit le dict en JSON string
        metadata = Metadatas(
            general_object_id=kwargs['general_object_id'],
            semistructured_data=data
        )

        # Ajout de la métadonnée à la session et flush pour obtenir l'id généré
        try:
            self.session.add(metadata)
            self.session.flush()
            return metadata
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Error creating metadata: {str(e)}") from e

    def create_object_tag(self, **kwargs: Any) -> "ObjectTags":
        """Crée les associations entre un objet et ses tags."""
        # Levée d'une exception si des champs supplémentaires sont passés en arguments
        _kwargs = ('general_object_id', 'tag_id')
        extra_keys = set(kwargs) - set(_kwargs)
        if extra_keys:
            raise ValueError(f"Unexpected fields for object tag: {', '.join(sorted(extra_keys))}")

        # Création de l'association entre l'objet et le tag
        object_tag = ObjectTags(
            general_object_id=kwargs['general_object_id'],
            tag_id=kwargs['tag_id']
        )

        # Ajout de l'association à la session et flush pour obtenir l'id généré
        try:
            self.session.add(object_tag)
            self.session.flush()
            return object_tag
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Error creating object tag: {str(e)}") from e

    def create_medias(self, **kwargs: str) -> "MediaFiles":
        """Crée les associations entre un objet et ses médias (images, vidéos, etc.)."""
        # Levée d'une exception si des champs supplémentaires sont passés en arguments
        _kwargs = ('metadata_id', 'file_name', 'file_type', 'alt_text',
                   'file_data', 'file_link', 'is_principal')
        extra_keys = set(kwargs) - set(_kwargs)
        if extra_keys:
            raise ValueError(f"Unexpected fields for media: {', '.join(sorted(extra_keys))}")

        # Création du média avec les champs spécifiques aux médias
        media = MediaFiles(
            metadata_id=kwargs.get('metadata_id'),
            file_name=kwargs.get('file_name'),
            file_type=kwargs.get('file_type', None),
            alt_text=kwargs.get('alt_text', None),
            file_data=kwargs.get('file_data', None),
            file_link=kwargs.get('file_link', None),
            is_principal=kwargs.get('is_principal', False)
        )

        # Ajout du média à la session et flush pour obtenir l'id généré
        try:
            self.session.add(media)
            self.session.flush()
            return media
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Error creating media: {str(e)}") from e

    def create_tag(self, **kwargs: str) -> "Tags":
        """Crée un nouveau tag."""
        # Levée d'une exception si des champs diffèrent des champs attendus pour un tag
        _kwargs = ('name', 'description')
        extra_keys = set(kwargs) - set(_kwargs)
        if extra_keys:
            raise ValueError(f"Unexpected fields for tag: {', '.join(sorted(extra_keys))}")

        # Création du tag avec les champs spécifiques aux tags
        tag = Tags(
            name=kwargs['name'],
            description=kwargs['description']
        )

        # Ajout du tag à la session et flush pour obtenir l'id généré
        try:
            self.session.add(tag)
            self.session.flush()
            return tag
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Error creating tag: {str(e)}") from e

    def commit_object(self) -> None:
        """Commit les changements liés à un objet (création, mise à jour, suppression)."""
        try:
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Error committing object changes: {str(e)}") from e

    def _resolve_general_object(self,
                                general_object: Optional[GeneralObjects],
                                id_object: Optional[int]) -> GeneralObjects:
        if general_object is None and id_object is not None:
            general_object = self.get_by_ref(id_object)
        if general_object is None:
            raise ValueError("Either general_object or id_object must be provided for update.")
        return general_object

    @staticmethod
    def _get_first_related(items: Sequence[Any]) -> Any | None:
        return items[0] if items else None

    @staticmethod
    def _apply_updates(target: Any, updates: Dict[str, Any]) -> None:
        for key, value in updates.items():
            setattr(target, key, value)

    def _apply_related_updates(self, related_items: Sequence[Any], updates: Dict[str, Any]) -> None:
        related = self._get_first_related(related_items)
        if related is None:
            return
        self._apply_updates(related, updates)

    def _apply_metadata_updates(self, related_items: Sequence[Any],
                                updates: Dict[str, Any]) -> None:
        related = self._get_first_related(related_items)
        if related is None:
            return
        for key, value in updates.items():
            if key == "semistructured_data":
                value = json.dumps(value)
            setattr(related, key, value)

    def _replace_tags(self, general_object: GeneralObjects, tag_names: Sequence[str]) -> None:
        general_object.object_tags.clear()
        for tag_name in tag_names:
            tag = self.session.query(Tags).filter_by(name=tag_name).first()
            if not tag:
                tag = self.create_tag(name=tag_name, description="")
            self.create_object_tag(general_object_id=general_object.id, tag_id=tag.id)

    def _replace_media(self, general_object: GeneralObjects,
                       media_items: Sequence[Dict[str, Any]]) -> None:
        for metadata in general_object.metadata:
            self.session.query(MediaFiles).filter_by(metadata_id=metadata.id).delete()
        for media_data in media_items:
            self.create_medias(**media_data)

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
                "tags": ["tag1", "tag2"],
                "media": [
                    {"metadata_id": 1, "file_name": "cover.jpg", "is_principal": True},
                ],
            }
            ```
        """
        if not update_payload:
            raise ValueError("update_payload must be provided for update.")
        general_object = self._resolve_general_object(general_object, id_object)

        update_general = update_payload.get("general")
        if update_general:
            self._apply_updates(general_object, update_general)

        update_book = update_payload.get("book", None)
        update_other_object = update_payload.get("other_object", None)
        update_metadata = update_payload.get("metadata", None)
        update_tags = update_payload.get("tags", None)
        update_media = update_payload.get("media", None)

        if update_book:
            self._apply_related_updates(general_object.books, update_book)
        if update_other_object:
            self._apply_related_updates(general_object.other_objects, update_other_object)
        if update_metadata:
            self._apply_metadata_updates(general_object.metadata, update_metadata)
        if update_tags is not None:
            self._replace_tags(general_object, update_tags)
        if update_media is not None:
            self._replace_media(general_object, update_media)

        self.session.commit()

    def delete(self, object_id: int):
        """Supprime un objet (soft delete)."""
        obj = self.get_by_ref(object_id)
        if not obj:
            raise ValueError(f"Object with id {object_id} not found.")
        obj.is_active = False
        self.session.commit()
