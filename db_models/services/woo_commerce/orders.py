"""
Module de services pour l'intégration avec WooCommerce.
La base de données locale est source unique de vérité pour les produits,
et WooCommerce est utilisé pour exposer ces produits à l'extérieur.

Le schéma métier est le suivant :
- Export des produits (dernière version) vers WooCommerce en cas de changements.
- Récupération des commandes depuis WooCommerce pour traitement dans l'outil local.
- Mise à jour du statut des commandes dans WooCommerce en fonction du traitement local.
"""

from typing import Optional, Any
import logging
from sqlalchemy.orm import Session
from db_models.repositories import CustomersRepository, OrdersRepository
from db_models.objects import Order
from db_models.services.woo_commerce.base import WCBase

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
        else:
            logger.exception(
                "Erreur lors de la mise à jour de la commande %s: %s",
                order_id,
                response.text
            )
            return False

    def create_order(self, order: Order) -> Optional[Order]:
        """
        Crée une nouvelle commande dans WooCommerce.
        Args:
            - order (Order): Données de la commande à créer.
            - customer (Customers): Données du client associé à la commande.
        Returns:
            Optional[Order]: La commande créée localement si la création a réussi, None sinon.
        """
        # Vérifier que le client existe dans WooCommerce, sinon le créer
        # TODO: Vérifier avec mail
        if not order.customer.wpwc_id:
            self.api_read.get("customers", params={"email": order.customer.email}).json()
        # Création de la donnée sous forme de dictionnaires pour l'API WooCommerce
        data = order.to_dict_for_woo_commerce()

        # Envoie de la requête de création de la commande à WooCommerce
        response = self.api_write.post('orders', data=data)

        # Traitement du retour de l'API pour lier la commande localement
        if response.status_code == 201:
            # Récupération de la commande créée depuis WooCommerce pour obtenir les données complètes
            wc_order = response.json()
            wpwc_customer_id = wc_order.get('customer_id')
            customer = self.customer_repo.get_by_wpwc_id(wpwc_customer_id)
            if customer is None:
                order.customer.wpwc_id = wpwc_customer_id
                customer_id = order.customer.id
            else:
                customer_id = customer.id
            order_wpwc = self.order_repo.create_from_woo_commerce(wc_order, customer_id)
            logger.info("Commande créée avec succès dans WooCommerce et localement.")
            return order
        logger.exception(
            "Erreur lors de la création de la commande dans WooCommerce: %s",
            response.text
        )
        return None
