"""Configuration du projet Flask"""

from typing import Dict, Any, List, Optional
from os import getenv
import requests

_TIMEOUT = 30  # secondes
PROTOCOLE = "http"  # pas de protocole HTTPS si un seul pod.

API_URL = getenv("API_URL", f"{PROTOCOLE}://app-back:8000/api/v1")
USERS: Dict[str, str] = {
    "no_users": f"{API_URL}/users/no-user",
    "login": f"{API_URL}/users/login",
    "validate_session": f"{API_URL}/users/validate-session",
    "logout": f"{API_URL}/users/logout",
    "create": f"{API_URL}/users/create",
    "change_password": f"{API_URL}/users/change-password",
    "search": f"{API_URL}/users/search",
    "modify": f"{API_URL}/users/modify",
    "list": f"{API_URL}/users/list",
    "toggle_lock": f"{API_URL}/users/toggle-lock",
    "toggle_active": f"{API_URL}/users/toggle-active",
}
INVENTORY: Dict[str, str] = {
    "parse": f"{API_URL}/inventory/parse",
    "unknown_products": f"{API_URL}/inventory/unknown-products",
    "prepare": f"{API_URL}/inventory/prepare",
    "validate": f"{API_URL}/inventory/validate",
    "commit": f"{API_URL}/inventory/commit",
    "status": f"{API_URL}/inventory/status",
}
DILICOM: Dict[str, Any] = {
    "orders": {
        "send": f"{API_URL}/dilicom/orders/send",
    }
}
MAILS: Dict[str, str] = {
    "create": f"{API_URL}/mails/create",
    "send_supplier_order": f"{API_URL}/mails/send-order",
}
DOCUMENTS: Dict[str, str] = {
    "create": f"{API_URL}/documents/create",
}
WOO_COMMERCE: Dict[str, str] = {
    "sync_catalog": f"{API_URL}/woo-commerce/background/sync-catalog",
    "sync_orders": f"{API_URL}/woo-commerce/background/sync-orders",
    "reconcile_vat_rates": f"{API_URL}/woo-commerce/background/reconcile-vat-rates",
}

def post(path: str, payload: Dict[str, Any] | List[Any]) -> Dict[str, Any]:
    """POST JSON vers le micro-service FastAPI (opérations lourdes uniquement)."""
    url = path
    try:
        resp = requests.post(url, json=payload, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Erreur de communication avec le service d'inventaire : {exc}"
        ) from exc


def get(path: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """GET vers le micro-service FastAPI (opérations lourdes uniquement)."""
    url = path
    try:
        resp = requests.get(url, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Erreur de communication avec le service d'inventaire : {exc}"
        ) from exc
