"""
Fonctions helper de logging métier.

Chaque fonction correspond à un log_type MongoDB et appelle le logger Python standard
avec le bon extra dict. MongoForwardHandler se charge ensuite de router vers la bonne
collection (ex: 2026-users, 2026-clients, 2026-métiers).

Usage dans un blueprint :
    from logs.log_actions import log_user_action, log_client_event, log_metier_event

    log_user_action(user_id="alice", action="login", ip_address=request.remote_addr)
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("app_front")

# ---------------------------------------------------------------------------
# Collection : 2026-users
# Qui  : actions des utilisateurs internes (connexion, déconnexion, CRUD user…)
# ---------------------------------------------------------------------------

def log_user_action(
    *,
    user_id: str,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    status_code: Optional[int] = None,
    obj_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Trace une action d'un utilisateur interne (login, logout, création, etc.).

    Args:
        user_id:       Identifiant de l'utilisateur (ex: session["username"])
        action:        Verbe décrivant l'action (ex: "login", "logout", "create_user")
        resource_type: Type de ressource concernée (ex: "user", "order")
        resource_id:   Identifiant de la ressource (ex: str(user.id))
        ip_address:    IP de la requête (request.remote_addr)
        status_code:   Code HTTP de la réponse (ex: 200, 403)
        obj_metadata:  Données contextuelles libres (ex: {"permissions": "ADMIN"})
    """
    logger.info(
        "User action: %s → %s",
        user_id,
        action,
        extra={
            "log_type": "users",
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "ip_address": ip_address,
            "status_code": status_code,
            "obj_metadata": obj_metadata or {},
        },
    )


# ---------------------------------------------------------------------------
# Collection : 2026-clients
# Qui  : événements liés aux clients (création, modification, push WC…)
# ---------------------------------------------------------------------------

def log_client_event(
    *,
    client_id: str,
    event: str,
    user_id: Optional[str] = None,
    resource_type: str = "client",
    ip_address: Optional[str] = None,
    status_code: Optional[int] = None,
    obj_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Trace un événement sur un client (création, modification, sync WooCommerce…).

    Args:
        client_id:     Identifiant du client concerné (ex: str(customer_id))
        event:         Description de l'événement (ex: "create", "wc_push")
        user_id:       Utilisateur interne à l'origine de l'action
        resource_type: Type de ressource (défaut : "client")
        ip_address:    IP de la requête
        status_code:   Code HTTP de la réponse
        obj_metadata:  Données contextuelles libres (ex: {"wc_id": 42})
    """
    logger.info(
        "Client event: %s → %s",
        client_id,
        event,
        extra={
            "log_type": "clients",
            "user_id": user_id,
            "action": event,
            "resource_type": resource_type,
            "resource_id": client_id,
            "ip_address": ip_address,
            "status_code": status_code,
            "obj_metadata": obj_metadata or {},
        },
    )


# ---------------------------------------------------------------------------
# Collection : 2026-métiers
# Qui  : événements métier automatiques (Dilicom, imports, tâches planifiées…)
# ---------------------------------------------------------------------------

def log_metier_event(
    *,
    event: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    status_code: Optional[int] = None,
    obj_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Trace un événement métier (import Dilicom, synchronisation stock, etc.).

    Args:
        event:         Description de l'événement (ex: "dilicom_import", "stock_sync")
        resource_type: Catégorie métier (ex: "dilicom", "stock", "order")
        resource_id:   Identifiant de la ressource traitée (ex: ISBN, order_id)
        user_id:       Utilisateur déclencheur si manuel (None si automatique)
        status_code:   Code HTTP ou code de retour de l'opération
        obj_metadata:  Données contextuelles libres (ex: {"nb_records": 150})
    """
    logger.info(
        "Metier event: %s → %s",
        resource_type,
        event,
        extra={
            "log_type": "métiers",
            "user_id": user_id,
            "action": event,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "status_code": status_code,
            "obj_metadata": obj_metadata or {},
        },
    )
