"""
Module de services pour l'intégration avec WooCommerce.
La base de données locale est source unique de vérité pour les produits,
et WooCommerce est utilisé pour exposer ces produits à l'extérieur.

TODO : implémenter les méthodes.

Le schéma métier est le suivant :
- Export des produits (dernière version) vers WooCommerce en cas de changements.
- Récupération des commandes depuis WooCommerce pour traitement dans l'outil local.
- Mise à jour du statut des commandes dans WooCommerce en fonction du traitement local.
"""

from woocommerce import API
from db_models.config.woocommerce import WooCommerceConfig, load_woocommerce_config

class WCService:
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

    def __init__(self, separated_keys: bool = False):
        if separated_keys:
            self.config_read: WooCommerceConfig = load_woocommerce_config(direction="r")
            self.config_write: WooCommerceConfig = load_woocommerce_config(direction="w")
            self.api_read: API = API(
                url=self.config_read.base_url,
                consumer_key=self.config_read.consumer_key,
                consumer_secret=self.config_read.consumer_secret,
                wp_api=self.config_read.wp_api,
                verify_ssl=self.config_read.verify_ssl,
                version=self.config_read.version
            )
            self.api_write: API = API(
                url=self.config_write.base_url,
                consumer_key=self.config_write.consumer_key,
                consumer_secret=self.config_write.consumer_secret,
                wp_api=self.config_write.wp_api,
                verify_ssl=self.config_write.verify_ssl,
                version=self.config_write.version
            )
        else:
            self.config: WooCommerceConfig = load_woocommerce_config(direction="rw")
            self.api_read: API = API(
                url=self.config.base_url,
                consumer_key=self.config.consumer_key,
                consumer_secret=self.config.consumer_secret,
                wp_api=self.config.wp_api,
                verify_ssl=self.config.verify_ssl,
                version=self.config.version
            )
            self.api_write = self.api_read



    def export_products(self):
        """
        Exporte la dernière version des produits vers WooCommerce.
        """
        # Récupération de tous les produits de la base de données
        # Transformation des données au format attendu par WooCommerce
        # Envoi des données à WooCommerce via l'API
        # Traitement du retour et gestion des erreurs
        # Logging des opérations pour le suivi et le débogage
        pass # TODO

    def get_orders(self):
        """Récupère les commandes depuis WooCommerce."""
        # Implémenter la logique pour récupérer les commandes depuis WooCommerce
        pass # TODO

    def update_order(self, order_id, status):
        """Met à jour le statut d'une commande dans WooCommerce."""
        # Implémenter la logique pour mettre à jour le statut d'une commande dans WooCommerce
        pass # TODO
