"""Module de dépôt pour la gestion des inventaires."""

from typing import Any, Dict, Optional
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import InventoryMovements


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
            raise ValueError(
                f"Erreur lors de la création de l'inventaire : {str(e)}"
            ) from e

    def update(
        self,
        update_data: Dict[str, Any],
        inventory_id: Optional[int] = None,
        inventory: Optional[InventoryMovements] = None,
    ) -> InventoryMovements:
        """
        Mise à jour d'un inventaire existant.
        """
        if set(update_data.keys()) - set(self._kwargs):
            extra_keys = set(update_data.keys()) - set(self._kwargs)
            raise ValueError(f"Champs inattendus : {', '.join(sorted(extra_keys))}")

        if inventory_id is None and inventory is None:
            raise ValueError("Fournir un identifiant ou un objet pour la mise à jour.")

        if inventory is None:
            inventory = (
                self.session.query(self.model).filter_by(id=inventory_id).first()
            )
            if not inventory:
                raise ValueError(f"Inventaire avec id {inventory_id} non trouvé.")

        for key, value in update_data.items():
            setattr(inventory, key, value)

        try:
            self.session.commit()
            return inventory
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la mise à jour de l'inventaire : {str(e)}"
            ) from e

    def get_last_inventory_movement(self, general_object_id: int) -> Optional[InventoryMovements]:
        """
        Récupère le dernier mouvement d'inventaire pour un objet donné.
        """
        return (
            self.session.query(self.model)
            .filter_by(general_object_id=general_object_id)
            .order_by(self.model.date.desc())
            .first()
        )

    def get_average_price(self, general_object_id: int) -> float:
        """
        Récupère le dernier prix moyen d'achat pour un objet donné.
        """
        last_movement = self.get_last_inventory_movement(general_object_id)
        if not last_movement:
            qty_at_movement = 0
            costs_at_movement = 0.0
            last_movement_date = datetime.strptime('1990-01-01 00:00:00', "%Y-%m-%d %H:%M:%S")
        else:
            qty_at_movement = last_movement.quantity
            costs_at_movement = last_movement.price_at_movement * qty_at_movement
            last_movement_date = last_movement.movement_timestamp
        avg_price = costs_at_movement / qty_at_movement if qty_at_movement > 0 else 0.0
        all_ordered_since_last_movement = (
            self.session.query(self.model)
            .filter(self.model.general_object_id == general_object_id)
            .filter(self.model.date >= last_movement_date)
            .filter(self.model.movement_type == "in")
            .all()
        )
        if all_ordered_since_last_movement:
            total_qty = sum(m.quantity for m in all_ordered_since_last_movement)
            total_cost = sum(m.quantity * m.unit_price for m in all_ordered_since_last_movement)
            avg_price = (total_cost + costs_at_movement) \
                            / (total_qty + qty_at_movement) if total_qty > 0 else avg_price
        return avg_price
