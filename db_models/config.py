"""Module de configuration des modèles de base de données."""

from os import getenv
from dotenv import load_dotenv


class DBConfig:
    """Classe de configuration pour les modèles de base de données."""

    def __init__(self, prefix: str) -> None:
        load_dotenv()
        self.host = getenv(f"{prefix}_DB_HOST", None)
        self.port = getenv(f"{prefix}_DB_PORT", None)
        self.user = getenv(f"{prefix}_DB_USER", None)
        self.password = getenv(f"{prefix}_DB_PASSWORD", None)
        self.database = getenv(f"{prefix}_DB_DATABASE", None)
        if not self.__valid_config():
            raise ValueError("Configuration de la base de données invalide.")

    def __valid_config(self) -> bool:
        """Vérifie si la configuration est valide."""
        return all([self.host, self.port, self.user, self.password, self.database])

    def __repr__(self) -> str:
        """Représentation de l'objet DBConfig."""
        return (
            f"<DBConfig(host={self.host}, port={self.port}, user={self.user}, "
            f"database={self.database})>"
        )

    def get_connection_string(self) -> str:
        """Retourne la chaîne de connexion à la base de données."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
