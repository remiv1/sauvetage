"""Repository WooCommerce pour les commandes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db_models.objects import Customers, Order
from db_models.repositories.orders.repository import OrdersRepository
from db_models.services.woo_commerce.orders import WCOrdersService

logger = logging.getLogger(__name__)


class OrdersWooRepository:
    """Orchestrateur de synchronisation des commandes WooCommerce.

    Ce repository est le point d'entrée pour la récupération des commandes depuis
    l'API WooCommerce, les filtres de sélection (`created_via`, dates, pagination)
    et l'enchaînement des opérations de sync. Le mapping vers l'entité locale reste
    dans OrdersRepository.
    """

    def __init__(self, session: Session):
        self.session = session
        self.order_repo = OrdersRepository(session)
        self.service = WCOrdersService(session, separated_keys=True)

    def _one_month_ago(self) -> datetime:
        """Retourne la borne inférieure utilisée pour les synchronisations récentes."""
        return datetime.now(timezone.utc) - timedelta(days=30)

    def get_max_wpwc_id(self) -> int | None:
        """Renvoie le plus grand wpwc_id enregistré localement."""
        result = self.session.execute(
            select(func.max(Order.wpwc_id)).where(Order.wpwc_id.is_not(None))
        ).scalar()
        return int(result) if result is not None else None

    def import_new_direct_orders(self) -> list[Order]:
        """Importe depuis WooCommerce les commandes ERP créées via l'API REST."""
        max_id = self.get_max_wpwc_id()
        logger.info("Import ERP WooCommerce : wpwc_id maximal local = %s.", max_id)
        wc_orders = self.service._fetch_wc_orders(  # pylint: disable=W0212
            status=None,
            created_via="rest-api",
            orderby="date",
            order="desc",
            page_size=100,
        )
        direct_orders = [
            wc for wc in wc_orders
            if (wc.get("id") is not None)
            and (max_id is None or int(wc["id"]) > max_id)
        ]
        logger.info(
            "Import ERP WooCommerce : %d commande(s) reçue(s), %d retenue(s) "
            "après filtrage sur le wpwc_id maximal.",
            len(wc_orders),
            len(direct_orders),
        )
        if not direct_orders:
            return []

        customer_cache = self.service._resolve_customer_cache(direct_orders)  # pylint: disable=W0212
        imported: list[Order] = []
        skipped_without_customer = 0
        failed = 0
        for wc_order in direct_orders:
            wpwc_id = wc_order.get("id")
            customer_id = wc_order.get("customer_id")
            if not customer_id or customer_id not in customer_cache:
                skipped_without_customer += 1
                logger.error(
                    "Import ERP WooCommerce : commande %s ignorée, client WooCommerce %s "
                    "absent ou non résolu localement.",
                    wpwc_id,
                    customer_id,
                )
                continue
            try:
                order = self.order_repo.create_from_woo_commerce(
                    wc_order,
                    customer_cache[customer_id].id,
                )
                imported.append(order)
                logger.info(
                    "Import ERP WooCommerce : commande %s insérée localement " +
                    "sous l'identifiant %d.",
                    wpwc_id,
                    order.id,
                )
            except Exception:  # pylint: disable=broad-except
                failed += 1
                logger.exception(
                    "Import ERP WooCommerce : échec de l'insertion de la commande %s.",
                    wpwc_id,
                )
        logger.info(
            "Import ERP WooCommerce terminé : %d importée(s), %d ignorée(s) sans client, "
            "%d en erreur.",
            len(imported),
            skipped_without_customer,
            failed,
        )
        return imported

    def sync_recent_wc_orders(self) -> list[Order]:
        """Met à jour localement les commandes WooCommerce récentes du site."""
        since = self._one_month_ago()
        wc_orders = self.service._fetch_wc_orders(  # pylint: disable=W0212
            status=None,
            created_via="store-api",
            after=since,
            orderby="date",
            order="desc",
            page_size=100,
        )
        updated: list[Order] = []
        skipped_invalid = 0
        created = 0
        failed = 0
        customer_cache = self.service._resolve_customer_cache(wc_orders)  # pylint: disable=W0212
        for wc_order in wc_orders:
            int_wpwc_id = self._get_recent_wc_order_id(wc_order, since)
            if int_wpwc_id is None:
                skipped_invalid += 1
                continue
            outcome, order = self._sync_store_order(
                wc_order,
                int_wpwc_id,
                customer_cache,
            )
            if outcome == "invalid":
                skipped_invalid += 1
            elif outcome == "created" and order is not None:
                created += 1
                updated.append(order)
            elif outcome == "updated" and order is not None:
                updated.append(order)
            elif outcome == "failed":
                failed += 1
        logger.info(
            "Synchronisation site WooCommerce terminée : %d créée(s), %d mise(s) à jour, "
            "%d ignorée(s) pour données invalides, %d en erreur.",
            created,
            len(updated) - created,
            skipped_invalid,
            failed,
        )
        return updated

    @staticmethod
    def _get_recent_wc_order_id(wc_order: dict, since: datetime) -> int | None:
        """Valide l'identifiant et la date de création d'une commande WooCommerce."""
        wpwc_id = wc_order.get("id")
        date_created_gmt = wc_order.get("date_created_gmt")
        if wpwc_id is None or not date_created_gmt:
            logger.error(
                "Synchronisation site WooCommerce : commande %s ignorée, "
                "wpwc_id ou date_created_gmt manquant.",
                wpwc_id,
            )
            return None
        try:
            created_dt = datetime.fromisoformat(date_created_gmt.replace("Z", "+00:00"))
        except ValueError:
            logger.error(
                "Synchronisation site WooCommerce : commande %s ignorée, "
                "date_created_gmt invalide : %s.",
                wpwc_id,
                date_created_gmt,
            )
            return None
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)
        if created_dt < since:
            logger.info(
                "Synchronisation site WooCommerce : commande %s ignorée, "
                "créée hors de la période récente.",
                wpwc_id,
            )
            return None
        return int(wpwc_id)

    def _sync_store_order(
        self,
        wc_order: dict,
        wpwc_id: int,
        customer_cache: dict[int, Customers],
    ) -> tuple[str, Order | None]:
        """Crée ou met à jour localement une commande provenant du site WooCommerce."""
        customer_wpwc_id = wc_order.get("customer_id")
        if not isinstance(customer_wpwc_id, int) or customer_wpwc_id == 0:
            logger.error(
                "Synchronisation site WooCommerce : commande %s ignorée, client "
                "WooCommerce %s absent ou non résolu localement.",
                wpwc_id,
                customer_wpwc_id,
            )
            return "invalid", None
        customer = customer_cache.get(customer_wpwc_id)
        if customer is None:
            logger.error(
                "Synchronisation site WooCommerce : commande %s ignorée, client "
                "WooCommerce %s absent ou non résolu localement.",
                wpwc_id,
                customer_wpwc_id,
            )
            return "invalid", None

        existing = self.session.execute(
            select(Order).where(Order.wpwc_id == wpwc_id)
        ).scalar_one_or_none()
        try:
            if existing is None:
                order = self.order_repo.create_from_woo_commerce(wc_order, customer.id)
                logger.info(
                    "Synchronisation site WooCommerce : commande %s créée localement "
                    "sous l'identifiant %d.",
                    wpwc_id,
                    order.id,
                )
                return "created", order
            order = self.order_repo.update_from_woo_commerce(
                existing,
                wc_order,
                customer.id,
            )
            logger.info(
                "Synchronisation site WooCommerce : commande %s mise à jour localement "
                "(identifiant local %d).",
                wpwc_id,
                order.id,
            )
            return "updated", order
        except Exception:  # pylint: disable=broad-except
            logger.exception(
                "Synchronisation site WooCommerce : échec du traitement de la commande %s.",
                wpwc_id,
            )
            return "failed", None

    def push_recent_local_orders_without_wpwc_id(self) -> list[Order]:
        """Pousse vers WooCommerce les commandes locales récentes non synchronisées."""
        since = self._one_month_ago()
        orders = self.session.execute(
            select(Order)
            .where(Order.wpwc_id.is_(None))
            .where(Order.created_at >= since)
        ).scalars().all()

        pushed: list[Order] = []
        for order in orders:
            if order.customer is None:
                continue
            ok, _ = self.service.push_order(order)
            if ok:
                pushed.append(order)
        return pushed

    def run_full_sync(self) -> dict[str, int]:
        """Exécute les trois actions de synchronisation WooCommerce des commandes."""
        imported = self.import_new_direct_orders()
        updated = self.sync_recent_wc_orders()
        pushed = self.push_recent_local_orders_without_wpwc_id()
        self.session.commit()
        return {
            "imported": len(imported),
            "updated": len(updated),
            "pushed": len(pushed),
        }
