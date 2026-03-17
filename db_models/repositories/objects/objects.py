"""
Module pour les dépôts des objets vendus par la librairie. Contient les classes :
    - ObjectsRepository : Contient les méthodes pour interagir avec les données des objets
                          vendus par la librairie.
"""

from typing import Any, Sequence, Optional
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import GeneralObjects, ObjectTags



class ObjectsRepository(BaseRepository):
    """
    Dépôt de données pour les objets vendus par la librairie.
    Contient les méthodes :
    - get_all : pour récupérer tous les objets.
    - get_by_ref : pour récupérer un objet par une référence (id, ean13, etc.).
    - create : pour créer un nouvel objet.
    - update : pour mettre à jour un objet existant.
    - update_complete : pour mettre à jour un objet avec tous ses éléments liés
                        (books, other_objects, obj_metadata, object_tags, media).
    - delete : pour supprimer un objet (soft delete).
    """
    def __init__(self, *args: Any, **kwargs: str) -> None:
        """Initialise le dépôt de données pour les objets vendus par la librairie."""
        super().__init__(*args, **kwargs)
        self.model = GeneralObjects
        self._kwargs = tuple(column.name for column in self.model.__table__.columns)
        # Importations locales pour casser l'import circulaire
        from .books import BooksRepository  # pylint: disable=import-outside-toplevel
        from .other_objects import OtherObjectsRepository   # pylint: disable=import-outside-toplevel
        from .obj_metadatas import ObjMetadatasRepository   # pylint: disable=import-outside-toplevel
        from .object_tags import ObjectTagsRepository   # pylint: disable=import-outside-toplevel
        from .media import MediaRepository  # pylint: disable=import-outside-toplevel
        self.book_repo = BooksRepository(self.session)
        self.other_object_repo = OtherObjectsRepository(self.session)
        self.obj_metadata_repo = ObjMetadatasRepository(self.session)
        self.object_tags_repo = ObjectTagsRepository(self.session)
        self.media_repo = MediaRepository(self.session)


    def _get_global_select(self):
        """Retourne une requête de base pour les objets, avec tous les éléments liés."""
        return (select(self.model).where(self.model.is_active == True)   # pylint: disable=singleton-comparison
            .options(joinedload(self.model.supplier),
                 joinedload(self.model.book),
                 joinedload(self.model.other_object),
                 joinedload(self.model.inventory_movements),
                 joinedload(self.model.obj_metadatas),
                 joinedload(self.model.object_tags).joinedload(ObjectTags.tag)))


    def get_all(self) -> Sequence["GeneralObjects"]:
        """
        Récupère tous les objets actifs avec tous les éléments liés :
        (supplier, book, other_object, inventory_movements, obj_metadata, object_tags).
        Returns:
            List[GeneralObjects]: Une liste de tous les objets actifs avec leurs éléments liés.
        """
        stmt = self._get_global_select()

        return self.session.execute(stmt).unique().scalars().all()


    def get_by_ref(self, reference: str | int) -> "GeneralObjects":
        """Récupère un objet par une référence (id ou ean13)."""
        if isinstance(reference, str) and not reference.isdigit():
            stmt = self._get_global_select().where(self.model.ean13 == reference)
        elif isinstance(reference, int) or (isinstance(reference, str) and reference.isdigit()):
            stmt = self._get_global_select().where(self.model.id == int(reference))
        else:
            raise ValueError("Reference must be an integer id or a string ean13.")
        return self.session.execute(stmt).unique().scalar_one_or_none()


    def get_by_name(self, name: str) -> Sequence["GeneralObjects"]:
        """Récupère une liste d'objets dont le nom correspond à la recherche."""
        stmt = self._get_global_select().where(self.model.name.ilike(f"%{name}%")).limit(10)
        return self.session.execute(stmt).unique().scalars().all()


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


    def delete(self, object_id: int):
        """Supprime un objet (soft delete)."""
        obj = self.get_by_ref(object_id)
        if not obj:
            raise ValueError(f"Object with id {object_id} not found.")
        obj.is_active = False
        self.session.commit()


    def toggle_active(self, object_id: int) -> bool:
        """Bascule le statut actif/inactif d'un objet. Retourne le nouveau statut."""
        obj = self.get_by_ref(object_id)
        if not obj:
            raise ValueError(f"Object with id {object_id} not found.")
        obj.is_active = not obj.is_active
        self.session.commit()
        return obj.is_active


    def save_from_form(self, form: Any, instance: Optional[GeneralObjects]=None) -> int:
        """
        Sauvegarde un objet à partir d'un formulaire.
        Si instance est fourni, met à jour l'objet existant, sinon en crée un nouveau.
        """
        if instance is None:
            instance = GeneralObjects()
            self.session.add(instance)

        instance.supplier_id = int(form.supplier_id.data)
        instance.general_object_type = form.general_object_type.data
        instance.ean13 = form.ean_13.data
        instance.name = form.name.data
        instance.description = form.description.data
        instance.price = float(form.price.data or 0)
        self.session.flush()
        form.general_object_id.data = instance.id

        if form.general_object_type.data == "book":
            self.book_repo.save_from_form(
                form=form.book,
                general_object_id=instance.id,
                instance=instance.book
            )
        else:
            self.other_object_repo.save_from_form(
                form=form.other_object,
                general_object_id=instance.id,
                instance=instance.other_object,
            )
        self.obj_metadata_repo.save_from_form(
            form=form.obj_metadatas,
            general_object_id=instance.id,
            instance=instance.obj_metadatas[0] if instance.obj_metadatas else None,
        )
        self.object_tags_repo.save_from_form(
            form=form,
            general_object_id=instance.id,
            parent_instance=instance,
        )
        self.media_repo.save_from_form(
            form=form,
            general_object_id=instance.id,
            parent_instance=instance,
        )
        self.commit_object()
        return instance.id
