"""
Module de services pour l'intégration avec WooCommerce.
La base de données locale est source unique de vérité pour les produits,
et WooCommerce est utilisé pour exposer ces produits à l'extérieur.

Le schéma métier est le suivant :
- Export des produits (dernière version) vers WooCommerce en cas de changements.
- Récupération des commandes depuis WooCommerce pour traitement dans l'outil local.
- Mise à jour du statut des commandes dans WooCommerce en fonction du traitement local.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
import logging
import requests
import tenacity
from requests import Response
from sqlalchemy.orm import Session
from db_models.repositories import CustomersRepository, OrdersRepository
from db_models.objects import Customers, Order, OrderLine
from db_models.services.woo_commerce.base import WCBase
from db_models.services.woo_commerce.customers import WCCustomersService
from db_models.services.woo_commerce.utils import _serialize_decimals

logger = logging.getLogger(__name__)

# Alias pour les payloads JSON bruts renvoyés par l'API WooCommerce
WCData = dict[str, Any]


class OrderStatus(str, Enum):
    """Statuts possibles d'une commande ou d'une ligne de commande.

    Note : à terme, centraliser dans db_models/objects/orders.py.
    """

    DRAFT = "draft"
    INVOICED = "invoiced"
    SHIPPED = "shipped"
    CANCELED = "canceled"
    RETURNED = "returned"
    PROCESSING = "processing"
    COMPLETED = "completed"


class _TransientAPIError(Exception):
    """Levée sur une réponse HTTP transitoirement indisponible (429, 503)."""


def _safe_log_text(text: str | None, max_len: int = 500) -> str:
    """Tronque le texte de réponse API pour les logs afin de limiter la taille."""
    if not text:
        return ""
    return text[:max_len]


def _call_api(fn: Callable[..., Response], *args: Any, **kwargs: Any) -> Response:
    """Appelle fn(*args, **kwargs) avec retry sur erreurs réseau ou transitoires.

    Effectue jusqu'à 3 tentatives avec backoff exponentiel (2 s → 30 s) sur :
    - requests.exceptions.ConnectionError / Timeout
    - Réponses HTTP 429 (rate limit) ou 503 (service indisponible)

    Args:
        fn (Callable[..., Response]): Méthode de l'API WooCommerce (ex: api.get, api.put).
        *args (Any): Arguments positionnels transmis à fn.
        **kwargs (Any): Arguments nommés transmis à fn.

    Returns:
        Response: La réponse HTTP retournée par fn.

    Raises:
        _TransientAPIError: Si les 3 tentatives échouent sur 429/503.
        requests.exceptions.ConnectionError | Timeout: Si erreur réseau persistante.
    """
    for attempt in tenacity.Retrying(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=30),
        retry=tenacity.retry_if_exception_type((
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            _TransientAPIError,
        )),
        reraise=True,
    ):
        with attempt:
            response = fn(*args, **kwargs)
            if response.status_code in (429, 503):
                raise _TransientAPIError(
                    f"HTTP {response.status_code} — réessai en cours"
                )
            return response
    raise AssertionError("jamais atteint — tenacity lève toujours avant")


def _index_wc_lines_by_product(wc_lines: list[WCData]) -> dict[tuple[int, int], int]:
    """Construit un index (product_id, variation_id) → wpwc_id à partir des lignes WC."""
    return {
        (int(wl.get("product_id") or 0), int(wl.get("variation_id") or 0)): int(wl["id"])
        for wl in wc_lines if wl.get("id")
    }


def _match_line_to_wc(line: OrderLine, wc_by_product: dict[tuple[int, int], int]) -> int | None:
    """Retourne le wpwc_id WC correspondant à une ligne locale, ou None si introuvable."""
    if not line.general_object or not line.general_object.id_wpwc:
        return None
    pid = int(line.general_object.id_wpwc)
    vid = int(line.object_variation.id_wpwc) if (
        line.object_variation and line.object_variation.id_wpwc
    ) else 0
    return wc_by_product.get((pid, vid))

class WCOrdersService(WCBase):
    """
    Service pour interagir avec l'API de WooCommerce.
    Ce service gère la connexion à l'API, l'export des produits, la récupération des commandes,
    et la mise à jour des statuts de commandes.
    Vérifier les variables d'environnement pour la configuration de l'API WooCommerce :
    - WOOCOMMERCE_BASE_URL : URL de base de l'API WooCommerce (ex: https://www.your_site.com)
    - WOOCOMMERCE_VERIFY_SSL : Vérifie le certificat SSL lors des requêtes API (True/False)
    - WOOCOMMERCE_VERSION : Version de l'API WooCommerce
    - WOOCOMMERCE_WP_API : Indique si l'API WordPress est utilisée
    - WOOCOMMERCE_READER_KEY : Clé API pour la lecture
    - WOOCOMMERCE_READER_SECRET : Secret API pour la lecture
    - WOOCOMMERCE_WRITER_KEY : Clé API pour l'écriture
    - WOOCOMMERCE_WRITER_SECRET : Secret API pour l'écriture
    - WOOCOMMERCE_CONSUMER_KEY : Clé API consommateur
    - WOOCOMMERCE_CONSUMER_SECRET : Secret API consommateur
    
    Args:
    - session (Session): Session SQLAlchemy pour les opérations de base de données.
    - separated_keys (bool): Si True, utilise des clés séparées pour la lecture et l'écriture.
                              Sinon, utilise une seule configuration pour les deux.
    """

    def __init__(self, session: Session, separated_keys: bool = False):
        """
        Initialise le service WooCommerce avec la configuration appropriée.
        Args:
            session (Session):
                - Session SQLAlchemy pour les opérations de base de données.
            separated_keys (bool):
                - Indique si des clés séparées sont utilisées pour la lecture et l'écriture.
        Attributs:
            api_read (API): Instance de l'API WooCommerce pour les opérations de lecture.
            api_write (API): Instance de l'API WooCommerce pour les opérations d'écriture.
            order_repo (OrdersRepository): Repo pour accéder aux commandes locales.
            customer_repo (CustomersRepository): Repo pour accéder aux clients locaux.
        """
        super().__init__(session, separated_keys)
        self.customer_repo = CustomersRepository(session)
        self.order_repo = OrdersRepository(session)
        self.customer_service = WCCustomersService(session, separated_keys)

    def get_orders(self, status: list[str] | None = None) -> list[Order]:
        """Récupère les commandes depuis WooCommerce, avec filtrage optionnel par statut.

        Les clients absents localement sont récupérés en un seul appel batch.
        En cas d'erreur API, retourne une liste vide.

        Args:
            status (list[str] | None): Statuts à filtrer
                (ex: ['processing', 'completed']). Si None, tous les statuts.

        Returns:
            list[Order]: Commandes importées/créées localement.
        """
        wc_orders = self._fetch_wc_orders(status)
        customer_cache = self._resolve_customer_cache(wc_orders)
        return [
            self.order_repo.create_from_woo_commerce(wc_order, customer_cache[cid].id)
            for wc_order in wc_orders
            if (cid := wc_order.get('customer_id')) and cid in customer_cache
        ]

    def update_order(self, order_id: int, data: dict[str, Any]) -> bool:
        """
        Met à jour une commande dans WooCommerce.

        Args:
            order_id (int): ID de la commande dans WooCommerce.
            data (dict[str, Any]): Données à mettre à jour pour la commande.

        Returns:
            bool: True si la mise à jour a réussi, False sinon.
        """
        try:
            response = _call_api(
                self.api_write.put, f'orders/{order_id}', data=_serialize_decimals(data)
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Exception lors de la mise à jour de la commande %s : %s",
                order_id, str(exc)[:500],
            )
            return False
        if response.status_code == 200:
            logger.info("Commande %s mise à jour avec succès.", order_id)
            return True
        logger.error(
            "Erreur lors de la mise à jour de la commande %s : %s",
            order_id, _safe_log_text(response.text),
        )
        return False

    def create_order(self, order: Order) -> Order:
        """
        Crée une nouvelle commande dans WooCommerce et lie le wpwc_id localement.

        Args:
            order (Order): Commande locale à créer dans WooCommerce.

        Returns:
            Order: La commande locale avec wpwc_id mis à jour.

        Raises:
            RuntimeError: Si la création échoue côté WooCommerce.
        """
        existing_customer = self.customer_repo.get_by_email(order.customer.mail)
        if existing_customer:
            wc_customer = self.customer_service.get_by_mail(order.customer.mail)
            self.customer_service.diff_customer(
                local_customer=order.customer,
                wc_customer=wc_customer,
                from_local=True
            )
        else:
            self.customer_service.create_wpwc_customer_if_not_exists(order.customer)

        data = _serialize_decimals(order.to_dict_for_woo_commerce())

        try:
            response = _call_api(self.api_write.post, 'orders', data=data)
        except Exception as exc:  # pylint: disable=broad-except
            raise RuntimeError(
                f"Exception lors de la création de la commande WooCommerce : {exc}"
            ) from exc

        if response.status_code == 201:
            wc_order = response.json()
            order_wpwc = self.order_repo.create_from_woo_commerce(wc_order, order.customer.id)
            logger.info("Commande créée avec succès dans WooCommerce.")
            order.wpwc_id = order_wpwc.wpwc_id
            return order
        error_text = _safe_log_text(response.text)
        logger.error(
            "Erreur lors de la création de la commande dans WooCommerce : %s", error_text
        )
        raise RuntimeError(
            f"WooCommerce a refusé la création de la commande (HTTP {response.status_code})"
        )

    def push_order(self, order: Order) -> tuple[bool, str | None]:
        """Pousse la commande vers WooCommerce (création ou mise à jour).

        Comportement des lignes :
        - Annulées avec wpwc_id présent dans WC : envoyées quantity=0 pour suppression,
          puis wpwc_id vidé.
        - Annulées avec wpwc_id absent de WC (déjà supprimé) : ignorées.
        - Actives sans wpwc_id : créées dans WC, wpwc_id assigné depuis la réponse.
        - Actives avec wpwc_id : mises à jour dans WC.

        En cas d'échec API, les wpwc_id des lignes sont restaurés à leur état initial.
        Ne commite pas. Enregistre un OrderSyncLog dans tous les cas.

        Returns:
            tuple[bool, str | None]: (succès, message_erreur_ou_None)
        """
        operation = "update" if order.wpwc_id else "create"

        # Snapshot des wpwc_id avant toute modification (restaurés en cas d'échec)
        wpwc_snapshot = {line.id: line.wpwc_id for line in order.order_lines}

        if operation == "update":
            self._pre_sync_line_ids(order)

        try:
            data = _serialize_decimals(order.to_dict_for_woo_commerce())
            if operation == "create":
                response = _call_api(self.api_write.post, "orders", data=data)
                ok = response.status_code == 201
            else:
                response = _call_api(
                    self.api_write.put, f"orders/{order.wpwc_id}", data=data
                )
                ok = response.status_code == 200
        except Exception as exc:  # pylint: disable=broad-except
            self._restore_line_snapshot(order, wpwc_snapshot)
            error_msg = str(exc)[:500]
            self.sync_log_repo.log_order(
                order_id=order.id,
                external_id=str(order.wpwc_id) if order.wpwc_id else None,
                sync_direction="outbound",
                operation=operation,
                sync_status="failed",
                error_message=error_msg,
            )
            logger.exception("Exception lors du push WooCommerce (commande %d)", order.id)
            return False, error_msg

        if ok:
            wc_data: WCData = response.json()
            if operation == "create":
                order.wpwc_id = wc_data.get("id")
            self._post_push_sync(order, wc_data.get("line_items", []))
            order.last_synced_at = datetime.now(timezone.utc)
            self.sync_log_repo.log_order(
                order_id=order.id,
                external_id=str(order.wpwc_id),
                sync_direction="outbound",
                operation=operation,
                sync_status="success",
            )
            logger.info("Commande %d poussée avec succès vers WooCommerce.", order.id)
            return True, None

        self._restore_line_snapshot(order, wpwc_snapshot)
        error_msg = _safe_log_text(response.text)
        self.sync_log_repo.log_order(
            order_id=order.id,
            external_id=str(order.wpwc_id) if order.wpwc_id else None,
            sync_direction="outbound",
            operation=operation,
            sync_status="failed",
            error_message=error_msg,
        )
        logger.warning("Erreur WooCommerce (commande %d) : %s", order.id, error_msg)
        return False, error_msg

    def _fetch_wc_orders(self, status: list[str] | None) -> list[WCData]:
        """Récupère les données brutes des commandes depuis l'API WooCommerce.

        Args:
            status (list[str] | None): Filtres de statut à transmettre à l'API.

        Returns:
            list[WCData]: Données brutes WooCommerce, ou [] en cas d'erreur.
        """
        params: dict[str, list[str]] = {}
        if status:
            params['status'] = status
        try:
            return _call_api(self.api_read.get, 'orders', params=params).json()
        except Exception:  # pylint: disable=broad-except
            logger.error("Impossible de récupérer les commandes depuis WooCommerce.")
            return []

    def _resolve_customer_cache(self, wc_orders: list[WCData]) -> dict[int, Customers]:
        """Construit un cache {wpwc_id: Customers} pour toutes les commandes WC.

        Les clients présents localement sont résolus directement.
        Les clients manquants sont récupérés en un seul appel batch depuis WC.

        Args:
            wc_orders (list[WCData]): Commandes brutes WooCommerce.

        Returns:
            dict[int, Customers]: Cache des clients résolus localement.
        """
        all_wpwc_ids: set[int] = {wc['customer_id'] for wc in wc_orders if wc.get('customer_id')}
        customer_cache: dict[int, Customers] = {}
        missing_wpwc_ids: set[int] = set()

        for wpwc_id in all_wpwc_ids:
            local = self.customer_repo.get_by_wpwc_id(wpwc_id)
            if local:
                customer_cache[wpwc_id] = local
            else:
                missing_wpwc_ids.add(wpwc_id)

        if missing_wpwc_ids:
            try:
                include_str = ','.join(str(i) for i in sorted(missing_wpwc_ids))
                wc_customers: list[WCData] = _call_api(
                    self.api_read.get, 'customers', params={'include': include_str}
                ).json()
                for wc_cust in wc_customers:
                    local = self.customer_repo.create_from_woo_commerce(wc_cust)
                    customer_cache[int(wc_cust['id'])] = local
            except Exception:  # pylint: disable=broad-except
                logger.error(
                    "Impossible de récupérer %d clients manquants depuis WooCommerce.",
                    len(missing_wpwc_ids),
                )

        for wpwc_id in all_wpwc_ids - customer_cache.keys():
            logger.warning("Client WC %s introuvable, commandes associées ignorées.", wpwc_id)

        return customer_cache

    @staticmethod
    def _restore_line_snapshot(order: Order, snapshot: dict[int, int | None]) -> None:
        """Restaure les wpwc_id des lignes à leur état d'avant un push échoué.

        Args:
            order (Order): Commande dont les lignes sont à restaurer.
            snapshot (dict[int, int | None]): {line.id: wpwc_id} pris avant le push.
        """
        for line in order.order_lines:
            if line.id in snapshot:
                line.wpwc_id = snapshot[line.id]

    def _sync_line_ids(
        self,
        order: Order,
        wc_lines: list[WCData],
        *,
        clear_all_canceled: bool,
    ) -> None:
        """Synchronise les wpwc_id des lignes locales avec l'état WooCommerce.

        Args:
            order (Order): Commande locale dont les lignes sont à synchroniser.
            wc_lines (list[WCData]): Lignes renvoyées par l'API WooCommerce.
            clear_all_canceled (bool):
                - True  : vide le wpwc_id de toutes les lignes annulées (post-push).
                - False : vide uniquement les wpwc_id stales absents de WC (pré-push).
        """
        wc_ids = {int(wl["id"]) for wl in wc_lines if wl.get("id")}
        wc_by_product = _index_wc_lines_by_product(wc_lines)

        for line in order.order_lines:
            if line.status == OrderStatus.CANCELED:
                if line.wpwc_id and (clear_all_canceled or line.wpwc_id not in wc_ids):
                    line.wpwc_id = None
            else:
                new_id = _match_line_to_wc(line, wc_by_product)
                if new_id:
                    line.wpwc_id = new_id
                elif line.wpwc_id and line.wpwc_id not in wc_ids:
                    # ID local obsolète non retrouvé par produit : traiter comme nouvelle ligne
                    logger.debug(
                        "Ligne %d (commande %d) : wpwc_id=%d absent de WC → réinitialisé.",
                        line.id, order.id, line.wpwc_id,
                    )
                    line.wpwc_id = None

    def _pre_sync_line_ids(self, order: Order) -> None:
        """Resynchronise les wpwc_id locaux depuis l'état actuel de WC avant un push.

        Effectue un GET sur la commande WC pour récupérer les lignes en cours.
        - Lignes annulées avec wpwc_id absent de WC : wpwc_id vidé (stale).
        - Lignes actives : wpwc_id mis à jour par appariement product_id + variation_id.

        Args:
            order (Order): Commande dont les lignes doivent être resynchronisées.
        """
        try:
            response = _call_api(self.api_read.get, f"orders/{order.wpwc_id}")
            if response.status_code != 200:
                return
            wc_lines: list[WCData] = response.json().get("line_items", [])
        except Exception:  # pylint: disable=broad-except
            return

        self._sync_line_ids(order, wc_lines, clear_all_canceled=False)

    def _post_push_sync(self, order: Order, wc_lines: list[WCData]) -> None:
        """Met à jour les wpwc_id locaux après un push réussi.

        - Lignes annulées : wpwc_id vidé (supprimées dans WC via quantity=0 ou déjà absentes).
        - Lignes actives : wpwc_id assigné/mis à jour depuis la réponse WC.

        Args:
            order (Order): Commande dont les lignes doivent être synchronisées.
            wc_lines (list[WCData]): Lignes renvoyées par WooCommerce dans la réponse du push.
        """
        self._sync_line_ids(order, wc_lines, clear_all_canceled=True)
