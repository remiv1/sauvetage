"""Module de configuration pour l'intégration avec Dilicom."""

from os import getenv
from dataclasses import dataclass

@dataclass
class DilicomConfig:
    """Classe de configuration pour l'intégration avec Dilicom."""
    host: str
    port: int
    username: str
    password: str

def load_dilicom_config() -> DilicomConfig:
    """Charge la configuration de Dilicom à partir des variables d'environnement."""
    return DilicomConfig(
        host=getenv("DILICOM_HOST", "sftp.dilicom.com"),
        port=int(getenv("DILICOM_PORT", "22")),
        username=getenv("DILICOM_ID", "your_username"),
        password=getenv("DILICOM_SECRET", "your_password"),
    )
