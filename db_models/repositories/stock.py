"""
Dépôt de fonctions de gestion des stocks (commandes, mouvements, etc.) utilisées par les
routes du blueprint stock.
"""
from sqlalchemy import select, func
from db_models.objects import InventoryMovements
from db_models.objects.objects import GeneralObjects
from db_models.objects.stocks import OrderIn, OrderInLine
from db_models.objects.suppliers import Suppliers
from db_models.repositories.base_repo import BaseRepository


class StockRepository(BaseRepository):
    """Dépôt de fonctions de gestion des stocks (commandes, mouvements, etc.) utilisées par les
    routes du blueprint stock.
    """
    def get_zero_price_items(self) -> list[dict]:
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


    def update_movement_price(self, movement_id: int, price: float) -> int:
        """Crée un nouveau mouvement d'inventaire en dupliquant le mouvement
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


    def get_supplier_orders(self) -> list[dict]:
        """Récupère la liste des commandes fournisseurs avec le nom du fournisseur
        et le nombre de lignes de commande.

        Returns:
            list[dict]: Liste de dictionnaires contenant les infos de chaque commande.
        """
        # Sous-requête : nombre de lignes par commande
        line_count_sq = (
            select(
                OrderInLine.order_in_id,
                func.count(OrderInLine.id).label(   # pylint: disable=not-callable
                    "line_count"
                ),
            )
            .group_by(OrderInLine.order_in_id)
            .subquery()
        )

        stmt = (
            select(
                OrderIn.id,
                OrderIn.order_ref,
                OrderIn.external_ref,
                OrderIn.value,
                Suppliers.name.label("supplier_name"),
                func.coalesce(line_count_sq.c.line_count, 0).label("line_count"),
            )
            .outerjoin(Suppliers, OrderIn.supplier_id == Suppliers.id)
            .outerjoin(line_count_sq, OrderIn.id == line_count_sq.c.order_in_id)
            .order_by(OrderIn.id.desc())
        )

        result = self.session.execute(stmt).all()
        return [
            {
                "id": row[0],
                "order_ref": row[1],
                "external_ref": row[2],
                "value": row[3],
                "supplier_name": row[4],
                "line_count": row[5],
            }
            for row in result
        ]


    def cancel_supplier_order(self, order_id: int) -> None:
        """Supprime une commande fournisseur et ses lignes associées.

        Les mouvements d'inventaire liés aux lignes sont désassociés (inventory_movement_id
        mis à NULL sur la ligne) mais conservés à titre de traçabilité.

        Args:
            order_id: L'identifiant de la commande à annuler.

        Raises:
            ValueError: Si la commande n'existe pas.
            RuntimeError: En cas d'erreur lors du commit.
        """
        order = self.session.get(OrderIn, order_id)
        if order is None:
            raise ValueError(f"Commande {order_id} introuvable")

        # Chargement ORM des lignes pour passer par les relations SQLAlchemy
        lines = (
            self.session.execute(select(OrderInLine).where(OrderInLine.order_in_id == order_id))
            .scalars()
            .all()
        )

        for line in lines:
            # Désassociation du mouvement d'inventaire (FK nullable) avant suppression
            line.inventory_movement_id = None   # type: ignore
            self.session.delete(line)

        # Flush pour propager les changements sur les lignes avant de supprimer la commande
        self.session.flush()
        self.session.delete(order)

        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise RuntimeError(
                f"Erreur lors de l'annulation de la commande : {exc}"
            ) from exc


    def create_order_in_db(self, id_supplier: int) -> int:
        """Crée une nouvelle commande fournisseur en base à partir des données du formulaire.

        Args:
            id_supplier: L'identifiant du fournisseur pour la commande.

        Returns:
            L'ID de la commande créée.
        """
        new_order = OrderIn(supplier_id=id_supplier)
        self.session.add(new_order)
        self.session.flush()
        new_order.order_ref = f"CMD-{new_order.id:06d}"
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise RuntimeError(f"Erreur lors de la création de la commande : {exc}") from exc

        return new_order.id
