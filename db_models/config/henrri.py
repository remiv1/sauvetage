"""Module de configuration pour l'intégration avec Henrri."""

from os import getenv
from dataclasses import dataclass

@dataclass
class HenrriConfig:
    """Classe de configuration pour l'intégration avec Henrri."""
    base_url: str
    api_key: str
    api_secret: str

def load_henrri_config() -> HenrriConfig:
    """Charge la configuration de Henrri à partir des variables d'environnement."""
    return HenrriConfig(
        base_url=getenv("HENRRI_BASE_URL", "https://api.henrri.com"),
        api_key=getenv("HENRRI_API_KEY", "your_api_key"),
        api_secret=getenv("HENRRI_API_SECRET", "your_api_secret"),
    )
