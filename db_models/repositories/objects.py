"""
Module pour les dépôts des objets vendus par la librairie. Contient les classes :
    - ObjectsRepository : Contient les méthodes pour interagir avec les données des objets
                          vendus par la librairie.
"""

from typing import Any
from sqlalchemy import select, or_  # Ajout de l'import pour or_
from sqlalchemy.orm import joinedload
from db_models.repositories.base_repo import BaseRepository
from db_models.objects.objects import GeneralObjects

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

    def get_all(self):
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

    def get_by_ref(self, reference: str | int):
        """Récupère un objet par une référence (id, ean13, etc.)."""
        stmt = self._get_global_select().where(or_(
            self.model.id == reference, self.model.ean13 == reference))
        return self.session.execute(stmt).scalar_one_or_none()

    def create(self, **kwargs: str):
        """Crée un nouvel objet."""
        pass  # TODO

    def update(self, object_id: int, **kwargs: str):
        """Met à jour un objet existant."""
        pass  # TODO

    def delete(self, object_id: int):
        """Supprime un objet (soft delete)."""
        pass  # TODO
