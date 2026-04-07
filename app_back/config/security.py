"""
Module de configuration de la sécurité pour l'API interne.
Ce module contient les fonctions et les configurations nécessaires pour sécuriser les routes
internes de l'API, notamment la gestion des tokens d'accès et des restrictions d'IP.
"""

from os import getenv

def get_security_token() -> str:
    """Récupère le token de sécurité depuis les variables d'environnement."""
    token = getenv("SECURITY_TOKEN")
    if not token:
        raise ValueError("Le token de sécurité n'est pas défini dans les variables.")
    return token
