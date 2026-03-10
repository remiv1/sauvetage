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


    def get_supplier_returns(self) -> list[dict]:
        """Récupère la liste des retours fournisseurs avec le nom du fournisseur
        et le nombre de lignes de retour.

        Returns:
            list[dict]: Liste de dictionnaires contenant les infos de chaque retour.
        """
        # Sous-requête : nombre de lignes par retour
        line_count_sq = (
            select(
                OrderInLine.return_in_id,
                func.count(OrderInLine.id).label("line_count"), # pylint: disable=not-callable
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


    def create_return_in_db(self, id_supplier: int) -> int:
        """Crée un nouveau retour fournisseur en base à partir des données du formulaire.

        Args:
            id_supplier: L'identifiant du fournisseur pour le retour.

        Returns:
            L'ID du retour créé.
        """
        new_return = OrderIn(supplier_id=id_supplier, order_ref="temp")
        self.session.add(new_return)
        self.session.flush()
        new_return.order_ref = f"RET-{new_return.id:06d}"
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise RuntimeError(f"Erreur lors de la création du retour : {exc}") from exc

        return new_return.id


    def create_return_in_line_db(self, return_in_id: int,
                                general_object_id: int,
                                quantity: int,
                                price_at_movement: float = 0.0) -> int:
        """Crée une nouvelle ligne de retour fournisseur en base à partir des données
        du formulaire.

        Args:
            return_in_id: L'identifiant du retour fournisseur associé.
            general_object_id: L'identifiant de l'article retourné.
            quantity: La quantité retournée.

        Returns:
            L'ID de la ligne de retour créée.
        """
        new_line = OrderInLine(
            return_in_id=return_in_id,
            general_object_id=general_object_id,
            quantity=quantity,
        )
        new_movement = InventoryMovements(
            general_object_id=general_object_id,
            movement_type="out",
            quantity=quantity * -1,  # Quantité négative pour un retour
            price_at_movement=price_at_movement,
            source=f"Retour fournisseur #{return_in_id}",
            destination="Stock",
            notes=f"Retour fournisseur #{return_in_id} - Ligne #{general_object_id}",
        )
        self.session.add(new_movement)
        self.session.flush()
        new_line.inventory_movement_id = new_movement.id
        self.session.add(new_line)
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            message = f"Erreur lors de la création de la ligne de retour : {exc}"
            raise RuntimeError(message) from exc

        return new_line.id


    def create_order_in_line_db(self, order_in_id: int,
                                general_object_id: int,
                                quantity: int,
                                price_at_movement: float = 0.0) -> int:
        """Crée une nouvelle ligne de commande fournisseur en base à partir des données
        du formulaire.

        Args:
            order_in_id: L'identifiant de la commande fournisseur associée.
            general_object_id: L'identifiant de l'article commandé.
            quantity: La quantité commandée.

        Returns:
            L'ID de la ligne de commande créée.
        """
        new_line = OrderInLine(
            order_in_id=order_in_id,
            general_object_id=general_object_id,
            quantity=quantity,
        )
        new_movement = InventoryMovements(
            general_object_id=general_object_id,
            movement_type="in",
            quantity=quantity,
            price_at_movement=price_at_movement,
            source=f"Commande fournisseur #{order_in_id}",
            destination="Stock",
            notes=f"Commande fournisseur #{order_in_id} - Ligne #{general_object_id}",
        )
        self.session.add(new_movement)
        self.session.flush()
        new_line.inventory_movement_id = new_movement.id
        self.session.add(new_line)
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            message = f"Erreur lors de la création de la ligne de commande : {exc}"
            raise RuntimeError(message) from exc

        return new_line.id


    def create_order_in_db(self, id_supplier: int) -> int:
        """Crée une nouvelle commande fournisseur en base à partir des données du formulaire.

        Args:
            id_supplier: L'identifiant du fournisseur pour la commande.

        Returns:
            L'ID de la commande créée.
        """
        new_order = OrderIn(supplier_id=id_supplier, order_ref="temp")
        self.session.add(new_order)
        self.session.flush()
        new_order.order_ref = f"CMD-{new_order.id:06d}"
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise RuntimeError(f"Erreur lors de la création de la commande : {exc}") from exc

        return new_order.id


    def get_order_by_id(self, order_id: int) -> dict:
        """Récupère les détails d'une commande fournisseur à partir de son ID.

        Args:
            order_id: L'identifiant de la commande à récupérer.

        Returns:
            Un dictionnaire contenant les détails de la commande, ou un dictionnaire
            vide si la commande n'existe pas.
        """
        stmt = (
            select(
                OrderIn.id,
                OrderIn.order_ref,
                OrderIn.external_ref,
                OrderIn.value,
                Suppliers.name.label("supplier_name"),
            )
            .outerjoin(Suppliers, OrderIn.supplier_id == Suppliers.id)
            .where(OrderIn.id == order_id)
        )

        result = self.session.execute(stmt).first()
        if result is None:
            return {}

        return {
            "id": result[0],
            "order_ref": result[1],
            "external_ref": result[2],
            "value": result[3],
            "supplier_name": result[4],
        }


    def get_return_by_id(self, return_id: int) -> dict:
        """Récupère les détails d'un retour fournisseur à partir de son ID.

        Args:
            return_id: L'identifiant du retour à récupérer.

        Returns:
            Un dictionnaire contenant les détails du retour, ou un dictionnaire
            vide si le retour n'existe pas.
        """
        stmt = (
            select(
                OrderIn.id,
                OrderIn.order_ref,
                OrderIn.external_ref,
                OrderIn.value,
                Suppliers.name.label("supplier_name"),
            )
            .outerjoin(Suppliers, OrderIn.supplier_id == Suppliers.id)
            .where(OrderIn.id == return_id)
        )

        result = self.session.execute(stmt).first()
        if result is None:
            return {}

        return {
            "id": result[0],
            "order_ref": result[1],
            "external_ref": result[2],
            "value": result[3],
            "supplier_name": result[4],
        }
