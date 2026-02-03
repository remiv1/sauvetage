"""
Module de gestion des logs avec MongoDB.
Classe MongoDBLogger pour enregistrer et gérer les logs.
    - initialisation avec paramètres de connexion
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import os
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, PyMongoError

class MongoDBLogger:
    """Gestionnaire de logs MongoDB"""

    def __init__(self, *, host: str = os.getenv('MONGO_HOST', 'localhost'),
                 port: int = int(os.getenv('MONGO_PORT', '27017')),
                 username: str = os.getenv('MONGO_USER_APP', 'app_user'),
                 password: str = os.getenv('MONGO_PASSWORD_APP', 'app_password'),
                 database: str = os.getenv('MONGO_DB_LOGS', 'sauvetage_logs'),
                 timeout: int = 5000) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.timeout = timeout
        self.client: Optional[MongoClient[Any]] = None
        self.db = None
        self._connect()
        self.levels: List[str] = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        self.log_types: List[str] = ['users', 'logs', 'clients', 'métiers']


    def _connect(self) -> None:
        """Établir la connexion à MongoDB"""
        try:
            connection_string = (
                f"mongodb://{self.username}:{self.password}@"
                f"{self.host}:{self.port}/{self.database}"
                f"?authSource=admin&serverSelectionTimeoutMS={self.timeout}"
            )

            self.client = MongoClient(connection_string)
            self.db = self.client[self.database]

            # Vérifier la connexion
            self.client.admin.command('ping')
            logging.info("✓ Connecté à MongoDB")

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logging.error("✗ Erreur de connexion MongoDB: %s", e)
            raise

    def _get_collection_name(self) -> str:
        """Obtenir le nom de la collection pour l'année courante"""
        return datetime.now().strftime('%Y')

    def log(self, *, level: str, message: str, log_type: str = 'logs',
            user_id: Optional[str] = None, action: Optional[str] = None,
            resource_type: Optional[str] = None, resource_id: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None) -> str:
        """Enregistrer un log dans MongoDB"""

        if level not in self.levels:
            raise ValueError(f"Niveau de log invalide: {level}")

        if log_type not in self.log_types:
            raise ValueError(f"Type de log invalide: {log_type}")

        collection_name = f"{self._get_collection_name()}-{log_type}"

        log_entry: Dict[str, Any] = {
            'timestamp': datetime.now(timezone.utc),
            'level': level,
            'message': message,
            'user_id': user_id,
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'metadata': metadata or {},
            'ip_address': ip_address
        }

        try:
            result: Any = self.db[collection_name].insert_one(log_entry)    # type: ignore
            return str(result.inserted_id)  # type: ignore

        except PyMongoError as e:
            logging.error("Erreur lors de l'enregistrement du log: %s", e)
            raise

    def log_user_action(self, *, user_id: str, action: str, resource_type: Optional[str] = None,
                        resource_id: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None
                        ) -> str:
        """Enregistrer une action utilisateur"""
        return self.log(level=self.levels[1], message=f"Utilisateur {user_id} a effectué: {action}",
                        log_type=self.log_types[0], user_id=user_id, action=action,
                        resource_type=resource_type, resource_id=resource_id, metadata=metadata,
                        ip_address=ip_address)

    def log_client_event(self, *, client_id: str, event: str,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """Enregistrer un événement client"""
        return self.log(level=self.levels[1], message=f"Événement client {client_id}: {event}",
                        log_type=self.log_types[2], resource_type='client', resource_id=client_id,
                        metadata=metadata)

    def log_error(self, *, message: str, exception: Optional[Exception] = None,
                  user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Enregistrer une erreur"""
        if exception:
            message = f"{message} - {str(exception)}"

        return self.log(level=self.levels[3], message=message, log_type=self.log_types[1],
                        user_id=user_id, metadata=metadata)

    def search_logs(self, *, log_type: str = 'logs', level: Optional[str] = None,
                    user_id: Optional[str] = None, limit: int = 100) -> List[Any]:
        """Rechercher des logs"""
        collection_name = f"{self._get_collection_name()}-{log_type}"

        query = {}
        if level:
            query['level'] = level
        if user_id:
            query['user_id'] = user_id

        try:
            return list(self.db[collection_name].find(query)    # type: ignore
                        .sort('timestamp', -1).limit(limit))  # type: ignore
        except PyMongoError as e:
            logging.error("Erreur lors de la recherche: %s", e)
            return []

    def close(self) -> None:
        """Fermer la connexion"""
        if self.client:
            self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # pylint: disable=unused-argument # type: ignore
        self.close()

# Instance globale (singleton)
_logger = None  # pylint: disable=invalid-name

def get_logger() -> MongoDBLogger:
    """Obtenir l'instance du logger MongoDB"""
    global _logger  # pylint: disable=global-statement
    if _logger is None:
        _logger = MongoDBLogger()
    return _logger
