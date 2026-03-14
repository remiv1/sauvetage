"""
Dépôt de fonctions de gestion des stocks (commandes, mouvements, etc.) utilisées par les
routes du blueprint stock.
"""

from decimal import Decimal
from typing import Sequence, Optional, Any, Dict
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from db_models.objects import (
    InventoryMovements, GeneralObjects, OrderIn, OrderInLine, DilicomReferencial, Suppliers
)
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
            .where(or_(
                OrderIn.orderin_lines.any(OrderInLine.qty_ordered >= 0),  # Exclure les retours
                OrderIn.orderin_lines == None  # Inclure les commandes sans lignes # pylint: disable=singleton-comparison
            ))
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
        new_order.order_state = "draft"
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
        new_return.order_state = "draft"
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


    def edit_order_in_line_db(self, line_id: int,
                                general_object_id: int,
                                quantity: int,
                                price_at_movement: float = 0.0,
                                vat_rate: float = 0.0) -> None:
        """Modifie une ligne de commande fournisseur en base à partir des données du formulaire.

        Args:
            line_id: L'identifiant de la ligne de commande à modifier.
            general_object_id: L'identifiant de l'article commandé.
            quantity: La quantité commandée.
            price_at_movement: Le prix unitaire de l'article au moment du mouvement.
            vat_rate: Le taux de TVA applicable.

        Raises:
            ValueError: Si la ligne de commande n'existe pas.
            RuntimeError: En cas d'erreur lors du commit.
        """
        line = self.session.get(OrderInLine, line_id)
        if line is None:
            raise ValueError(f"Ligne de commande {line_id} introuvable")

        line.general_object_id = general_object_id
        line.qty_ordered = quantity
        line.unit_price = Decimal(price_at_movement)
        line.vat_rate = Decimal(vat_rate)

        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            message = f"Erreur lors de la modification de la ligne de commande : {exc}"
            raise RuntimeError(message) from exc


    def delete_order_in_line_db(self, line_id: int) -> None:
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
        except Exception as exc:
            self.session.rollback()
            message = f"Erreur lors de la suppression de la ligne de commande : {exc}"
            raise RuntimeError(message) from exc


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
                selectinload(OrderIn.orderin_lines)
            )
            .where(OrderIn.id == order_id)
        )

        result = self.session.execute(stmt).scalar_one_or_none()
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
            select(im.general_object_id, func.max(im.movement_timestamp).label("max_ts"))
            .where(im.movement_type == "inventory")
            .group_by(im.general_object_id)
            .subquery()
        )
        latest_inv_qty = (
            select(im.general_object_id,
                   im.quantity.label("inv_qty"),
                   im.movement_timestamp.label("inv_ts"))
            .join(latest_inv_ts,
                  and_(im.general_object_id == latest_inv_ts.c.general_object_id,
                       im.movement_timestamp == latest_inv_ts.c.max_ts))
            .where(im.movement_type == "inventory")
            .subquery()
        )

        # --- Sous-requête : somme des mouvements 'in' après le dernier inventaire ---
        in_after = (
            select(im.general_object_id,
                   func.coalesce(func.sum(im.quantity), 0).label("in_qty"))
            .join(latest_inv_qty,
                  im.general_object_id == latest_inv_qty.c.general_object_id)
            .where(im.movement_type == "in",
                   im.movement_timestamp > latest_inv_qty.c.inv_ts)
            .group_by(im.general_object_id)
            .subquery()
        )

        # --- Sous-requête : somme des mouvements 'out' après le dernier inventaire ---
        out_after = (
            select(im.general_object_id,
                   func.coalesce(func.sum(im.quantity), 0).label("out_qty"))
            .join(latest_inv_qty,
                  im.general_object_id == latest_inv_qty.c.general_object_id)
            .where(im.movement_type == "out",
                   im.movement_timestamp > latest_inv_qty.c.inv_ts)
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
            .outerjoin(latest_inv_qty,
                       go.id == latest_inv_qty.c.general_object_id)
            .outerjoin(in_after, go.id == in_after.c.general_object_id)
            .outerjoin(out_after, go.id == out_after.c.general_object_id)
            .outerjoin(DilicomReferencial,
                       go.ean13 == DilicomReferencial.ean13)
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
            where_clauses.append(go.is_active == is_active)  # pylint: disable=singleton-comparison
        dilicom_filter = self._dilicom_status_filter(dilicom_status)
        if dilicom_filter is not None:
            where_clauses.append(dilicom_filter)

        if where_clauses:
            base = base.where(and_(*where_clauses))

        # --- Comptage total ---
        count_stmt = select(func.count()).select_from(base.subquery())  # pylint: disable=not-callable
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
            items.append({
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
            })

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
                DilicomReferencial.dilicom_synced == True  # pylint: disable=singleton-comparison
            ),
            "pending": and_(
                DilicomReferencial.create_ref == True,  # pylint: disable=singleton-comparison
                DilicomReferencial.dilicom_synced == False  # pylint: disable=singleton-comparison
            ),
            "deleting": and_(
                DilicomReferencial.delete_ref == True,  # pylint: disable=singleton-comparison
                DilicomReferencial.dilicom_synced == False  # pylint: disable=singleton-comparison
            ),
            "inactive": or_(
                DilicomReferencial.id == None,  # pylint: disable=singleton-comparison
                and_(
                    DilicomReferencial.delete_ref == True,  # pylint: disable=singleton-comparison
                    DilicomReferencial.dilicom_synced == True  # pylint: disable=singleton-comparison
                )
            ),
        }
        return mapping.get(dilicom_status) if dilicom_status else None


