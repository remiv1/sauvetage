"""
Dépôt de fonctions de gestion des stocks (commandes, mouvements, etc.) utilisées par les
routes du blueprint stock.
"""

from decimal import Decimal
from typing import Sequence, Optional, Any, Dict
from sqlalchemy import select, func, or_, and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from db_models.objects import (
    InventoryMovements,
    GeneralObjects,
    OrderIn,
    OrderInLine,
    DilicomReferencial,
    Suppliers,
)
from db_models.repositories.base_repo import BaseRepository


class StockRepository(BaseRepository):
    """Dépôt de fonctions de gestion des stocks (commandes, mouvements, etc.) utilisées par les
    routes du blueprint stock.
    """

    def _compensate_inventory_movements(self, movement_ids: set, order_id: int) -> None:
        """Crée des mouvements de compensation inverse pour annuler les mouvements d'inventaire
        liés à une commande annulée.

        Args:
            movement_ids: Ensemble des IDs des mouvements d'inventaire à compenser.
            order_id: L'identifiant de la commande annulée (pour les notes du mouvement).
        """
        inventory_movements = self.session.execute(
            select(InventoryMovements).where(InventoryMovements.id.in_(movement_ids))
        ).scalars().all()
        for movement in inventory_movements:
            note = f"Compensation du mouvement #{movement.id} lié à la commande annulée #{order_id}"
            source = f"Compensation annulation commande #{order_id}"
            compensation = InventoryMovements(
                general_object_id=movement.general_object_id,
                movement_type="in" if movement.movement_type == "out" else "out",
                quantity=movement.quantity * -1,
                price_at_movement=movement.price_at_movement,
                source=source,
                destination=movement.destination,
                notes=note,
            )
            self.session.add(compensation)

    def get_zero_price_items(self) -> Sequence[dict]:
        """Récupère les articles dont le dernier inventaire a un prix de revient à zéro.

        Retourne une liste de dictionnaires avec les clés :
        - `general_object_id`, `name`, `ean13`, `price_at_movement`, `movement_id`.
        """
        im = InventoryMovements
        go = GeneralObjects

        # Sous-requête simple : timestamp max par general_object_id (mouvements d'inventaire)
        latest = (
            select(
                im.general_object_id, func.max(im.movement_timestamp).label("max_ts")
            )
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

    def clone_movement_with_updated_price(self, movement_id: int, price: float) -> int:
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
            raise RuntimeError(
                f"Erreur lors de la mise à jour du prix : {exc}"
            ) from exc

        return new_movement.id

    def update_order_in_price(self, order_id: int) -> None:
        """Met à jour le prix total d'une commande fournisseur en recalculant le total
        à partir des lignes de commande.

        Args:
            order_id: L'identifiant de la commande à mettre à jour.

        Raises:
            ValueError: Si la commande n'existe pas.
            RuntimeError: En cas d'erreur lors du commit.
        """
        order = self.session.get(OrderIn, order_id)
        if order is None:
            raise ValueError(f"Commande {order_id} introuvable")
        stmt = select(
            func.coalesce(
                func.sum(
                    OrderInLine.qty_ordered
                    * OrderInLine.unit_price
                    * (1 + OrderInLine.vat_rate / 100)
                ),
                0,
            ).label("total_ttc")
        ).where(OrderInLine.order_in_id == order_id)
        total_ttc = self.session.execute(stmt).scalar_one()
        print(f"DEBUG Calculated total TTC for order {order_id}: {total_ttc}")  # Debug log
        order.value = float(total_ttc)
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            message = f"Erreur lors de la mise à jour du prix de la commande : {exc}"
            raise SQLAlchemyError(message) from exc

    def get_supplier_orders(self, out: bool = False) -> Sequence[OrderIn]:
        """Récupère la liste des commandes fournisseurs avec toutes les relations chargées.

        Charge les fournisseurs et les lignes de commande de manière eager pour éviter
        le lazy loading.

        Returns:
            Sequence[OrderIn]: Liste des commandes avec relations complètement chargées.
        """
        if out:
            order_sens = OrderInLine.qty_ordered < 0
        else:
            order_sens = OrderInLine.qty_ordered >= 0
        stmt = (
            select(OrderIn)
            .options(
                selectinload(OrderIn.supplier), selectinload(OrderIn.orderin_lines)
            )
            .where(
                or_(
                    OrderIn.orderin_lines.any(
                        order_sens
                    ),  # Exclure les retours ou les commandes selon le sens
                    OrderIn.orderin_lines == None,  # pylint: disable=singleton-comparison
                )
            )
            .order_by(OrderIn.id.desc())
        )
        return self.session.execute(stmt).scalars().all()

    def cancel_supplier_order(self, order_id: int) -> None:
        """
        Supprime une commande fournisseur et ses lignes associées et compense les mouvements
        d'inventaire liés.

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
            self.session.execute(
                select(OrderInLine).where(OrderInLine.order_in_id == order_id)
            )
            .scalars()
            .all()
        )

        # Suppression des lignes et déliaison des mouvements d'inventaire associés
        lines_to_compensate: set = set()
        for line in lines:
            lines_to_compensate.add(line.inventory_movement_id)
            line.inventory_movement_id = None  # type: ignore
            self.session.delete(line)

        # Création des mouvements de compensation pour annuler l'impact sur le stock
        self._compensate_inventory_movements(lines_to_compensate, order_id)

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

    def edit_order_in_db(self, order_in: OrderIn, action: str = "create", out: bool = False) -> int:
        """Crée/ modifie une commande fournisseur en base à partir des données du formulaire.

        Args:
            order_in: L'objet OrderIn contenant les données de la commande à créer ou modifier.
            action: "create" pour une nouvelle commande, "edit" pour une modification.
            out: True si c'est un retour fournisseur (quantité négative), False pour une commande.

        Returns:
            L'ID de la commande créée/modifiée.
        """
        # Gestion de l'opération de création de commande
        if action == "create":
            self.session.add(order_in)
            self.session.flush()
            if out is True:
                ref = f"RET-{order_in.id:06d}"
            else:
                ref = f"CMD-{order_in.id:06d}"
            order_in.order_ref = ref
            order_in.order_state = "draft"

        # Gestion de l'opération de modification de commande
        elif action == "edit":
            existing_order = self.session.get(OrderIn, order_in.id)
            if existing_order is None:
                raise ValueError(f"Commande {order_in.id} introuvable")
            existing_order.supplier_id = order_in.supplier_id
            existing_order.supplier_id = order_in.supplier_id
            existing_order.order_ref = order_in.order_ref
            existing_order.external_ref = order_in.external_ref
            existing_order.orderin_lines = order_in.orderin_lines
            existing_order.order_state = order_in.order_state
            existing_order.value = order_in.value

        # Gestion de l'action inconnue
        else:
            raise ValueError(f"Action inconnue : {action}")

        # Commit de la transaction avec gestion des erreurs
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            message = f"Erreur lors de la création/modification de la commande : {exc}"
            raise RuntimeError(message) from exc

        return order_in.id

    def edit_order_in_line_db(
            self, new_line: OrderInLine,
            action: str = "edit",
            out: bool = False
        ) -> int:
        """
        Modifie/crée une ligne de commande fournisseur en base à partir des données du formulaire.
        Gère également la création ou la mise à jour du mouvement d'inventaire associé.
        Args:
            new_line: L'objet OrderInLine contenant les données de la ligne à créer ou modifier.
            action: "create" pour une nouvelle ligne, "edit" pour une modification.
            out: True si c'est un retour fournisseur (quantité négative), False pour une commande.
        """
        # Gestion de l'opération de création
        if action == "create":
            if out is True:
                source = f"Retour fournisseur #{new_line.order_in_id}"
                notes = f"Retour fournisseur #{new_line.order_in_id}" \
                       + f" - Ligne #{new_line.general_object_id}"
                destination = "Fournisseur"
                movement_type = "out"
            else:
                source = f"Commande fournisseur #{new_line.order_in_id}"
                notes = f"Commande fournisseur #{new_line.order_in_id}" \
                       + f" - Ligne #{new_line.general_object_id}"
                destination = "Stock"
                movement_type = "in"
            movement = InventoryMovements(
                general_object_id=new_line.general_object_id,
                movement_type=movement_type,
                quantity=new_line.qty_ordered,
                price_at_movement=Decimal(new_line.unit_price),
                source=source,
                destination=destination,
                notes=notes,
            )
            self.session.add(movement)
            self.session.flush()
            new_line.inventory_movement_id = movement.id
            self.session.add(new_line)

        # Gestion de l'opération d'édition
        elif action == "edit":
            existing_line = self.session.get(OrderInLine, new_line.id)
            if existing_line is None:
                raise ValueError(f"Ligne de commande {new_line.id} introuvable")
            existing_movement = self.session.get(
                InventoryMovements, existing_line.inventory_movement_id
            )
            if existing_movement is None:
                raise ValueError(
                    f"Mouvement d'inventaire {existing_line.inventory_movement_id} introuvable"
                )
            existing_line.general_object_id = new_line.general_object_id
            existing_line.qty_ordered = new_line.qty_ordered
            existing_line.unit_price = new_line.unit_price
            existing_line.vat_rate = new_line.vat_rate

            existing_movement.general_object_id = new_line.general_object_id
            existing_movement.quantity = new_line.qty_ordered
            existing_movement.price_at_movement = new_line.unit_price

        else:
            raise ValueError(f"Action inconnue : {action}")
        try:
            self.session.commit()
            return new_line.id
        except SQLAlchemyError as exc:
            self.session.rollback()
            message = f"Erreur lors de la modification/création de la ligne de commande : {exc}"
            raise RuntimeError(message) from exc

    def delete_order_in_line_db(self, line_id: int) -> int:
        """Supprime une ligne de commande fournisseur en base.

        Args:
            line_id: L'identifiant de la ligne de commande à supprimer.

        Raises:
            ValueError: Si la ligne de commande n'existe pas.
            RuntimeError: En cas d'erreur lors du commit.
        """
        line = self.session.get(OrderInLine, line_id)
        if line is None:
            raise ValueError(f"Ligne de commande {line_id} introuvable")

        self.session.delete(line)

        try:
            self.session.commit()
            return line_id
        except Exception as exc:
            self.session.rollback()
            message = f"Erreur lors de la suppression de la ligne de commande : {exc}"
            raise RuntimeError(message) from exc

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
                selectinload(OrderIn.supplier), selectinload(OrderIn.orderin_lines)
            )
            .where(OrderIn.id == order_id)
        )

        result = self.session.execute(stmt).scalar_one_or_none()
        if result is None:
            raise ValueError(f"Commande {order_id} introuvable")
        return result

    def search_stock_global(
        self,
        name: Optional[str] = None,
        ean13: Optional[str] = None,
        supplier_id: Optional[int] = None,
        object_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        dilicom_status: Optional[str] = None,
        page: int = 1,
        per_page: int = 100,
    ) -> Dict[str, Any]:
        """Recherche paginée du stock global avec calcul de quantité.

        La quantité est calculée comme :
          qté du dernier inventaire + mouvements 'in' - mouvements 'out'
          (seuls les mouvements postérieurs au dernier inventaire sont comptés)

        Args:
            name: Filtre par nom (ILIKE).
            ean13: Filtre par EAN13 (ILIKE).
            supplier_id: Filtre par fournisseur.
            object_type: Filtre par type d'objet.
            is_active: Filtre par statut actif/inactif.
            dilicom_status: Filtre par statut Dilicom (active, pending, deleting, inactive).
            page: Numéro de page (1-indexé).
            per_page: Nombre d'éléments par page.

        Returns:
            Dict avec 'items' (liste de dicts) et 'total' (nombre total).
        """
        im = InventoryMovements
        go = GeneralObjects

        # --- Sous-requête : quantité du dernier inventaire par objet ---
        latest_inv_ts = (
            select(
                im.general_object_id, func.max(im.movement_timestamp).label("max_ts")
            )
            .where(im.movement_type == "inventory")
            .group_by(im.general_object_id)
            .subquery()
        )
        latest_inv_qty = (
            select(
                im.general_object_id,
                im.quantity.label("inv_qty"),
                im.movement_timestamp.label("inv_ts"),
            )
            .join(
                latest_inv_ts,
                and_(
                    im.general_object_id == latest_inv_ts.c.general_object_id,
                    im.movement_timestamp == latest_inv_ts.c.max_ts,
                ),
            )
            .where(im.movement_type == "inventory")
            .subquery()
        )

        # --- Sous-requête : somme des mouvements 'in' après le dernier inventaire ---
        in_after = (
            select(
                im.general_object_id,
                func.coalesce(func.sum(im.quantity), 0).label("in_qty"),
            )
            .join(
                latest_inv_qty,
                im.general_object_id == latest_inv_qty.c.general_object_id,
            )
            .where(
                im.movement_type == "in",
                im.movement_timestamp > latest_inv_qty.c.inv_ts,
            )
            .group_by(im.general_object_id)
            .subquery()
        )

        # --- Sous-requête : somme des mouvements 'out' après le dernier inventaire ---
        out_after = (
            select(
                im.general_object_id,
                func.coalesce(func.sum(im.quantity), 0).label("out_qty"),
            )
            .join(
                latest_inv_qty,
                im.general_object_id == latest_inv_qty.c.general_object_id,
            )
            .where(
                im.movement_type == "out",
                im.movement_timestamp > latest_inv_qty.c.inv_ts,
            )
            .group_by(im.general_object_id)
            .subquery()
        )

        # --- Quantité calculée ---
        qty_expr = (
            func.coalesce(latest_inv_qty.c.inv_qty, 0)
            + func.coalesce(in_after.c.in_qty, 0)
            - func.abs(func.coalesce(out_after.c.out_qty, 0))
        ).label("stock_qty")

        # --- Requête principale ---
        base = (
            select(
                go.id,
                go.name,
                go.ean13,
                go.general_object_type,
                go.is_active,
                go.price,
                Suppliers.name.label("supplier_name"),
                Suppliers.id.label("sid"),
                qty_expr,
                DilicomReferencial.id.label("dilicom_id"),
                DilicomReferencial.create_ref,
                DilicomReferencial.delete_ref,
                DilicomReferencial.dilicom_synced,
                DilicomReferencial.is_active.label("dilicom_is_active"),
            )
            .select_from(go)
            .join(Suppliers, go.supplier_id == Suppliers.id)
            .outerjoin(latest_inv_qty, go.id == latest_inv_qty.c.general_object_id)
            .outerjoin(in_after, go.id == in_after.c.general_object_id)
            .outerjoin(out_after, go.id == out_after.c.general_object_id)
            .outerjoin(DilicomReferencial, go.ean13 == DilicomReferencial.ean13)
        )

        # --- Filtres ---
        where_clauses = []
        if name:
            where_clauses.append(go.name.ilike(f"%{name}%"))
        if ean13:
            where_clauses.append(go.ean13.ilike(f"%{ean13}%"))
        if supplier_id is not None:
            where_clauses.append(go.supplier_id == supplier_id)
        if object_type:
            where_clauses.append(go.general_object_type == object_type)
        if is_active is not None:
            where_clauses.append(
                go.is_active == is_active
            )  # pylint: disable=singleton-comparison
        dilicom_filter = self._dilicom_status_filter(dilicom_status)
        if dilicom_filter is not None:
            where_clauses.append(dilicom_filter)

        if where_clauses:
            base = base.where(and_(*where_clauses))

        # --- Comptage total ---
        count_stmt = select(func.count()).select_from(  # pylint: disable=not-callable
            base.subquery()
        )
        total = self.session.execute(count_stmt).scalar() or 0

        # --- Pagination ---
        offset = (page - 1) * per_page
        base = base.order_by(go.name).limit(per_page).offset(offset)

        rows = self.session.execute(base).all()
        items = []
        for row in rows:
            dilicom_st = self._compute_dilicom_status(
                row.dilicom_id, row.create_ref, row.delete_ref, row.dilicom_synced
            )
            items.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "ean13": row.ean13,
                    "general_object_type": row.general_object_type,
                    "is_active": row.is_active,
                    "price": float(row.price) if row.price else 0.0,
                    "supplier_name": row.supplier_name,
                    "supplier_id": row.sid,
                    "stock_qty": int(row.stock_qty) if row.stock_qty else 0,
                    "dilicom_status": dilicom_st,
                    "dilicom_id": row.dilicom_id,
                }
            )

        return {"items": items, "total": total, "page": page, "per_page": per_page}

    @staticmethod
    def _compute_dilicom_status(
        dilicom_id, create_ref, delete_ref, dilicom_synced
    ) -> str:
        """Calcule le statut Dilicom pour l'affichage.

        Returns:
            'active', 'pending', 'deleting' ou 'inactive'.
        """
        if dilicom_id is None:
            return "inactive"
        if create_ref and dilicom_synced:
            return "active"
        if create_ref and not dilicom_synced:
            return "pending"
        if delete_ref and not dilicom_synced:
            return "deleting"
        return "inactive"

    @staticmethod
    def _dilicom_status_filter(dilicom_status: Optional[str]):
        """Retourne une clause WHERE SQLAlchemy pour le filtre Dilicom, ou None."""
        mapping = {
            "active": and_(
                DilicomReferencial.create_ref == True,  # pylint: disable=singleton-comparison
                DilicomReferencial.dilicom_synced == True,  # pylint: disable=singleton-comparison
            ),
            "pending": and_(
                DilicomReferencial.create_ref == True,  # pylint: disable=singleton-comparison
                DilicomReferencial.dilicom_synced == False,  # pylint: disable=singleton-comparison
            ),
            "deleting": and_(
                DilicomReferencial.delete_ref == True,  # pylint: disable=singleton-comparison
                DilicomReferencial.dilicom_synced == False,  # pylint: disable=singleton-comparison
            ),
            "inactive": or_(
                DilicomReferencial.id == None,  # pylint: disable=singleton-comparison
                and_(
                    DilicomReferencial.delete_ref == True,  # pylint: disable=singleton-comparison
                    DilicomReferencial.dilicom_synced == True,  # pylint: disable=singleton-comparison
                ),
            ),
        }
        return mapping.get(dilicom_status) if dilicom_status else None


class DilicomReferencialRepository(BaseRepository):
    """
    Dépôt de fonctions de gestion des références Dilicom utilisées par les
    routes du blueprint stock.
    """

    def _get_select(
        self,
        to_create: Optional[bool] = None,
        created: Optional[bool] = None,
        to_delete: Optional[bool] = None,
        deleted: Optional[bool] = None,
    ) -> Any:
        """Construit une requête SQLAlchemy pour filtrer les références Dilicom en fonction
        des critères de création/suppression.

        Args:
            to_create: Si True, filtre les références à créer (create_ref=True).
            created: Si True, filtre les références déjà créées (create_ref=True).
            to_delete: Si True, filtre les références à supprimer (delete_ref=True).
            deleted: Si True, filtre les références déjà supprimées (delete_ref=True).
        """
        stmt = select(DilicomReferencial)
        where_clauses = []
        if to_create is True:
            where_clauses.append(
                DilicomReferencial.create_ref == True  # pylint: disable=singleton-comparison
            )
            where_clauses.append(
                DilicomReferencial.dilicom_synced == False  # pylint: disable=singleton-comparison
            )
        if created is True:
            where_clauses.append(
                DilicomReferencial.create_ref == True  # pylint: disable=singleton-comparison
            )
            where_clauses.append(
                DilicomReferencial.dilicom_synced == True  # pylint: disable=singleton-comparison
            )
        if to_delete is True:
            where_clauses.append(
                DilicomReferencial.delete_ref == True  # pylint: disable=singleton-comparison
            )
            where_clauses.append(
                DilicomReferencial.dilicom_synced == False  # pylint: disable=singleton-comparison
            )
        if deleted is True:
            where_clauses.append(
                DilicomReferencial.delete_ref == True  # pylint: disable=singleton-comparison
            )
            where_clauses.append(
                DilicomReferencial.dilicom_synced == True  # pylint: disable=singleton-comparison
            )
        if where_clauses:
            stmt = stmt.where(and_(*where_clauses))
        return stmt

    def _update_status(self, status: str) -> Dict[str, bool]:
        """Met à jour les champs de statut d'une référence Dilicom en fonction du statut
        cible.

        Args:
            status: Le statut cible (to_create, created, to_delete, deleted).

        Returns:
            Un dictionnaire avec les clés `create_ref`, `delete_ref`, `dilicom_synced`
            indiquant les valeurs à appliquer pour chaque champ.
        """
        if status == "to_create":
            return {"create_ref": True, "delete_ref": False, "dilicom_synced": False}
        elif status == "created":
            return {"create_ref": True, "delete_ref": False, "dilicom_synced": True}
        elif status == "to_delete":
            return {"create_ref": False, "delete_ref": True, "dilicom_synced": False}
        elif status == "deleted":
            return {"create_ref": False, "delete_ref": True, "dilicom_synced": True}
        else:
            raise ValueError(f"Statut inconnu : {status}")

    def get_one_by_ean13(self, ean13: str) -> Optional[DilicomReferencial]:
        """Récupère une référence Dilicom à partir de son EAN13.

        Args:
            ean13: L'EAN13 de la référence à récupérer.

        Returns:
            Une instance de `DilicomReferencial` si la référence existe, sinon None.
        """
        stmt = select(DilicomReferencial).where(DilicomReferencial.ean13 == ean13)
        result = self.session.execute(stmt).scalar_one_or_none()
        return result

    def create_status(
        self, ean13: str, gln13: str, movement: str
    ) -> DilicomReferencial:
        """Crée une nouvelle référence Dilicom en base.

        Args:
            ean13: L'EAN13 de l'objet à référencer.
            gln13: Le GLN13 du point de vente.
            movement: Le type de mouvement (to_create, created, to_delete, deleted).

        Returns:
            L'instance de `DilicomReferencial` créée.

        Raises:
            ValueError: Si le type de mouvement est inconnu.
            RuntimeError: En cas d'erreur lors du commit.
        """
        status_fields = self._update_status(movement)
        ref = self.get_one_by_ean13(ean13)
        if not ref:
            ref = DilicomReferencial(ean13=ean13, gln13=gln13)
        for field, value in status_fields.items():
            setattr(ref, field, value)
        self.session.add(ref)
        try:
            self.session.commit()
            print(f"Référence Dilicom créée/modifiée avec succès : ID={ref.id}")
        except Exception as exc:
            self.session.rollback()
            message = f"Erreur lors de la création de la référence Dilicom : {exc}"
            raise RuntimeError(message) from exc

        return ref
