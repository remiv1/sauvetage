"""
Module de décorateurs pour la gestion des accès aux routes internes.
Ce module contient des décorateurs pour sécuriser les routes internes de l'API,
en vérifiant les tokens d'accès et les adresses IP autorisées.
"""

from fastapi import Request, HTTPException
from app_back.config.security import get_security_token

INTERNAL_TOKEN = get_security_token()  # Récupère le token de sécurité depuis la configuration
ALLOWED_IPS = {"127.0.0.1", "10.0.0.5"}  # exemple

def access_control(restrict_ip: bool = False):
    """
    Décorateur pour contrôler l'accès aux routes internes.
    Ce décorateur vérifie la présence d'un token d'accès valide dans les en-têtes de la requête,
    et peut également restreindre l'accès à certaines adresses IP.
    Args:
        restrict_ip (bool): Si True, restreint l'accès aux adresses IP spécifiées dans ALLOWED_IPS.
    """
    def wrapper(request: Request):
        # Vérification du token
        token = request.headers.get("X-Internal-Token")
        if token != INTERNAL_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid token")

        # Vérification IP si demandé
        if restrict_ip:
            if request.client is None:
                raise HTTPException(status_code=400, detail="Unable to determine client IP")
            client_ip = request.client.host
            if client_ip not in ALLOWED_IPS:
                raise HTTPException(status_code=403, detail="IP not allowed")

        return True
    return wrapper
