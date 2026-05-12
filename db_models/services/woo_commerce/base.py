"""Module de base pour les services WooCommerce.
Ce module fournit une classe de base pour les services WooCommerce, gérant la configuration et
l'initialisation des clients API pour les opérations de lecture et d'écriture.
Il permet également de centraliser la gestion des sessions."""

from typing import Optional
from woocommerce import API
from sqlalchemy.orm import Session
from db_models.config.woocommerce import WooCommerceConfig, load_woocommerce_config
from db_models.repositories.sync_log import SyncLogRepository

class WCBase:
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
                    - Avantages des clés séparées :
                        - Permet de limiter les permissions de chaque clé.
                        - Facilite la rotation des clés sans interruption de service.
                        - Améliore la sécurité en cas de compromission d'une clé.
                    - Inconvénients des clés séparées :
                        - Nécessite une configuration plus complexe.
                        - Peut compliquer le développement et les tests.
        Attributs:
            api_read (API): Instance de l'API WooCommerce pour les opérations de lecture.
            api_write (API): Instance de l'API WooCommerce pour les opérations d'écriture.
            object_repo (ObjectsRepository): Repo pour accéder aux objets locaux.
            tag_repo (TagsRepository): Repo pour accéder aux tags locaux.
            sync_log_repo (SyncLogRepository): Repo pour enregistrer les logs de synchronisation.
        """
        self.session = session
        if separated_keys:
            config_read: WooCommerceConfig = load_woocommerce_config(direction="r")
            config_write: WooCommerceConfig = load_woocommerce_config(direction="w")
            self.api_read: API = API(
                url=config_read.base_url,
                consumer_key=config_read.consumer_key,
                consumer_secret=config_read.consumer_secret,
                wp_api=config_read.wp_api,
                verify_ssl=config_read.verify_ssl,
                version=config_read.version
            )
            self.api_write: API = API(
                url=config_write.base_url,
                consumer_key=config_write.consumer_key,
                consumer_secret=config_write.consumer_secret,
                wp_api=config_write.wp_api,
                verify_ssl=config_write.verify_ssl,
                version=config_write.version
            )
        else:
            config: WooCommerceConfig = load_woocommerce_config(direction="rw")
            self.api_read: API = API(
                url=config.base_url,
                consumer_key=config.consumer_key,
                consumer_secret=config.consumer_secret,
                wp_api=config.wp_api,
                verify_ssl=config.verify_ssl,
                version=config.version
            )
            self.api_write = self.api_read
        self.sync_log_repo = SyncLogRepository(self.session)


    def _log_sync(
        self,
        entity_type: str,
        entity_id: Optional[int],
        wpwc_id: Optional[int],
        operation: str,
        sync_status: str,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Enregistre une entrée dans le journal de synchronisation WooCommerce.
        
        Args:
            entity_type (str): Type de l'entité synchronisée (wpwc, henrri, ...).
            entity_id (Optional[int]): ID local de l'entité.
            wpwc_id (Optional[int]): ID externe WooCommerce de l'entité.
            operation (str): Type d'opération (create, update, delete).
            sync_status (str): Statut de la synchronisation (success, failure).
            error_message (Optional[str]): Message d'erreur en cas d'échec.

        Returns:
            None
        """
        self.sync_log_repo.log_object(
            entity_type=entity_type,
            entity_id=entity_id,
            external_id=str(wpwc_id) if wpwc_id is not None else None,
            external_system="wpwc",
            sync_direction="outbound",
            operation=operation,
            sync_status=sync_status,
            error_message=error_message,
        )