class DilicomReferencialRepository(BaseRepository):
    """
    Dépôt de fonctions de gestion des références Dilicom utilisées par les
    routes du blueprint stock.
    """

    def _get_select(self, to_create: Optional[bool] = None, created: Optional[bool] = None,
                    to_delete: Optional[bool] = None, deleted: Optional[bool] = None) -> Any:
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
            where_clauses.append(DilicomReferencial.create_ref == True)  # pylint: disable=singleton-comparison
            where_clauses.append(DilicomReferencial.dilicom_synced == False)  # pylint: disable=singleton-comparison
        if created is True:
            where_clauses.append(DilicomReferencial.create_ref == True)  # pylint: disable=singleton-comparison
            where_clauses.append(DilicomReferencial.dilicom_synced == True)  # pylint: disable=singleton-comparison
        if to_delete is True:
            where_clauses.append(DilicomReferencial.delete_ref == True)  # pylint: disable=singleton-comparison
            where_clauses.append(DilicomReferencial.dilicom_synced == False)  # pylint: disable=singleton-comparison
        if deleted is True:
            where_clauses.append(DilicomReferencial.delete_ref == True)  # pylint: disable=singleton-comparison
            where_clauses.append(DilicomReferencial.dilicom_synced == True)  # pylint: disable=singleton-comparison
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


    def get_all_referentials(self,
                             synced: Optional[bool] = None
                             ) -> Dict[str, Optional[Sequence[DilicomReferencial]]]:
        """Récupère toutes les références Dilicom en fonction de leur statut de synchronisation.

        Args:
            synced: Filtre les références en fonction de leur statut de synchronisation.
                    Si True, ne retourne que les références synchronisées.
                    Si False, ne retourne que les références non synchronisées.
                    Si None ou absent, retourne toutes les références.

        Retourne un dictionnaire avec les clés :
        - `to_create`, `created`, `to_delete`, `deleted`,
            chacune contenant une liste de références Dilicom.
        """
        stmt_to_create = self._get_select(to_create=True) if synced is False else None
        stmt_created = self._get_select(created=True) if synced is True else None
        stmt_to_delete = self._get_select(to_delete=True) if synced is False else None
        stmt_deleted = self._get_select(deleted=True) if synced is True else None
        referentials = {
            "to_create": self.session.execute(stmt_to_create).scalars().all() \
                                if stmt_to_create else [],
            "created": self.session.execute(stmt_created).scalars().all() \
                                if stmt_created else [],
            "to_delete": self.session.execute(stmt_to_delete).scalars().all() \
                                if stmt_to_delete else [],
            "deleted": self.session.execute(stmt_deleted).scalars().all() \
                                if stmt_deleted else [],
        }
        return referentials


    def create_or_update_referential(self, data: dict, status: str) -> int:
        """Crée ou met à jour une référence Dilicom en base à partir des données du formulaire.

        Si `id` est présent dans les données et correspond à une référence existante, la
        référence est mise à jour. Sinon, une nouvelle référence est créée.

        Args:
            data: Dictionnaire contenant les données de la référence (isbn, gln13, etc.).
            status: Le statut de la référence (to_create, created, to_delete, deleted).
        Returns:
            L'identifiant de la référence créée ou mise à jour.
        """
        ref_id = data.get("id")
        if ref_id:
            ref = self.get_one_by_ean13(data.get("ean13", ""))
            if not ref:
                raise ValueError(f"Référence avec ID {ref_id} introuvable pour mise à jour")
            status_updates = self._update_status(status)
            for key, value in data.items():
                setattr(ref, key, value)
            for key, value in status_updates.items():
                setattr(ref, key, value)
        else:
            ref = DilicomReferencial.from_dict(data)
            status_updates = self._update_status(status)
            for key, value in status_updates.items():
                setattr(ref, key, value)
            self.session.add(ref)
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            msg = f"Erreur lors de la création/mise à jour de la référence : {exc}"
            raise RuntimeError(msg) from exc
        return ref.id
