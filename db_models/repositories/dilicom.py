"""Repository pour les opérations liées à Dilicom."""

from typing import List
import paramiko
from db_models.config import load_dilicom_config, DilicomConfig
from logs.logger import get_logger

logger = get_logger()

class DilicomRepository:
    """
    Repository pour les opérations liées à Dilicom.
    Attributes:
        direction (str): La direction de l'opération, par défaut "put".
    """

    def __init__(self, timeout: int = 30):
        self.config: DilicomConfig = load_dilicom_config()  # Charger la configuration de Dilicom
        self.timeout = timeout  # Timeout pour la connexion SFTP
        self.client = None  # Client SSH pour la connexion SFTP
        self.transport = None  # Transport SSH pour la connexion SFTP
        self.sftp = None  # Client SFTP

    def __str__(self):
        return f"""
        <DilicomRepository(\n
            - username={self.config.username},\n
            - host={self.config.host},\n
            - port={self.config.port},\n
            - password={'****' if self.config.password else None})>
        """

    def __repr__(self):
        return self.__str__()

    def connect(self) -> None:
        """Établit une connexion au serveur SFTP de Dilicom."""
        try:
            # 1. client SSH
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # 2. connection SSH
            self.client.connect(
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
                allow_agent=False,
                look_for_keys=False,
                timeout=self.timeout,
                banner_timeout=self.timeout,
                auth_timeout=self.timeout,
            )
            # 3. récupération du transport SSH
            self.transport = self.client.get_transport()
            if self.transport is None:
                raise DilicomConnectionError("Transport SSH indisponible pour la connexion SFTP.")
            opts = self.transport.get_security_options()
            # 4. forcer les algorithmes legacy de Dilicom
            opts.kex = ["diffie-hellman-group1-sha1"]
            opts.ciphers = ["aes128-cbc", "3des-cbc"]
            opts.digests = ["hmac-sha1"]
            opts.key_types = ["ssh-rsa"]
            # 5. ouverture du client SFTP
            self.sftp = self.client.open_sftp()
            logger.log_client_event(client_id="background",
                                    event="✓ Connexion réussie au serveur SFTP de Dilicom",
                                    obj_metadata={
                                        "host": self.config.host,
                                        "port": self.config.port,
                                        "username": self.config.username,
                                    })
        except paramiko.AuthenticationException as e:
            message = f"✗ Erreur d'authentification au serveur SFTP de Dilicom: {e}"
            logger.log_client_event(client_id="background",
                                    event=message,
                                    obj_metadata={
                                        "host": self.config.host,
                                        "port": self.config.port,
                                        "username": self.config.username,
                                        "error": str(e),
                                    })
            raise DilicomAuthenticationError(message) from e
        except paramiko.SSHException as e:
            message = f"✗ Erreur SSH lors de la connexion au serveur SFTP de Dilicom: {e}"
            logger.log_client_event(client_id="background",
                                    event=message,
                                    obj_metadata={
                                        "host": self.config.host,
                                        "port": self.config.port,
                                        "username": self.config.username,
                                        "error": str(e),
                                    })
            raise DilicomConnectionError(message) from e
        except Exception as e:
            message = f"✗ Erreur inattendue lors de la connexion au serveur SFTP de Dilicom: {e}"
            logger.log_client_event(client_id="background",
                                    event=message,
                                    obj_metadata={
                                        "host": self.config.host,
                                        "port": self.config.port,
                                        "username": self.config.username,
                                        "error": str(e),
                                    })
            raise DilicomConnectionError(message) from e

    def close(self) -> None:
        """Ferme la connexion au serveur SFTP de Dilicom."""
        if self.sftp:
            try:
                self.sftp.close()
            except Exception as e:
                message = f"Erreur lors de la fermeture du client SFTP de Dilicom: {e}"
                logger.log_error(message=message,
                                 exception=e,
                                 user_id="background",
                                 obj_metadata={
                                     "host": self.config.host,
                                     "port": self.config.port,
                                     "username": self.config.username,
                                     "error": str(e),
                                 })
                raise DilicomSFTPError(message) from e

        if self.client:
            try:
                self.client.close()
            except Exception as e:
                message = f"Erreur lors de la fermeture du client SSH de Dilicom: {e}"
                logger.log_error(message=message,
                                 exception=e,
                                 user_id="background",
                                 obj_metadata={
                                     "host": self.config.host,
                                     "port": self.config.port,
                                     "username": self.config.username,
                                     "error": str(e),
                                 })
                raise DilicomSFTPError(message) from e

        self.sftp = None
        self.client = None
        self.transport = None
    def upload(self, local_path: str, remote_path: str) -> None:
        """Télécharge un fichier vers le serveur SFTP de Dilicom.
        Args:
            local_path (str): Le chemin local du fichier à télécharger.
            remote_path (str): Le chemin distant où le fichier doit être téléchargé.
        """
        # Implémentation pour télécharger un fichier vers le serveur SFTP de Dilicom
        pass

    def download(self, remote_path: str, local_path: str) -> None:
        """Télécharge un fichier depuis le serveur SFTP de Dilicom.
        Args:
            remote_path (str): Le chemin distant du fichier à télécharger.
            local_path (str): Le chemin local où le fichier doit être téléchargé.
        """
        # Implémentation pour télécharger un fichier depuis le serveur SFTP de Dilicom
        pass

    def list_files(self, remote_path: str) -> List[str]:
        """Liste les fichiers présents dans un répertoire du serveur SFTP de Dilicom.
        Args:
            remote_path (str): Le chemin distant du répertoire à lister.
        Returns:
            List[str]: Une liste des noms de fichiers présents dans le répertoire.
        """
        # Implémentation pour lister les fichiers présents dans un dossier du serveur SFTP
        pass

    def delete(self, remote_path: str) -> None:
        """Supprime un fichier du serveur SFTP de Dilicom.
        Args:
            remote_path (str): Le chemin distant du fichier à supprimer.
        """
        # Implémentation pour supprimer un fichier du serveur SFTP de Dilicom
        pass

    def __enter__(self):
        """Permet d'utiliser le repository dans un contexte de gestion de ressources."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Ferme automatiquement la connexion lorsque le contexte est quitté."""
        self.close()


class DilicomConnectionError(Exception):
    """Exception levée en cas d'erreur de connexion au serveur SFTP de Dilicom."""
    pass    # pylint: disable=unnecessary-pass

class DilicomAuthenticationError(Exception):
    """Exception levée en cas d'erreur d'authentification au serveur SFTP de Dilicom."""
    pass    # pylint: disable=unnecessary-pass

class DilicomSFTPError(Exception):
    """Exception levée en cas d'erreur lors des opérations SFTP avec le serveur de Dilicom."""
    pass    # pylint: disable=unnecessary-pass
