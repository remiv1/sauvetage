"""
Module de service pour la gestion des clients dans l'intégration avec WooCommerce.
Ce module fournit des méthodes pour récupérer, créer et mettre à jour les clients dans WooCommerce,
ainsi que pour synchroniser les données des clients entre WooCommerce et la base de données locale.
"""

from typing import Optional, Any
import logging
from sqlalchemy.orm import Session
from db_models.objects import Customers
from db_models.models.woo import WCCustomerGet
from db_models.repositories import CustomersRepository, OrdersRepository
from db_models.services.woo_commerce.base import WCBase

logger = logging.getLogger(__name__)

class WCCustomersService(WCBase):
    """
    Service pour interagir avec l'API de WooCommerce.
    Ce service gère la connexion à l'API, la gestion des clients,
    et la synchronisation des données des clients entre WooCommerce et la base de données locale.
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
            customer_repo (CustomersRepository): Repo pour accéder aux clients locaux.
        """
        super().__init__(session, separated_keys)
        self.order_repo = OrdersRepository(session)
        self.customer_repo = CustomersRepository(session)

    def exists_wpwc_customer(self, email: str) -> bool:
        """
        Vérifie si un client avec l'email donné existe dans WooCommerce.
        Args:
            email (str): L'email du client à vérifier.
        Returns:
            bool: True si le client existe, False sinon.
        """
        response = self.api_read.get("customers", params={"email": email})
        if response.status_code == 200:
            customers = response.json()
            return len(customers) > 0
        logger.exception(
            "Erreur lors de la vérification du client WooCommerce : %s - %s",
            response.status_code,
            response.text
        )
        return False

    def create_wpwc_customer(self, customer: Customers) -> Optional[Customers]:
        """
        Crée un client dans WooCommerce à partir des données fournies.
        Args:
            customer (Customers): Objet Customers contenant les données du client à créer.
        Returns:
            Customers: L'objet Customers créé localement après la création dans WooCommerce.
        """
        # Vérifier si le client existe déjà dans WooCommerce et si l'email est disponible
        if not (email := customer.get_wpwc_mail()):
            logger.warning(
                "Le client %s n'a pas d'email actif, impossible de le créer dans WooCommerce.",
                customer.id
            )
            return None
        if self.exists_wpwc_customer(email):
            logger.info(
                "Le client avec l'email %s existe déjà dans WooCommerce.",
                email
            )
            return None

        # Convertir les données du client en format compatible avec l'API WooCommerce
        customer_data = customer.to_dict_for_wpwc()

        # Créer le client dans WooCommerce
        response = self.api_write.post("customers", data=customer_data)

        # Traitement du retour de l'API
        if response.status_code == 201:
            wc_customer = response.json()
            data = {
                'wpwc_id': wc_customer.get('id'),
            }
            return self.customer_repo.update_info(customer.id, data)
        logger.exception(
            "Erreur lors de la création du client WooCommerce : %s - %s",
            response.status_code,
            response.text
        )
        return None

    def diff_customer(
            self,
            local_customer: Customers,
            wc_customer: dict[str, Any],
            from_local: bool = True
        ) -> dict[str, Any]:
        """
        Compare les données d'un client local avec celles d'un client WooCommerce pour détecter
        les différences et retourner un dictionnaire des champs à mettre à jour ainsi que
        le modèle à mettre à jour (local ou WooCommerce).
        Args:
            local_customer (Customers): Objet Customers représentant le client local.
            wc_customer (dict): Dictionnaire représentant le client WooCommerce.
        Returns:
            dict[str, Any]: Dictionnaire des champs à mettre à jour.
        """
        local_data = local_customer.to_dict_for_wpwc(update=True)
        wc_data = WCCustomerGet(**wc_customer).model_dump()
        if from_local:
            return self._diff(from_=local_data, to_=wc_data)
        return self._diff(from_=wc_data, to_=local_data)

    def _diff_keyed_list(
        self, local: list[dict], remote: list[dict]
    ) -> list[dict] | None:
        """Compare deux listes de dicts indexées par 'key' (ex: meta_data WooCommerce)."""
        local_map = {x["key"]: x["value"] for x in local}
        remote_map = {x["key"]: x["value"] for x in remote if "key" in x}
        sub = self._diff(from_=local_map, to_=remote_map)
        return [{"key": k, "value": v} for k, v in sub.items()] if sub else None

    def _diff_list(self, local: list, remote: list) -> list | None:
        """Compare deux listes et retourne la valeur locale si différente."""
        if all(isinstance(x, dict) for x in local):
            if all("key" in x for x in local):
                return self._diff_keyed_list(local, remote)
            return local if local != remote else None
        return local if local != remote else None

    def _diff(self, *, from_: dict[str, Any], to_: dict[str, Any]) -> dict[str, Any]:
        diff = {}
        for key, local_value in from_.items():
            remote_value = to_.get(key)
            if isinstance(local_value, dict) and isinstance(remote_value, dict):
                sub = self._diff(from_=local_value, to_=remote_value)
                if sub:
                    diff[key] = sub
            elif isinstance(local_value, list) and isinstance(remote_value, list):
                result = self._diff_list(local_value, remote_value)
                if result is not None:
                    diff[key] = result
            elif local_value != remote_value:
                diff[key] = local_value
        return diff
