"""Module des utilitaires pour les échanges avec Henrri."""

from typing import Optional
from os import getenv
from dataclasses import dataclass

@dataclass
class HenrriConfig:
    """Configuration pour les échanges avec Henrri."""
    api_key: str = getenv("HENRRI_API_KEY", "")
    api_url: Optional[str] = getenv("HENRRI_API_URL", None)
    api_secret: str = getenv("HENRRI_API_SECRET", "")
