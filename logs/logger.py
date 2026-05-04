"""
Module de gestion des logs avec MongoDB.
Classe MongoDBLogger pour enregistrer et gérer les logs.
    - initialisation avec paramètres de connexion
"""

from urllib.parse import quote_plus
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import os
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, PyMongoError

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

class MongoDBLogger:
    """
    Gestionnaire de logs MongoDB.
    
    Args:
    - host (str): Adresse du serveur MongoDB
    - port (int): Port de connexion à MongoDB
    - username (str): Nom d'utilisateur pour l'authentification MongoDB
    - password (str): Mot de passe pour l'authentification MongoDB
    - database (str): Nom de la base de données MongoDB pour les logs
    - timeout (int): Délai de connexion en millisecondes
    """

    def __init__(   # pylint: disable=too-many-arguments
        self,
        *,
        host: str = os.getenv("MONGO_HOST", "localhost"),
        port: int = int(os.getenv("MONGO_PORT", "27017")),
        username: str = os.getenv("MONGO_USER_APP", "app_user"),
        password: str = os.getenv("MONGO_PASSWORD_APP", "app_password"),
        database: str = os.getenv("MONGO_DB_LOGS", "sauvetage_logs"),
        timeout: int = 5000,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.timeout = timeout
        self.client: Optional[MongoClient[Any]] = None
        self.db = None
        self._connect()
        self.levels: List[str] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.log_types: List[str] = ["users", "logs", "clients", "métiers"]

    def _connect(self) -> None:
        """Établir la connexion à MongoDB"""
        try:
            username_enc = quote_plus(self.username)
            password_enc = quote_plus(self.password)
            connection_string = (
                f"mongodb://{username_enc}:{password_enc}@"
                f"{self.host}:{self.port}/{self.database}"
                f"?authSource={self.database}&connectTimeoutMS={self.timeout}"
            )

            self.client = MongoClient(connection_string)
            self.db = self.client[self.database]

            # Vérifier la connexion
            self.client.admin.command("ping")
            logging.info("✓ Connecté à MongoDB")

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logging.error("✗ Erreur de connexion MongoDB: %s", e)
            raise

    def _get_collection_name(self) -> str:
        """Obtenir le nom de la collection pour l'année courante"""
        return datetime.now().strftime("%Y")

    def log(    # pylint: disable=too-many-arguments
        self,
        *,
        level: str,
        message: str,
        log_type: str = "logs",
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        obj_metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> str:
        """
        Enregistrer un log dans MongoDB
        Utiliser plutôt les méthodes spécialisées comme :
        - log_user_action
        - log_client_event
        - log_error
        - log_dilicom_event

        Args:
            level (str): Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message (str): Message de log
            log_type (str): Type de log (users, logs, clients, métiers)
            user_id (Optional[str]): ID de l'utilisateur associé au log
            action (Optional[str]): Action effectuée (ex: "login", "upload_file", etc.)
            resource_type (Optional[str]): Type de ressource (ex: "file", "endpoint", etc.)
            resource_id (Optional[str]): ID de la ressource concernée
            obj_metadata (Optional[Dict[str, Any]]): Métadonnées supplémentaires liées au log
            ip_address (Optional[str]): Adresse IP de l'utilisateur
            status_code (Optional[int]): Code de statut HTTP associé à l'action (si applicable)
        """

        if level not in self.levels:
            raise ValueError(f"Niveau de log invalide: {level}")

        if log_type not in self.log_types:
            raise ValueError(f"Type de log invalide: {log_type}")

        collection_name = f"{self._get_collection_name()}-{log_type}"

        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc),
            "level": level,
            "message": message,
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "status_code": status_code,
            "obj_metadata": obj_metadata or {},
            "ip_address": ip_address,
        }

        try:
            result: Any = self.db[collection_name].insert_one(log_entry)  # type: ignore
            return str(result.inserted_id)  # type: ignore

        except PyMongoError as e:
            logging.error("Erreur lors de l'enregistrement du log: %s", e)
            raise

    def log_user_action(    # pylint: disable=too-many-arguments
        self,
        *,
        user_id: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        obj_metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> str:
        """
        Enregistrer une action utilisateur.
        
        Args:
            user_id (str): ID de l'utilisateur
            action (str): Action effectuée par l'utilisateur
            resource_type (Optional[str]): Type de ressource concernée
            resource_id (Optional[str]): ID de la ressource concernée
            obj_metadata (Optional[Dict[str, Any]]): Métadonnées supplémentaires liées à l'action
            ip_address (Optional[str]): Adresse IP de l'utilisateur
        Returns:
            str: ID du log enregistré
        """
        return self.log(
            level=self.levels[1],
            message=f"Utilisateur {user_id} a effectué: {action}",
            log_type=self.log_types[0],
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            obj_metadata=obj_metadata,
            ip_address=ip_address,
        )

    def log_client_event(
        self,
        *,
        client_id: str,
        event: str,
        obj_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Enregistrer un événement client"""
        return self.log(
            level=self.levels[1],
            message=f"Événement client {client_id}: {event}",
            log_type=self.log_types[2],
            resource_type="client",
            resource_id=client_id,
            obj_metadata=obj_metadata,
        )

    def log_error(
        self,
        *,
        message: str,
        exception: Optional[Exception] = None,
        user_id: Optional[str] = None,
        obj_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Enregistrer une erreur"""
        if exception:
            message = f"{message} - {str(exception)}"

        return self.log(
            level=self.levels[3],
            message=message,
            log_type=self.log_types[1],
            user_id=user_id,
            obj_metadata=obj_metadata,
        )

    def log_dilicom_event(
        self,
        *,
        event: str,
        obj_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Enregistrer un événement métier lié à Dilicom
        
        Args:
            event (str): Description de l'événement métier Dilicom
            obj_metadata (Optional[Dict[str, Any]]): Métadonnées supplémentaires liées à
                                                     l'événement (ex: type d'opération, durée, etc.)
        Returns:
            str: ID du log enregistré
        """
        return self.log(
            level=self.levels[1],
            message=f"Événement métier Dilicom: {event}",
            log_type=self.log_types[3],
            resource_type="dilicom_event",
            obj_metadata=obj_metadata,
        )

    def search_logs(
        self,
        *,
        log_type: str = "logs",
        level: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Any]:
        """Rechercher des logs"""
        collection_name = f"{self._get_collection_name()}-{log_type}"

        query = {}
        if level:
            query["level"] = level
        if user_id:
            query["user_id"] = user_id

        try:
            return list(
                self.db[collection_name]  # type: ignore
                .find(query)
                .sort("timestamp", -1)
                .limit(limit)
            )  # type: ignore
        except PyMongoError as e:
            logging.error("Erreur lors de la recherche: %s", e)
            return []

    def close(self) -> None:
        """Fermer la connexion"""
        if self.client:
            self.client.close()

    def __enter__(self):
        return self

    def __exit__(
        self, exc_type, exc_val, exc_tb
    ):  # pylint: disable=unused-argument # type: ignore
        self.close()


class MongoForwardHandler(logging.Handler):
    """
    Handler qui redirige les logs Python vers MongoDBLogger.
    """
    def __init__(self, mongo_logger):
        super().__init__()
        self.mongo_logger = mongo_logger
        level = os.getenv("LOG_LEVEL", "INFO").upper()
        if level == "DEBUG":
            self.log_level = logging.DEBUG
        elif level == "INFO":
            self.log_level = logging.INFO
        elif level == "WARNING":
            self.log_level = logging.WARNING
        elif level == "ERROR":
            self.log_level = logging.ERROR
        elif level == "CRITICAL":
            self.log_level = logging.CRITICAL
        else:
            self.log_level = logging.INFO
        self.setLevel(self.log_level)

    def emit(self, record: logging.LogRecord) -> None:
        """Rediriger le log vers MongoDBLogger"""
        if record.name.startswith("pymongo"):
            return

        # Récupérer les extras du record de log
        extra: Dict[str, Any] = getattr(record, "extra", {})

        self.mongo_logger.log(
            level=record.levelname,
            message=record.getMessage(),
            log_type=extra.get("log_type", "logs"),
            user_id=extra.get("user_id"),
            action=extra.get("action"),
            resource_type=extra.get("resource_type"),
            resource_id=extra.get("resource_id"),
            obj_metadata=extra.get("obj_metadata"),
            ip_address=extra.get("ip_address"),
            status_code=extra.get("status_code"),
        )


class FilterExtras(logging.Filter):
    """
    Génère un filtre pour ajouter les extras de log_type aux enregistrements de log.
    """
    def __init__(self, **extras: str):
        super().__init__()
        self.extras: dict[str, Any] = extras

    def filter(self, record: logging.LogRecord) -> bool:
        """Ajouter le log_type aux extras du record de log"""
        if not hasattr(record, "extra"):
            setattr(record, "extra", {})
        record.extra.setdefault("extra", {})    # type: ignore

        for key, value in self.extras.items():
            record.extra["extra"].setdefault(key, value)  # type: ignore

        return True


# Instance globale (singleton)
_logger = None  # pylint: disable=invalid-name


def setup_logging():
    """Configure le logging pour l'application."""
    root_logger = logging.getLogger()
    # éviter les doublons si reload Uvicorn/Gunicorn
    if any(isinstance(h, MongoForwardHandler) for h in root_logger.handlers):
        return
    handler = MongoForwardHandler(get_logger())
    root_logger.setLevel(LOG_LEVEL)
    root_logger.addHandler(handler)


def get_logger() -> MongoDBLogger:
    """Obtenir l'instance du logger MongoDB"""
    global _logger  # pylint: disable=global-statement
    if _logger is None:
        _logger = MongoDBLogger()
    return _logger
