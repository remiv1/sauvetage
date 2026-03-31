"""Configuration du projet Flask"""

from typing import Dict, Any, List, Optional
from os import getenv
import requests

_TIMEOUT = 30  # secondes

API_URL = getenv("API_URL", "http://app-back:8000/api/v1")
USERS: Dict[str, str] = {
    "no_users": f"{API_URL}/users/no-user",
    "login": f"{API_URL}/users/login",
    "create": f"{API_URL}/users/create",
    "change_password": f"{API_URL}/users/change-password",
    "search": f"{API_URL}/users/search",
    "modify": f"{API_URL}/users/modify",
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
}
DOCUMENTS: Dict[str, str] = {
    "create": f"{API_URL}/documents/create",
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
