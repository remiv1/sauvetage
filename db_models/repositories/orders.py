"""
Module pour la gestion des commandes. Contient la classe OrdersRepository qui gère
les interactions avec la base de données pour les commandes, notamment la création, la
mise à jour, la suppression et la récupération des commandes.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.sql import and_, or_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from db_models.repositories.base_repo import BaseRepository
from db_models.objects import Order, OrderLine, Customers, CustomerParts, CustomerPros


class OrdersRepository(BaseRepository):
    """Dépôt de données pour les commandes. Contient les méthodes pour interagir avec les
    données des commandes, notamment la création, la mise à jour, la suppression et la
    récupération des commandes."""

    # ── Lecture ──────────────────────────────────────────────

    def get_by_id(self, order_id: int) -> Order | None:
        """Récupère une commande par son identifiant avec eager loading.
        Args:
            order_id (int): L'identifiant de la commande à récupérer.
        Returns:
            Order | None: La commande correspondant à l'identifiant, ou None s'il n'existe pas.
        """
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.order_lines).joinedload(OrderLine.general_object),
                selectinload(Order.invoices),
                selectinload(Order.shipments),
                joinedload(Order.invoice_address),
                joinedload(Order.delivery_address),
                joinedload(Order.customer),
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def search_paginated(
        self,
        *,
        reference: str | None = None,
        customer_name: str | None = None,
        status: str | list[str] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """Recherche paginée des commandes avec filtres.
        Args:
            reference: Filtre par référence (ILIKE).
            customer_name: Filtre par nom du client (ILIKE).
            status: Filtre par statut exact ou liste de statuts.
            date_from: Date de création minimum.
            date_to: Date de création maximum.
            page: Numéro de page (1-indexed).
            per_page: Nombre d'éléments par page.
        Returns:
            Dict avec clés: items, total, page, per_page.
        """
        conditions = []
        needs_join = False

        if reference:
            conditions.append(Order.reference.ilike(f"%{reference}%"))
        if customer_name:
            needs_join = True
            conditions.append(or_(
                CustomerParts.first_name.ilike(f"%{customer_name}%"),
                CustomerParts.last_name.ilike(f"%{customer_name}%"),
                CustomerPros.company_name.ilike(f"%{customer_name}%"),
            ))
        if status:
            if isinstance(status, list):
                conditions.append(Order.status.in_(status))
            else:
                conditions.append(Order.status == status)
        if date_from:
            conditions.append(Order.created_at >= date_from)
        if date_to:
            conditions.append(Order.created_at <= date_to)

        where_clause = and_(*conditions) if conditions else True

        # Comptage total
        count_stmt = select(func.count(Order.id)).where(where_clause)  # type: ignore  # pylint: disable=not-callable
        if needs_join:
            count_stmt = (
                count_stmt
                .join(Customers, Order.customer_id == Customers.id)
                .outerjoin(CustomerParts, CustomerParts.customer_id == Customers.id)
                .outerjoin(CustomerPros, CustomerPros.customer_id == Customers.id)
            )
        total = self.session.execute(count_stmt).scalar()

        # Requête paginée
        offset = (page - 1) * per_page
        items_stmt = (
            select(Order)
            .where(where_clause)  # type: ignore
            .options(
                joinedload(Order.customer),
                selectinload(Order.order_lines),
            )
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        if needs_join:
            items_stmt = (
                items_stmt
                .join(Customers, Order.customer_id == Customers.id)
                .outerjoin(CustomerParts, CustomerParts.customer_id == Customers.id)
                .outerjoin(CustomerPros, CustomerPros.customer_id == Customers.id)
            )

        items = self.session.execute(items_stmt).scalars().unique().all()

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    # ── Écriture ─────────────────────────────────────────────

    def generate_reference(self, prefix: str = "CMD") -> str:
        """Génère une référence unique au format <PREFIX>-YYMM-00001.
        Args:
            prefix: Préfixe de la référence (CMD ou RET).
        Returns:
            str: La référence générée.
        """
        now = datetime.now(timezone.utc)
        yymm = now.strftime("%y%m")
        pattern = f"{prefix}-{yymm}-%"

        last_ref = self.session.execute(
            select(Order.reference)
            .where(Order.reference.like(pattern))
            .order_by(Order.reference.desc())
            .limit(1)
        ).scalar()

        if last_ref:
            last_num = int(last_ref.split("-")[-1])
            next_num = last_num + 1
        else:
            next_num = 1

        return f"{prefix}-{yymm}-{next_num:05d}"

    def create_order(self, *, customer_id: int, create_source: str = "web") -> Order:
        """Crée un brouillon de commande pour un client.
        Args:
            customer_id: Identifiant du client.
            create_source: Source de création.
        Returns:
            Order: La commande créée.
        """
        order = Order(
            reference=self.generate_reference("CMD"),
            customer_id=customer_id,
            status="draft",
            create_source=create_source,
        )
        try:
            self.session.add(order)
            self.session.commit()
            return order
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la création de la commande : {e.orig}"
            ) from e

    def add_line(
        self,
        order: Order,
        *,
        general_object_id: int,
        quantity: int,
        unit_price: float,
        discount: float = 0,
        vat_rate: float,
        create_source: str = "web",
    ) -> OrderLine:
        """Ajoute une ligne à une commande.
        Args:
            order: La commande parente.
            general_object_id: L'identifiant de l'article.
            quantity: Quantité commandée.
            unit_price: Prix unitaire HT.
            discount: Remise en pourcentage (0 par défaut).
            vat_rate: Taux de TVA en pourcentage.
            create_source: Source de création.
        Returns:
            OrderLine: La ligne de commande créée.
        """
        line = OrderLine(
            order_id=order.id,
            general_object_id=general_object_id,
            quantity=quantity,
            unit_price=unit_price,
            discount=discount,
            vat_rate=vat_rate,
            status="draft",
            create_source=create_source,
        )
        try:
            self.session.add(line)
            self.session.commit()
            return line
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de l'ajout de la ligne : {e.orig}"
            ) from e

    def update_order_status(
        self, order: Order, new_status: str, update_source: str = "web"
    ) -> Order:
        """Met à jour le statut d'une commande.
        Args:
            order: La commande à mettre à jour.
            new_status: Le nouveau statut.
            update_source: Source de la mise à jour.
        Returns:
            Order: La commande mise à jour.
        """
        order.status = new_status
        order.update_source = update_source
        try:
            self.session.commit()
            return order
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la mise à jour du statut : {str(e)}"
            ) from e

    def remove_line(self, line: OrderLine) -> bool:
        """Annule une ligne de commande (soft delete → status 'canceled').
        Args:
            line: La ligne à annuler.
        Returns:
            bool: True si l'annulation a réussi.
        """
        if line.status != "draft":
            raise ValueError("Seules les lignes en brouillon peuvent être annulées.")
        try:
            line.status = "canceled"
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de l'annulation de la ligne : {str(e)}"
            ) from e

    # ── Facturation (coupure de ligne) ───────────────────────

    def cut_line_for_invoice(
        self, order_line: OrderLine, invoiced_quantity: int
    ) -> bool:
        """Crée une nouvelle ligne de commande à partir d'une ligne de commande existante,
        en ajustant les quantités et les montants pour correspondre à la quantité facturée.
        Args:
            order_line (OrderLine): La ligne de commande à couper.
            invoiced_quantity (int): La quantité facturée.
        Returns:
            bool: True si la ligne a été coupée avec succès.
        """
        if invoiced_quantity >= order_line.quantity:
            raise ValueError(
                "La quantité facturée doit être inférieure à la quantité commandée."
            )

        new_line = OrderLine(
            order_id=order_line.order_id,
            general_object_id=order_line.general_object_id,
            quantity=order_line.quantity - invoiced_quantity,
            unit_price=order_line.unit_price,
            vat_rate=order_line.vat_rate,
            status="draft",
            create_source="cut_line_for_invoice",
        )

        order_line.quantity = invoiced_quantity

        try:
            self.session.add(new_line)
            self.session.merge(order_line)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la coupure de la ligne de commande : {str(e)}"
            ) from e
