"""
Dépôt de fonctions de gestion des stocks (commandes, mouvements, etc.) utilisées par les
routes du blueprint stock.
"""
from datetime import datetime, timezone
from sqlalchemy import select, func
from db_models.objects import InventoryMovements
from db_models.objects.objects import GeneralObjects
from db_models.repositories.base_repo import BaseRepository


class StockRepository(BaseRepository):
    """
    Dépôt de fonctions de gestion des stocks (commandes, mouvements, etc.) utilisées par les
    routes du blueprint stock.
    """
    def get_zero_price_items(self) -> list[dict[str, object]]:
        """Récupère les articles dont le dernier inventaire a un prix de revient à zéro.

        Retourne une liste de dictionnaires avec les clés :
        - `general_object_id`, `name`, `ean13`, `price_at_movement`, `movement_id`.
        """
        im = InventoryMovements
        go = GeneralObjects

        # Sous-requête simple : timestamp max par general_object_id (mouvements d'inventaire)
        latest = (
            select(im.general_object_id, func.max(im.movement_timestamp).label("max_ts"))
            .where(im.movement_type == "inventory")
            .group_by(im.general_object_id)
            .subquery()
        )

        stmt = (
            select(
                im.id.label("movement_id"),
                im.general_object_id,
                go.name,
                go.ean13,
                im.price_at_movement,
            )
            .select_from(
                im.__table__.join(
                    latest,
                    (im.general_object_id == latest.c.general_object_id)
                    & (im.movement_timestamp == latest.c.max_ts),
                ).join(go, im.general_object_id == go.id)
            )
            .where(im.price_at_movement == 0)
        )

        result = self.session.execute(stmt).all()
        return [
            {
                "movement_id": row[0],
                "general_object_id": row[1],
                "name": row[2],
                "ean13": row[3],
                "price_at_movement": row[4],
            }
            for row in result
        ]


    def get_qty_by_id(self, general_object_id: int, theorical: bool = False) -> int:
        """
        Récupère la quantité en stock d'un article à partir de son ID.
        """
        def _last_inventory() -> tuple[int, datetime]:
            """
            Récupère la quantité et le timestamp du dernier mouvement d'inventaire pour l'article.
            Si aucun mouvement d'inventaire n'existe, retourne (0, epoch).
            """
            stmt = (
                select(
                    InventoryMovements
                ).where(
                    InventoryMovements.general_object_id == general_object_id,
                    InventoryMovements.movement_type == "inventory",
                ).order_by(InventoryMovements.movement_timestamp.desc())
                .limit(1)
            )
            result = self.session.execute(stmt).scalar_one_or_none()
            if result is None:
                return 0, datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            return result.quantity, result.movement_timestamp

        def _sum_by_type(movement_type: str, since: datetime) -> int:
            """
            Calcule la somme des quantités pour un type de mouvement donné depuis une date.
            arguments:
                movement_type: "in", "out" ou "reserved"
                since: datetime à partir duquel calculer la somme
            retourne:
                Somme des quantités pour le type de mouvement depuis la date donnée
            """
            stmt = (
                select(
                    func.coalesce(func.sum(InventoryMovements.quantity), 0)
                ).where(
                    InventoryMovements.general_object_id == general_object_id,
                    InventoryMovements.movement_type == movement_type,
                    InventoryMovements.movement_timestamp >= since,
                )
            )
            return self.session.execute(stmt).scalar_one()

        qty, timestamp = _last_inventory()
        qty += _sum_by_type("in", timestamp)
        qty -= _sum_by_type("out", timestamp)
        if not theorical:
            qty -= _sum_by_type("reserved", timestamp)

        return qty


    def update_movement_price(self, movement_id: int, price: float) -> int:
        """
        Crée un nouveau mouvement d'inventaire en dupliquant le mouvement
        d'origine et en y appliquant le nouveau prix de revient.

        Le mouvement original reste inchangé (traçabilité).

        Args:
            movement_id: ID du mouvement d'origine à dupliquer.
            price: Nouveau prix de revient à appliquer.

        Returns:
            L'ID du nouveau mouvement créé.

        Raises:
            ValueError: si le mouvement d'origine n'existe pas.
            RuntimeError: en cas d'erreur lors du commit.
        """
        original = self.session.get(InventoryMovements, movement_id)
        if original is None:
            raise ValueError(f"Mouvement {movement_id} introuvable")

        new_movement = InventoryMovements(
            general_object_id=original.general_object_id,
            movement_type=original.movement_type,
            quantity=original.quantity,
            price_at_movement=price,
            source=original.source,
            destination=original.destination,
            notes=f"Correction prix (réf. mouvement #{movement_id})",
        )
        self.session.add(new_movement)
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise RuntimeError(f"Erreur lors de la mise à jour du prix : {exc}") from exc

        return new_movement.id
