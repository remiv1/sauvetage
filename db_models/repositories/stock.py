"""
Dépôt de fonctions de gestion des stocks (commandes, mouvements, etc.) utilisées par les
routes du blueprint stock.
"""
from typing import Sequence
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from db_models.objects import InventoryMovements
from db_models.objects.objects import GeneralObjects
from db_models.objects.stocks import OrderIn, OrderInLine
from db_models.repositories.base_repo import BaseRepository


class StockRepository(BaseRepository):
    """Dépôt de fonctions de gestion des stocks (commandes, mouvements, etc.) utilisées par les
    routes du blueprint stock.
    """
    def get_zero_price_items(self) -> Sequence[dict]:
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


    def get_supplier_orders(self) -> Sequence[OrderIn]:
        """Récupère la liste des commandes fournisseurs avec toutes les relations chargées.

        Charge les fournisseurs et les lignes de commande de manière eager pour éviter
        le lazy loading.

        Returns:
            Sequence[OrderIn]: Liste des commandes avec relations complètement chargées.
        """
        stmt = (
            select(OrderIn)
            .options(
                selectinload(OrderIn.supplier),
                selectinload(OrderIn.orderin_lines)
            )
            .where(OrderIn.orderin_lines.any(OrderInLine.qty_ordered < 0))  # Exclure les retours
            .order_by(OrderIn.id.desc())
        )
        return self.session.execute(stmt).scalars().all()


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


    def get_supplier_returns(self) -> Sequence[OrderIn]:
        """Récupère la liste des retours fournisseurs avec toutes les relations chargées.

        Charge les fournisseurs et les lignes de retour de manière eager pour éviter
        le lazy loading.

        Returns:
            Sequence[OrderIn]: Liste des retours avec relations complètement chargées.
        """
        stmt = (
            select(OrderIn)
            .options(
                selectinload(OrderIn.supplier),
                selectinload(OrderIn.return_in_lines)
            )
            .where(OrderIn.return_in_id.isnot(None))  # Inclure seulement les retours
            .order_by(OrderIn.id.desc())
        )
        return self.session.execute(stmt).scalars().all()


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


    def create_order_in_line_db(self, order_in_id: int,
                                general_object_id: int,
                                quantity: int,
                                price_at_movement: float = 0.0,
                                vat_rate: float = 0.0) -> int:
        """Crée une nouvelle ligne de commande fournisseur en base à partir des données
        du formulaire.

        Args:
            order_in_id: L'identifiant de la commande fournisseur associée.
            general_object_id: L'identifiant de l'article commandé.
            quantity: La quantité commandée.
            price_at_movement: Le prix unitaire de l'article au moment du mouvement.
            vat_rate: Le taux de TVA applicable.

        Returns:
            L'ID de la ligne de commande créée.
        """
        new_line = OrderInLine(
            order_in_id=order_in_id,
            general_object_id=general_object_id,
            qty_ordered=quantity,
            unit_price=price_at_movement,
            vat_rate=vat_rate,
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


    def create_return_in_line_db(self, return_in_id: int,
                                general_object_id: int,
                                quantity: int,
                                price_at_movement: float = 0.0,
                                vat_rate: float = 0.0) -> int:
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
            qty_ordered=quantity,
            unit_price=price_at_movement,
            vat_rate=vat_rate,
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


    def get_order_by_id(self, order_id: int) -> OrderIn:
        """Récupère les détails d'une commande fournisseur à partir de son ID.

        Charge le fournisseur et les lignes de commande de manière eager.

        Args:
            order_id: L'identifiant de la commande à récupérer.

        Returns:
            L'objet OrderIn avec toutes les relations chargées.

        Raises:
            ValueError: Si la commande n'existe pas.
        """
        stmt = (
            select(OrderIn)
            .options(
                selectinload(OrderIn.supplier),
                selectinload(OrderIn.orderin_lines),
                selectinload(OrderIn.supplier)
            )
            .where(OrderIn.id == order_id)
        )

        row = self.session.execute(stmt).first()
        result = row.scalar() if row is not None else None
        if result is None:
            raise ValueError(f"Commande {order_id} introuvable")
        return result


    def get_return_by_id(self, return_id: int) -> OrderIn:
        """Récupère les détails d'un retour fournisseur à partir de son ID.

        Charge le fournisseur et les lignes de retour de manière eager.

        Args:
            return_id: L'identifiant du retour à récupérer.

        Returns:
            L'objet OrderIn avec toutes les relations chargées.

        Raises:
            ValueError: Si le retour n'existe pas.
        """
        stmt = (
            select(OrderIn)
            .options(
                selectinload(OrderIn.supplier),
                selectinload(OrderIn.return_in_lines)
            )
            .where(OrderIn.id == return_id)
        )

        result = self.session.execute(stmt).scalar_one_or_none()
        if result is None:
            raise ValueError(f"Retour {return_id} introuvable")
        return result