"""
Module de gestion des logs pour ingestion dans la base de données MongoDB.

Le module contient deux sous-modules :
- logger : Gestionnaire de logs MongoDB
- log_actions : Fonctions helper de logging métier

Usage dans un blueprint :
    from logs import logger, log_actions

    logger = logger.get_logger()
    log_actions.log_user_action(user_id="alice", action="login", ip_address=request.remote_addr)
"""

from .logger import get_logger, setup_logging
from .log_actions import (
    log_user_action,
    log_client_event,
    log_metier_event,
)

__all__ = [
    "log_user_action",
    "log_client_event",
    "log_metier_event",
    "get_logger",
    "setup_logging"
]
