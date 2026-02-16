"""Module de dépôt pour la gestion des inventaires."""

from typing import Any, Dict, Optional
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects.inventory import InventoryMovements

class InventoryRepository(BaseRepository):
    """
    Dépôt des données pour la gestion des inventaires.
    """
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.model = InventoryMovements
        self._kwargs = tuple(column.name for column in self.model.__table__.columns)

    def create(self, inventory_data: Dict[str, Any]):
        """
        Création d'un nouvel inventaire.
        Les champs requis pour créer un inventaire sont définis dans le modèle Inventory.
        """
        extra_keys = set(inventory_data.keys()) - set(self._kwargs)
        if extra_keys:
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")

        inventory = self.model(**inventory_data)
        try:
            self.session.add(inventory)
            self.session.commit()
            return inventory
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la création de l'inventaire : {str(e)}") from e

    def update(self, update_data: Dict[str, Any], inventory_id: Optional[int] = None,
               inventory: Optional[InventoryMovements] = None) -> InventoryMovements:
        """
        Mise à jour d'un inventaire existant.
        """
        if set(update_data.keys()) - set(self._kwargs):
            extra_keys = set(update_data.keys()) - set(self._kwargs)
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")

        if inventory_id is None and inventory is None:
            raise ValueError("Fournir un identifiant ou un objet pour la mise à jour.")

        if inventory is None:
            inventory = self.session.query(self.model).filter_by(id=inventory_id).first()
            if not inventory:
                raise ValueError(f"Inventaire avec id {inventory_id} non trouvé.")

        for key, value in update_data.items():
            setattr(inventory, key, value)

        try:
            self.session.commit()
            return inventory
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(f"Erreur lors de la mise à jour de l'inventaire : {str(e)}") from e
