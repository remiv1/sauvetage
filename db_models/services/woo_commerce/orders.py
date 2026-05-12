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
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from db_models.repositories.customers import (
    CustomersRepository,
    CustomerAddressesRepository,
    CustomerMailsRepository,
    CustomerPhonesRepository,
    Customers,
    CustomerParts,
    CustomerPros,
    CustomerPhones,
    CustomerMails,
    CustomerAddresses,
)
from db_models.repositories.orders import OrdersRepository, Order, OrderLine
from db_models.services.utils import slugify
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
        separated_keys (bool): Si True, utilise des clés séparées pour la lecture et l'écriture.
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
            object_repo (ObjectsRepository): Repo pour accéder aux objets locaux.
            tag_repo (TagsRepository): Repo pour accéder aux tags locaux.
            media_repo (MediaRepository): Repo pour accéder aux médias locaux.
            sync_log_repo (SyncLogRepository): Repo pour enregistrer les logs de synchronisation.
        """
        super().__init__(session, separated_keys)
        self.order_repo = OrdersRepository(session)
        self.customer_repo = CustomersRepository(session)

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