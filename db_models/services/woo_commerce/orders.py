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
from typing import Optional, Any
import logging
from sqlalchemy.orm import Session
from db_models.repositories import CustomersRepository, OrdersRepository
from db_models.objects import Order
from db_models.services.woo_commerce.base import WCBase
from db_models.services.woo_commerce.customers import WCCustomersService

logger = logging.getLogger(__name__)

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

    def get_orders(self, status: Optional[list[str]] = None) -> list[Order]:
        """
        Récupère les commandes depuis WooCommerce, avec un filtrage optionnel par statut.
        Args:
            - status (Optional[list[str]]):
                Liste de statuts de commandes à filtrer (ex: ['processing', 'completed']).
        Returns:
            list[Order]: Liste des commandes récupérées depuis WooCommerce.
        """
        params = {}
        if status:
            params['status'] = status
        wc_orders = self.api_read.get('orders', params=params).json()
        orders = []
        for wc_order in wc_orders:
            wpwc_customer_id = wc_order.get('customer_id')
            customer = self.customer_repo.get_by_wpwc_id(wpwc_customer_id)
            if not customer:
                wpwc_customer = self.api_read.get(f'customers/{wpwc_customer_id}').json()
                customer = self.customer_repo.create_from_woo_commerce(wpwc_customer)
            order = self.order_repo.create_from_woo_commerce(wc_order, customer.id)
            orders.append(order)
        return orders

    def update_order(self, order_id: int, data: dict[str, Any]) -> bool:
        """
        Met à jour une commande dans WooCommerce.
        Args:
            - order_id (int): ID de la commande dans WooCommerce.
            - data (dict[str, Any]): Données à mettre à jour pour la commande.
        Returns:
            bool: True si la mise à jour a réussi, False sinon.
        """
        response = self.api_write.put(f'orders/{order_id}', data=data)
        if response.status_code == 200:
            logger.info("Commande %s mise à jour avec succès.", order_id)
            return True
        logger.exception(
            "Erreur lors de la mise à jour de la commande %s: %s",
            order_id,
            response.text
        )
        return False

    def create_order(self, order: Order) -> Order:
        """
        Crée une nouvelle commande dans WooCommerce.
        Args:
            - order (Order): Données de la commande à créer.
            - customer (Customers): Données du client associé à la commande.
        Returns:
            Order: La commande créée localement.
        """
        # Vérifier que le client existe dans WooCommerce, sinon le créer
        wpwc_exists = self.customer_repo.get_by_email(order.customer.mail)
        if wpwc_exists:
            wc_customer = self.customer_service.get_by_mail(order.customer.mail)
            self.customer_service.diff_customer(
                local_customer=order.customer,
                wc_customer=wc_customer,
                from_local=True
            )
        else:
            self.customer_service.create_wpwc_customer_if_not_exists(order.customer)

        # Création de la donnée sous forme de dictionnaires pour l'API WooCommerce
        data = order.to_dict_for_woo_commerce()

        # Envoie de la requête de création de la commande à WooCommerce
        response = self.api_write.post('orders', data=data)

        # Traitement du retour de l'API pour lier la commande localement
        if response.status_code == 201:
            # Récupération de la commande créée depuis WooCommerce pour obtenir les données
            wc_order = response.json()
            order_wpwc = self.order_repo.create_from_woo_commerce(wc_order, order.customer.id)
            logger.info("Commande créée avec succès dans WooCommerce.")
            order.wpwc_id = order_wpwc.wpwc_id
            return order
        logger.exception(
            "Erreur lors de la création de la commande dans WooCommerce: %s",
            response.text
        )
        return order

    def push_order(self, order: Order) -> tuple[bool, str | None]:
        """Pousse la commande vers WooCommerce (création ou mise à jour).

        Enregistre un OrderSyncLog dans tous les cas. Ne commite pas.

        Returns:
            (success, error_message)
        """
        from db_models.repositories.sync_log import SyncLogRepository  # pylint: disable=import-outside-toplevel
        sync_repo = SyncLogRepository(self.session)
        operation = "update" if order.wpwc_id else "create"

        try:
            data = order.to_dict_for_woo_commerce()
            if operation == "create":
                response = self.api_write.post("orders", data=data)
                ok = response.status_code == 201
            else:
                response = self.api_write.put(f"orders/{order.wpwc_id}", data=data)
                ok = response.status_code == 200
        except Exception as exc:  # pylint: disable=broad-except
            error_msg = str(exc)[:500]
            sync_repo.log_order(
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
            wc_data = response.json()
            if operation == "create":
                order.wpwc_id = wc_data.get("id")
            order.last_synced_at = datetime.now(timezone.utc)
            sync_repo.log_order(
                order_id=order.id,
                external_id=str(order.wpwc_id),
                sync_direction="outbound",
                operation=operation,
                sync_status="success",
            )
            logger.info("Commande %d poussée avec succès vers WooCommerce.", order.id)
            return True, None

        error_msg = response.text[:500]
        sync_repo.log_order(
            order_id=order.id,
            external_id=str(order.wpwc_id) if order.wpwc_id else None,
            sync_direction="outbound",
            operation=operation,
            sync_status="failed",
            error_message=error_msg,
        )
        logger.warning("Erreur WooCommerce (commande %d) : %s", order.id, error_msg)
        return False, error_msg
