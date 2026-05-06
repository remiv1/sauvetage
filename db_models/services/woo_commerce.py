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

from typing import Any
from woocommerce import API
from sqlalchemy import select
from db_models.objects.vat import VatRate
from sqlalchemy.orm import Session
from db_models.config.woocommerce import WooCommerceConfig, load_woocommerce_config
from db_models.repositories.objects import ObjectsRepository

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

    def __init__(self, session: Session, separated_keys: bool = False):
        self.session = session
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
        self.object_repo = ObjectsRepository(self.session)

    def export_products(self):
        """
        Exporte la dernière version des produits vers WooCommerce.
        """
        # Récupération de tous les produits de la base de données
        products = self.object_repo.get_all(only_actives=True)
        # Transformation des données au format attendu par WooCommerce
        products_dicts = [product.to_dict() for product in products]
        # Envoi des données à WooCommerce via l'API
        # Traitement du retour et gestion des erreurs
        # Logging des opérations pour le suivi et le débogage
        pass # TODO

    def get_orders(self):
        """Récupère les commandes depuis WooCommerce."""
        # Implémenter la logique pour récupérer les commandes depuis WooCommerce
        pass # TODO

    def get_customer_info(self, customer_id):
        """Récupère les informations d'un client depuis WooCommerce."""
        # Implémenter la logique pour récupérer les informations d'un client depuis WooCommerce
        pass # TODO

    def update_order(self, order_id, status):
        """Met à jour le statut d'une commande dans WooCommerce."""
        # Implémenter la logique pour mettre à jour le statut d'une commande dans WooCommerce
        pass # TODO

    def export_tags(self) -> None:
        """Exporte les tags vers WooCommerce."""
        # Implémenter la logique pour exporter les tags vers WooCommerce
        # Récupérer les tags sans id_wpwc
        # Les envoyer à WooCommerce via l'API
        # Traiter le retour pour récupérer les id_wpwc et les stocker en base de données
        pass # TODO

    def export_pictures(self) -> None:
        """Exporte les images vers WooCommerce."""
        # Implémenter la logique pour exporter les images vers WooCommerce
        # Récupérer les images sans id_wpwc
        # Les envoyer à WooCommerce via l'API
        # Traiter le retour pour récupérer les id_wpwc et les stocker en base de données
        pass # TODO

    def _diff_vat_rates(self, vat_rates, wpwc_vat_rates) -> dict[str, list[dict[str, Any]]]:
        """Calcule les différences entre les taux de TVA locaux et ceux de WooCommerce."""
        data: dict[str, list[dict[str, Any]]] = {"create": [], "update": [], "delete": []}
        wpwc_vat_ids = {int(wpwc["id"]) for wpwc in wpwc_vat_rates}
        for v in vat_rates:
            for wpwc in wpwc_vat_rates:
                if float(wpwc["rate"]) == float(v.rate):
                    data["update"].append({
                        "id": int(wpwc["id"]),
                        "rate": str(v.rate),
                        "name": v.label,
                    })
                    wpwc_vat_ids.remove(int(wpwc["id"]))
                    break
            else:
                data["create"].append({
                    "rate": str(v.rate),
                    "name": v.label,
                })
        for wpwc_id in wpwc_vat_ids:
            data["delete"].append({"id": wpwc_id})
        return data

    def export_vat_rates(self) -> None:
        """Exporte les taux de TVA vers WooCommerce."""
        # Implémenter la logique pour exporter les taux de TVA vers WooCommerce
        # Récupérer les taux de TVA en cours de validité
        stmt = select(VatRate).where(VatRate.date_end == None) # pylint: disable=singleton-comparison
        vat_rates = self.session.execute(stmt).scalars().all()
        # Récupère les taux sur le site Internet de WooCommerce pour éviter les doublons
        wpwc_vat_rates = self.api_read.get("/taxes").json()
        # Calculer les différences entre les taux locaux et ceux de WooCommerce
        data = self._diff_vat_rates(vat_rates, wpwc_vat_rates)
        # Les envoyer à WooCommerce via l'API
        wpwc_vat_rates = self.api_write.post("/taxes/batch", data=data).json()
        # Traiter le retour pour récupérer les id_wpwc et les stocker en base de données
        for v in vat_rates:
            for wpwc in wpwc_vat_rates.get("update", []):
                if float(wpwc["rate"]) == float(v.rate):
                    v.wpwc_id = int(wpwc["id"])
                    break
            for wpwc in wpwc_vat_rates.get("create", []):
                if float(wpwc["rate"]) == float(v.rate):
                    v.wpwc_id = int(wpwc["id"])
                    break
        self.session.commit()
