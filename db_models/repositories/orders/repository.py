"""
Module pour la gestion des commandes. Contient la classe OrdersRepository qui gère
les interactions avec la base de données pour les commandes, notamment la création, la
mise à jour, la suppression et la récupération des commandes.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Sequence, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.sql import and_, or_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from db_models.repositories.base_repo import BaseRepository
from db_models.repositories.customers import (
    CustomersRepository,
    CustomerAddressesRepository,
)
from db_models.repositories.objects.objects import ObjectsRepository
from db_models.objects import (
    InventoryMovements,
    Order,
    OrderLine,
    Customers,
    CustomerParts,
    CustomerPros,
    CustomerAddresses,
    ObjectPrices,
)
from db_models.objects.vat import VatRate
from db_models.models.woo.order import WCOrderGet


class OrdersRepository(BaseRepository):
    """Dépôt local des commandes.

    Ce repository ne fait pas l'appel HTTP WooCommerce : il gère uniquement la
    persistance locale, le mapping depuis les payloads WooCommerce vers l'entité
    Order, ainsi que les opérations métier de l'ERP local.
    """

    def __init__(self, session):
        super().__init__(session)
        self.customer_repo = CustomersRepository(self.session)
        self.object_repo = ObjectsRepository(self.session)
        self.customer_address_repo = CustomerAddressesRepository(self.session)

    def _get_vat_rate_from_wpwc_tax_class(self, tax_class: str) -> float:
        """Résout le taux de TVA local actif correspondant à une classe WooCommerce."""
        return float(self._get_current_vat_rate_by_wpwc_slug(tax_class).rate)

    def _get_current_vat_rate_by_wpwc_slug(self, tax_class: str) -> VatRate:
        """Retourne le taux de TVA local actif correspondant à une classe WooCommerce."""
        vat_rate = self.session.execute(
            select(VatRate).where(
                VatRate.wpwc_slug == tax_class,
                VatRate.date_start <= datetime.now(timezone.utc),
                (VatRate.date_end.is_(None)) | (VatRate.date_end > datetime.now(timezone.utc)),
            )
        ).scalar_one_or_none()
        if vat_rate is None:
            raise ValueError(
                f"Classe de TVA WooCommerce '{tax_class}' introuvable dans le référentiel local."
            )
        return vat_rate

    def _get_current_vat_rate_by_value(self, value: float) -> VatRate:
        """Retourne le taux de TVA local actif correspondant à une valeur de pourcentage."""
        vat_rate = self.session.execute(
            select(VatRate).where(
                VatRate.rate == value,
                VatRate.date_start <= datetime.now(timezone.utc),
                (VatRate.date_end.is_(None)) | (VatRate.date_end > datetime.now(timezone.utc)),
            )
        ).scalar_one_or_none()
        if vat_rate is None:
            raise ValueError(f"Taux de TVA actif {value} % introuvable dans le référentiel local.")
        return vat_rate

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
                selectinload(Order.alerts),
                joinedload(Order.invoice_address),
                joinedload(Order.delivery_address),
                joinedload(Order.customer),
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def search_paginated(   # pylint: disable=too-many-arguments, too-many-locals
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

    def generate_reference(self, order: Order, prefix: str = "CMD") -> str:
        """Génère une référence unique au format <PREFIX>-YYMM-00001.
        Args:
            prefix: Préfixe de la référence (CMD ou RET).
        Returns:
            str: La référence générée.
        """
        now = datetime.now(timezone.utc)
        yymm = now.strftime("%y%m")
        next_num = order.id if order.id else 0
        return f"{prefix}-{yymm}-{next_num:05d}"

    def create_order(
        self,
        *,
        customer_id: int,
        invoice_address_id: int | None = None,
        delivery_address_id: int | None = None,
        create_source: str = "web",
    ) -> Order:
        """Crée un brouillon de commande pour un client.
        Args:
            customer_id: Identifiant du client.
            create_source: Source de création.
        Returns:
            Order: La commande créée.
        """
        order = Order(
            reference="",  # Référence temporaire, sera mise à jour après flush
            customer_id=customer_id,
            invoice_address_id=invoice_address_id,
            delivery_address_id=delivery_address_id,
            status="draft",
            create_source=create_source,
        )
        self.session.add(order)
        self.session.flush()
        order.reference = self.generate_reference(order, "CMD")
        try:
            self.session.commit()
            return order
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la création de la commande : {e.orig}"
            ) from e

    def create_return_order(self, source_order: Order) -> Order:
        """Crée une commande de retour à partir des lignes facturées de la commande source."""
        existing_return = self.session.execute(
            select(Order).where(Order.return_of_order_id == source_order.id)
        ).scalar_one_or_none()
        if existing_return is not None:
            return existing_return

        return_lines = [
            line
            for line in source_order.order_lines
            if line.status in {"invoiced", "shipped"}
        ]
        if not return_lines:
            raise ValueError("La commande ne contient aucune ligne facturée à retourner.")

        return_order = Order(
            reference="",
            customer_id=source_order.customer_id,
            invoice_address_id=source_order.invoice_address_id,
            delivery_address_id=source_order.delivery_address_id,
            return_of_order_id=source_order.id,
            status="draft",
            create_source="wc_cancellation_return",
        )
        for source_line in return_lines:
            return_order.order_lines.append(
                OrderLine(
                    general_object_id=source_line.general_object_id,
                    object_variation_id=source_line.object_variation_id,
                    quantity=-abs(source_line.quantity),
                    unit_price=source_line.unit_price,
                    discount=source_line.discount,
                    vat_rate=source_line.vat_rate,
                    vat_rate_id=source_line.vat_rate_id,
                    status="draft",
                    create_source="wc_cancellation_return",
                )
            )
        self.session.add(return_order)
        self.session.flush()
        return_order.reference = self.generate_reference(return_order, "RET")
        return return_order

    def create_from_woo_commerce(self, wc_order: dict, customer_id: int) -> Order:  # pylint: disable=R0914
        """Crée une commande locale à partir d'un payload WooCommerce.

        Cette méthode est un transformateur de données local : elle ne récupère pas
        les commandes depuis l'API, elle transforme uniquement un payload WC déjà
        obtenu par le service ou le repository Woo dédié.

        Args:
            wc_order: Dictionnaire contenant les données de la commande WooCommerce.
            customer_id: Identifiant du client local associé à la commande.
        Returns:
            Order: La commande créée dans la base de données locale.
        """
        def _dispatch_address(
                addresses: Sequence[CustomerAddresses]
            ) -> tuple[Optional[int], Optional[int]]:
            billing_address_id = None
            shipping_address_id = None
            for addr in addresses:
                if addr.is_billing and "WooCommerce" in (addr.address_name or ""):
                    billing_address_id = addr.id
                elif addr.is_shipping and "WooCommerce" in (addr.address_name or ""):
                    shipping_address_id = addr.id
            return billing_address_id, shipping_address_id

        # Convertion du dictionnaire en objet
        wpwc_order_model = WCOrderGet(**wc_order)

        # Conversion de l'objet en dictionnaire adapté pour l'ERP
        wpwc_order_dict = wpwc_order_model.to_dict_for_erp_order()

        # Conversion du dictionnaire en objet Order local
        wpwc_order_dict["customer_id"] = customer_id
        order = Order().from_dict(wpwc_order_dict)
        order.wpwc_id = wpwc_order_model.id
        order.create_source = wpwc_order_dict["create_source"]
        order.update_source = wpwc_order_dict["update_source"]
        order.last_synced_at = datetime.now(timezone.utc)

        # Gestion des addresses de facturation et de livraison
        local_addresses = self.customer_address_repo.get_by_customer_id(customer_id)
        if not local_addresses:
            raise ValueError(f"Aucune adresse trouvée pour le client ID {customer_id}.")
        billing_address_id, shipping_address_id = _dispatch_address(local_addresses)
        order.invoice_address_id = billing_address_id
        order.delivery_address_id = shipping_address_id

        # Gestion de lignes de la commande
        for line in wpwc_order_model.line_items:

            # Récupération du produit en local à partir de l'ID WooCommerce
            local_product = self.object_repo.get_by_wpwc_id(int(line.product_id))
            if not local_product:
                raise ValueError(
                    f"Produit avec ID WooCommerce {line.product_id} introuvable."
                )

            # Création de la ligne de commande locale en passant par un dictionnaire intermédiaire
            line_dict = wpwc_order_model.to_dict_for_erp_orderline(line)
            vat_rate = self._get_current_vat_rate_by_wpwc_slug(line.tax_class)
            line_dict["vat_rate"] = float(vat_rate.rate)
            line_dict["vat_rate_id"] = vat_rate.id
            line_object = OrderLine().from_dict(line_dict)
            line_object.wpwc_id = line.id
            line_object.create_source = line_dict["create_source"]
            line_object.update_source = line_dict["update_source"]
            line_object.general_object = local_product
            order.order_lines.append(line_object)
        self.session.add(order)
        self.session.flush()
        order.reference = self.generate_reference(order, "CMD")
        try:
            self.session.commit()
            return order
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la création de la commande depuis WooCommerce : {e.orig}"
            ) from e

    def update_from_woo_commerce(
        self,
        order: Order,
        wc_order: dict,
        customer_id: int,
    ) -> Order:
        """Met à jour une commande locale à partir d'un payload WooCommerce.

        Les lignes sont rapprochées par leur `wpwc_id`. Les lignes absentes
        localement sont ajoutées, sans supprimer de lignes ERP existantes.
        """
        wpwc_order_model = WCOrderGet(**wc_order)
        wpwc_order_dict = wpwc_order_model.to_dict_for_erp_order()
        order.customer_id = customer_id
        order.status = wpwc_order_dict["status"]
        order.update_source = wpwc_order_dict["update_source"]
        order.last_synced_at = datetime.now(timezone.utc)

        local_lines = {
            line.wpwc_id: line for line in order.order_lines if line.wpwc_id is not None
        }
        for wc_line in wpwc_order_model.line_items:
            line_dict = wpwc_order_model.to_dict_for_erp_orderline(wc_line)
            vat_rate = self._get_current_vat_rate_by_wpwc_slug(wc_line.tax_class)
            line_dict["vat_rate"] = float(vat_rate.rate)
            line_dict["vat_rate_id"] = vat_rate.id
            local_product = self.object_repo.get_by_wpwc_id(int(wc_line.product_id))
            if not local_product:
                raise ValueError(
                    f"Produit avec ID WooCommerce {wc_line.product_id} introuvable."
                )
            local_line = local_lines.get(wc_line.id)
            if local_line is None:
                local_line = OrderLine().from_dict(line_dict)
                local_line.wpwc_id = wc_line.id
                local_line.create_source = line_dict["create_source"]
                order.order_lines.append(local_line)
            else:
                local_line.quantity = line_dict["quantity"]
                local_line.unit_price = line_dict["unit_price"]
                local_line.discount = line_dict["discount"]
                local_line.vat_rate = line_dict["vat_rate"]
                local_line.vat_rate_id = line_dict["vat_rate_id"]
                local_line.update_source = line_dict["update_source"]
            local_line.general_object = local_product

        try:
            self.session.commit()
            return order
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la mise à jour de la commande depuis WooCommerce : {exc}"
            ) from exc

    def update_delivery_address(
        self,
        order: Order,
        *,
        delivery_address_id: int,
        update_source: str = "web",
    ) -> Order:
        """Met à jour l'adresse de livraison d'une commande."""
        address = self.session.execute(
            select(CustomerAddresses).where(
                CustomerAddresses.id == delivery_address_id,
                CustomerAddresses.customer_id == order.customer_id,
                CustomerAddresses.is_active == True,  # pylint: disable=singleton-comparison
                CustomerAddresses.is_shipping == True,  # pylint: disable=singleton-comparison
            )
        ).scalar_one_or_none()
        if address is None:
            raise ValueError("Adresse de livraison invalide pour ce client.")

        order.delivery_address_id = delivery_address_id
        order.update_source = update_source
        try:
            self.session.commit()
            return order
        except SQLAlchemyError as e:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la mise à jour de l'adresse de livraison : {str(e)}"
            ) from e

    def _build_order_line(
        self,
        *,
        order: Order,
        general_object_id: int,
        quantity: int,
        unit_price: float | Any,
        discount: float,
        vat_rate: float,
        vat_rate_id: int,
        create_source: str,
        object_variation_id: int | None,
    ) -> OrderLine:
        """Construit une ligne de commande à partir des paramètres métier."""
        return OrderLine(
            order_id=order.id,
            general_object_id=general_object_id,
            quantity=quantity,
            unit_price=float(unit_price),
            discount=discount,
            vat_rate=float(vat_rate),
            vat_rate_id=vat_rate_id,
            status="draft",
            create_source=create_source,
            object_variation_id=object_variation_id,
        )

    def _save_order_lines(
        self,
        lines: list[OrderLine],
        *,
        is_multi: bool,
    ) -> OrderLine | list[OrderLine]:
        """Persiste une ou plusieurs lignes et renvoie le bon type de résultat."""
        try:
            if is_multi:
                self.session.add_all(lines)
            else:
                self.session.add(lines[0])
            self.session.commit()
            return lines if is_multi else lines[0]
        except IntegrityError as exc:
            self.session.rollback()
            message = "lignes" if is_multi else "ligne"
            raise ValueError(f"Erreur lors de l'ajout des {message} : {exc.orig}") from exc

    def _build_vat_rate_id_for_price_row(
        self,
        price_row: ObjectPrices,
        fallback_vat_rate: float,
    ) -> int:
        """Retourne l'identifiant TVA à associer à un prix métier."""
        vat_rate_value = (
            float(price_row.vat_rate.rate)
            if price_row.vat_rate is not None
            else float(fallback_vat_rate or 0)
        )
        if price_row.vat_rate_id is not None:
            return price_row.vat_rate_id
        return self._get_current_vat_rate_by_value(vat_rate_value).id

    def add_line(   # pylint: disable=R0914, R0913
        self,
        order: Order,
        *,
        general_object_id: int,
        quantity: int,
        unit_price: float,
        discount: float = 0,
        vat_rate: float,
        object_variation_id: int | None = None,
        create_source: str = "web",
    ) -> OrderLine | list[OrderLine]:
        """Ajoute une ligne à une commande.

        Si l'article a plusieurs prix valides (avec leur propre TVA), on découpe la
        commande en autant de lignes que de prix actifs pour respecter le modèle
        de données métier.
        """
        general_object = self.session.execute(
            select(self.object_repo.model)
            .where(self.object_repo.model.id == general_object_id)
            .options(
                joinedload(self.object_repo.model.prices).joinedload(ObjectPrices.vat_rate),
            )
        ).scalars().unique().one_or_none()
        if general_object is None:
            raise ValueError(f"Article {general_object_id} introuvable.")

        valid_prices = sorted(
            general_object.get_valid_prices(),
            key=lambda row: (row.from_date, row.id or 0),
        )
        if len(valid_prices) > 1:
            lines = [
                self._build_order_line(
                    order=order,
                    general_object_id=general_object_id,
                    quantity=quantity,
                    unit_price=price_row.price,
                    discount=discount,
                    vat_rate=(
                        float(price_row.vat_rate.rate)
                        if price_row.vat_rate is not None
                        else float(vat_rate or 0)
                    ),
                    vat_rate_id=self._build_vat_rate_id_for_price_row(price_row, vat_rate),
                    create_source=create_source,
                    object_variation_id=object_variation_id,
                )
                for price_row in valid_prices
            ]
            return self._save_order_lines(lines, is_multi=True)

        if valid_prices:
            unit_price = float(valid_prices[0].price)
            vat_rate = (
                float(valid_prices[0].vat_rate.rate)
                if valid_prices[0].vat_rate is not None
                else float(vat_rate or 0)
            )

        resolved_vat_rate = (
            valid_prices[0].vat_rate
            if valid_prices and valid_prices[0].vat_rate is not None
            else self._get_current_vat_rate_by_value(float(vat_rate))
        )
        line = self._build_order_line(
            order=order,
            general_object_id=general_object_id,
            quantity=quantity,
            unit_price=unit_price,
            discount=discount,
            vat_rate=vat_rate,
            vat_rate_id=resolved_vat_rate.id,
            create_source=create_source,
            object_variation_id=object_variation_id,
        )
        return self._save_order_lines([line], is_multi=False)

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

    def update_line(    # pylint: disable=R0913
        self,
        line: OrderLine,
        *,
        quantity: int,
        unit_price: float,
        discount: float,
        vat_rate: float,
        update_source: str = "web",
    ) -> OrderLine:
        """Met à jour une ligne de commande encore en brouillon."""
        if line.status != "draft":
            raise ValueError("Seules les lignes en brouillon peuvent être modifiées.")

        line.quantity = quantity
        line.unit_price = unit_price
        line.discount = discount
        line.vat_rate = vat_rate
        line.vat_rate_id = self._get_current_vat_rate_by_value(vat_rate).id
        line.update_source = update_source
        try:
            self.session.commit()
            return line
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de la mise à jour de la ligne de commande : {exc}"
            ) from exc

    def cancel_order(self, order: Order, update_source: str = "web") -> Order:
        """Annule une commande, ses lignes et leurs réservations dans une transaction.

        Args:
            order: La commande à annuler.
            update_source: Source de la mise à jour.

        Returns:
            La commande annulée.

        Raises:
            ValueError: Si l'annulation ne peut pas être enregistrée.
        """
        try:
            for line in order.order_lines or []:
                if line.status != "draft":
                    continue
                self.session.add(
                    InventoryMovements(
                        general_object_id=line.general_object_id,
                        movement_type="reserved",
                        quantity=-line.quantity,
                        price_at_movement=float(line.unit_price),
                        source="order",
                        destination=f"CMD-{order.id}",
                        notes=f"Annulation réservation commande {order.reference}",
                    )
                )
                line.status = "cancelled"
                line.update_source = update_source

            order.status = "cancelled"
            order.update_source = update_source
            self.session.commit()
            return order
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise ValueError(
                f"Erreur lors de l'annulation de la commande : {exc}"
            ) from exc

    def remove_line(self, line: OrderLine) -> bool:
        """Annule une ligne de commande (soft delete → status 'cancelled').
        Args:
            line: La ligne à annuler.
        Returns:
            bool: True si l'annulation a réussi.
        """
        if line.status != "draft":
            raise ValueError("Seules les lignes en brouillon peuvent être annulées.")
        try:
            line.status = "cancelled"
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
        if (
            abs(invoiced_quantity) >= abs(order_line.quantity)
            or invoiced_quantity * order_line.quantity <= 0
        ):
            raise ValueError(
                "La quantité facturée doit avoir le même signe et une valeur absolue "
                "inférieure à la quantité commandée."
            )

        new_line = OrderLine(
            order_id=order_line.order_id,
            general_object_id=order_line.general_object_id,
            quantity=order_line.quantity - invoiced_quantity,
            unit_price=order_line.unit_price,
            vat_rate=order_line.vat_rate,
            vat_rate_id=order_line.vat_rate_id,
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
