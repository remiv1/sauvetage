"""Modules de gestion des sous-objets Autres objets liés aux objets généraux de la librairie."""

from typing import Any, Dict, Optional
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import OtherObjects


class OtherObjectsRepository(BaseRepository):
    """
    Repository pour la gestion des autres objets liés aux objets généraux.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.model = OtherObjects()
        self._kwargs = tuple(column.name for column in self.model.__table__.columns)

    def create(self, other_object_data: Dict[str, Any]) -> OtherObjects:
        """
        Crée un nouvel objet de type autre (DVD, CD, jeu, etc.).
         Les champs requis pour créer un autre objet sont :
        - general_object_id
        """
        # Levée d'une exception si des champs diffèrent des champs attendus pour un autre objet
        extra_keys = set(other_object_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")

        # Création de l'objet autre avec les champs spécifiques aux autres objets
        other_object = OtherObjects(**other_object_data)

        # Ajout de l'objet autre à la session et flush pour obtenir l'id généré
        try:
            self.session.add(other_object)
            self.session.flush()
            return other_object
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la création de l'autre objet : {str(e)}"
            ) from e

    def update(
        self,
        other_object_data: Dict[str, Any],
        other_object: Optional[OtherObjects] = None,
        other_object_id: Optional[int] = None,
    ) -> OtherObjects:
        """
        Met à jour les champs spécifiques aux autres objets (DVD, CD, jeu, etc.).
        Les champs spécifiques aux autres objets sont :
        - general_object_id
        """
        # Gestion des exceptions
        extra_keys = set(other_object_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")
        if not other_object and not other_object_id:
            raise ValueError(
                "Fournir un objet ou un identifiant d'objet pour la mise à jour."
            )
        if not other_object:
            other_object = (
                self.session.query(OtherObjects).filter_by(id=other_object_id).first()
            )
            if not other_object:
                raise ValueError(f"Autre objet avec id {other_object_id} non trouvé.")

        # Mise à jour des champs spécifiques aux autres objets
        for key, value in other_object_data.items():
            setattr(other_object, key, value)
        try:
            self.session.flush()
            return other_object
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la mise à jour de l'autre objet : {str(e)}"
            ) from e

    def save_from_form(
        self,
        general_object_id: int,
        form: Optional[Any] = None,  # pylint: disable=unused-argument
        instance: Optional[OtherObjects] = None,
    ) -> OtherObjects:
        """
        Met à jour les champs spécifiques aux autres objets à partir des données du formulaire.
        Les champs spécifiques aux autres objets sont :
        - general_object_id
        """
        if instance is None:
            instance = OtherObjects()
            self.session.add(instance)
        instance.general_object_id = general_object_id
        return instance
