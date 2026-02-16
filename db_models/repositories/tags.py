"""Module de gestion des tags associés aux objets ou non"""

from typing import Any, Dict, Optional
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects.objects import Tags

class TagsRepository(BaseRepository):
    """Dépôt pour la gestion des tags associés ou non aux objets"""
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.model = Tags
        # Récupération dynamique des colonnes du modèle
        self._kwargs = tuple(column.name for column in self.model.__table__.columns)

    def create(self, data: Dict[str, Any]) -> Tags:
        """Créer un tag"""
        # Vérification des champs attendus pour la création d'un tag
        extra_keys = set(data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")

        # Création de l'objet Tag avec les champs spécifiques aux tags
        tag = self.model(**data)
        try:
            self.session.add(tag)
            self.session.commit()
            return tag
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la création du tag : {str(e)}") from e

    def update(self, update_data: Dict[str, Any], tag_id: Optional[int]=None,
               tag: Optional[Tags]=None) -> Tags:
        """Mettre à jour un tag existant"""
        # Vérification des champs attendus pour la mise à jour d'un tag
        # Gestion de la levée d'exceptions
        extra_keys = set(update_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")
        if not tag and not tag_id:
            raise ValueError("Fournir un identifiant ou un objet pour la mise à jour.")
        if not tag:
            tag = self.session.query(self.model).filter_by(id=tag_id).first()
            if not tag:
                raise ValueError(f"Tag avec id {tag_id} non trouvé.")

        # Mise à jour des champs du tag avec les données fournies
        for key, value in update_data.items():
            setattr(tag, key, value)
        try:
            self.session.commit()
            return tag
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la mise à jour du tag : {str(e)}") from e
