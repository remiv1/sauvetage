"""Dépôt pour les opérations liées à l'inventaire et aux mouvements de stock."""

from typing import Sequence, Optional, Dict, Any
from sqlalchemy import select, func, or_, and_
from db_models.objects import (
    InventoryMovements,
    GeneralObjects,
    DilicomReferencial,
    Suppliers,
)
from db_models.repositories.base_repo import BaseRepository


class InventoryRepository(BaseRepository):
    """Dépôt pour les mouvements d'inventaire et la recherche de stock."""

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
