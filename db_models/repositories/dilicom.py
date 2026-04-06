"""Repository pour les opérations liées à Dilicom."""

from datetime import datetime
from dataclasses import dataclass
from typing import List
from pathlib import Path
import paramiko
from db_models.config import load_dilicom_config, DilicomConfig
from db_models.services.decorators import retry_sftp
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


    def print_config(self) -> None:
        """Affiche la configuration de Dilicom utilisée par le repository."""
        print(self.config)


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
            logger.log_error(message=message,
                             exception=e,
                             user_id="background",
                             obj_metadata={
                                 "host": self.config.host,
                                 "port": self.config.port,
                                 "username": self.config.username,
                                        "error": str(e),
                                    })
            raise DilicomAuthenticationError(message) from e
        except paramiko.SSHException as e:
            message = f"✗ Erreur SSH lors de la connexion au serveur SFTP de Dilicom: {e}"
            logger.log_error(message=message,
                             exception=e,
                             user_id="background",
                             obj_metadata={
                                 "host": self.config.host,
                                 "port": self.config.port,
                                        "username": self.config.username,
                                        "error": str(e),
                                    })
            raise DilicomConnectionError(message) from e
        except Exception as e:
            message = f"✗ Erreur inattendue lors de la connexion au serveur SFTP de Dilicom: {e}"
            logger.log_error(message=message,
                             exception=e,
                             user_id="background",
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
                logger.log_client_event(client_id="background",
                                        event="✓ Client SFTP de Dilicom fermé avec succès",
                                        obj_metadata={
                                            "host": self.config.host,
                                            "port": self.config.port,
                                            "username": self.config.username,
                                        })
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
                logger.log_client_event(client_id="background",
                                        event="✓ Client SSH de Dilicom fermé avec succès",
                                        obj_metadata={
                                            "host": self.config.host,
                                            "port": self.config.port,
                                            "username": self.config.username,
                                        })
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

    @retry_sftp
    def upload(self, local_path: str, remote_path: str) -> None:
        """
        Télécharge un fichier vers le serveur SFTP de Dilicom.

        Args:
            local_path (str): Le chemin local du fichier à télécharger.
            remote_path (str): Le chemin distant où le fichier doit être téléchargé.
        """
        if not self.sftp:
            message = DilicomConnectionError().stdr_message()
            logger.log_error(message=message,
                             user_id="background",
                             obj_metadata={
                                 "host": self.config.host,
                                 "port": self.config.port,
                                 "username": self.config.username,
                             })
            raise DilicomConnectionError(message)
        try:
            self.sftp.put(local_path, remote_path)
            logger.log_client_event(client_id="background",
                                    event=f"✓ Fichier '{local_path}' téléchargé vers " \
                                          + f"'{remote_path}' sur le serveur SFTP de Dilicom",
                                    obj_metadata={
                                        "host": self.config.host,
                                        "port": self.config.port,
                                        "username": self.config.username,
                                        "local_path": local_path,
                                        "remote_path": remote_path,
                                    })
        except FileNotFoundError as e:
            message = f"Le fichier local '{local_path}' n'existe pas pour le téléversement."
            logger.log_error(message=message,
                             exception=e,
                             user_id="background",
                             obj_metadata={
                                 "host": self.config.host,
                                 "port": self.config.port,
                                 "username": self.config.username,
                                 "local_path": local_path,
                             })
            raise DilicomSFTPError(message) from e
        except Exception as e:
            message = f"Erreur lors du téléchargement du fichier '{local_path}' vers " \
                      f"'{remote_path}' sur le serveur SFTP de Dilicom: {e}"
            logger.log_error(message=message,
                             exception=e,
                             user_id="background",
                             obj_metadata={
                                 "host": self.config.host,
                                 "port": self.config.port,
                                 "username": self.config.username,
                                 "local_path": local_path,
                                 "remote_path": remote_path,
                             })
            raise DilicomSFTPError(message) from e


    @retry_sftp
    def upload_from_memory(self, content: str | bytes, remote_path: str) -> None:
        """
        Télécharge un contenu depuis la mémoire vers le serveur SFTP de Dilicom.

        Args:
            content (str | bytes): Le contenu à télécharger.
            remote_path (str): Le chemin distant où le contenu doit être téléchargé.
        """
        if not self.sftp:
            message = DilicomConnectionError().stdr_message()
            logger.log_error(
                message=message,
                user_id="background",
                obj_metadata={
                    "host": self.config.host,
                    "port": self.config.port,
                    "username": self.config.username,
                })
            raise DilicomConnectionError(message)
        try:
            with self.sftp.file(remote_path, 'w') as remote_file:
                if isinstance(content, str):
                    content = content.encode('utf-8')
                remote_file.write(content)
            logger.log_dilicom_event(
                event=f"✓ Contenu téléchargé vers '{remote_path}' sur le serveur SFTP de Dilicom",
                obj_metadata={
                    "host": self.config.host,
                    "port": self.config.port,
                    "username": self.config.username,
                    "remote_path": remote_path,
                    "content_size": len(content),
                })
        except Exception as e:
            message = f"Erreur lors du téléchargement de contenu vers '{remote_path}' " \
                      f"sur le serveur SFTP de Dilicom: {e}"
            logger.log_error(
                message=message,
                exception=e,
                user_id="background",
                obj_metadata={
                    "host": self.config.host,
                    "port": self.config.port,
                    "username": self.config.username,
                    "remote_path": remote_path,
                    "content_size": len(content),
                })
            raise DilicomSFTPError(message) from e

    @retry_sftp
    def download(self, remote_path: str | Path, local_path: str, archive: bool = False) -> None:
        """
        Télécharge un fichier depuis le serveur SFTP de Dilicom.

        Args:
            remote_path (str | Path): Le chemin distant du fichier à télécharger.
            local_path (str): Le chemin local où le fichier doit être téléchargé.
        """
        if not self.sftp:
            message = DilicomConnectionError().stdr_message()
            logger.log_error(message=message,
                             user_id="background",
                             obj_metadata={
                                 "host": self.config.host,
                                 "port": self.config.port,
                                 "username": self.config.username,
                             })
            raise DilicomConnectionError(message)
        try:
            if archive:
                remote_path = Path('./ARC') / remote_path \
                                if not str(remote_path).startswith('./') \
                                else remote_path
            else:
                remote_path = Path('./O') / remote_path \
                                if not str(remote_path).startswith('./') \
                                else remote_path
            self.sftp.get(str(remote_path), local_path)
            with open(local_path, 'rb') as f:
                content = f.read()
            if content:
                content = content[:100] + (b'...' + content[100:] if len(content) > 100 else b'')
            else:
                content = b''
            logger.log_dilicom_event(
                event=f"✓ Fichier '{remote_path}' téléchargé vers " \
                      + f"'{local_path}' depuis le serveur SFTP de Dilicom",
                obj_metadata={
                    "host": self.config.host,
                    "port": self.config.port,
                    "username": self.config.username,
                    "remote_path": str(remote_path),
                    "local_path": local_path,
                    "content_size": len(content),
                    "archive": archive,
                    "content_preview": content,
                })
        except FileNotFoundError as e:
            message = f"Le fichier distant '{remote_path}' n'existe pas pour le téléchargement."
            logger.log_error(message=message,
                             exception=e,
                             user_id="background",
                             obj_metadata={
                                 "host": self.config.host,
                                 "port": self.config.port,
                                 "username": self.config.username,
                                 "remote_path": remote_path,
                             })
            raise DilicomSFTPError(message) from e
        except Exception as e:
            message = f"Erreur lors du téléchargement du fichier '{remote_path}' vers " \
                      f"'{local_path}' depuis le serveur SFTP de Dilicom: {e}"
            logger.log_error(message=message,
                             exception=e,
                             user_id="background",
                             obj_metadata={
                                 "host": self.config.host,
                                 "port": self.config.port,
                                 "username": self.config.username,
                                 "remote_path": remote_path,
                                 "local_path": local_path,
                             })
            raise DilicomSFTPError(message) from e


    def list_files(self, remote_path: str = '.',
                   complete: bool = False) -> List[str] | List["RemoteFile"]:
        """Liste les fichiers présents dans un répertoire du serveur SFTP de Dilicom.
        Args:
            remote_path (str): Le chemin distant du répertoire à lister.
            complete (bool): Si True, retourne les attributs complets des fichiers
                                (nom, chemin, taille, date de modification).
                             Si False, retourne uniquement les noms de fichiers.
        Returns:
            List[str] | List[RemoteFile]:
                - Une liste des noms de fichiers présents dans le répertoire ou
                - Une liste d'objets RemoteFile si complete est True.
        """
        # Implémentation pour lister les fichiers présents dans un dossier du serveur SFTP
        if not self.sftp:
            message = DilicomConnectionError().stdr_message()
            logger.log_error(message=message,
                             user_id="background",
                             obj_metadata={
                                 "host": self.config.host,
                                 "port": self.config.port,
                                 "username": self.config.username,
                                 "remote_path": remote_path,
                             })
            raise DilicomConnectionError(message)
        try:
            if complete:
                remotefiles = []
                for attr in self.sftp.listdir_attr(remote_path):
                    filename = attr.filename
                    filepath = f"{remote_path}/{filename}"
                    size = attr.st_size
                    int_modified_time = attr.st_mtime
                    if int_modified_time:
                        modified_time = datetime.fromtimestamp(int_modified_time)
                    else:
                        modified_time = None
                    remotefiles.append(RemoteFile(filename=filename,
                                                 filepath=filepath,
                                                 size=size,
                                                 modified_time=modified_time))
                return remotefiles
            return self.sftp.listdir(remote_path)
        except FileNotFoundError as e:
            message = f"Le répertoire distant '{remote_path}' n'existe pas sur le serveur SFTP."
            logger.log_error(message=message,
                             exception=e,
                             user_id="background",
                             obj_metadata={
                                 "host": self.config.host,
                                 "port": self.config.port,
                                 "username": self.config.username,
                                 "remote_path": remote_path,
                             })
            raise DilicomSFTPError(message) from e
        except Exception as e:
            message = f"Erreur lors du listage dans le répertoire '{remote_path}' " \
                        + f"sur le serveur SFTP: {e}"
            logger.log_error(message=message,
                             exception=e,
                             user_id="background",
                             obj_metadata={
                                 "host": self.config.host,
                                 "port": self.config.port,
                                 "username": self.config.username,
                                 "remote_path": remote_path,
                             })
            raise DilicomSFTPError(message) from e


    def delete(self, remote_path: str) -> None:
        """
        Supprime un fichier du serveur SFTP de Dilicom.

        Args:
            remote_path (str): Le chemin distant du fichier à supprimer.
        """
        # Implémentation pour supprimer un fichier du serveur SFTP de Dilicom
        if not self.sftp:
            message = DilicomConnectionError().stdr_message()
            logger.log_error(message=message,
                             user_id="background",
                             obj_metadata={
                                 "host": self.config.host,
                                 "port": self.config.port,
                                 "username": self.config.username,
                                 "remote_path": remote_path,
                             })
            raise DilicomConnectionError(message)
        try:
            self.sftp.remove(remote_path)
        except FileNotFoundError as e:
            message = f"Le fichier distant '{remote_path}' n'existe pas pour la suppression."
            logger.log_error(message=message,
                             exception=e,
                             user_id="background",
                             obj_metadata={
                                 "host": self.config.host,
                                 "port": self.config.port,
                                 "username": self.config.username,
                                 "remote_path": remote_path,
                             })
            raise DilicomSFTPError(message) from e
        except Exception as e:
            message = f"Erreur lors de la suppression du fichier '{remote_path}' " \
                      f"sur le serveur SFTP de Dilicom: {e}"
            logger.log_error(message=message,
                             exception=e,
                             user_id="background",
                             obj_metadata={
                                 "host": self.config.host,
                                 "port": self.config.port,
                                 "username": self.config.username,
                                 "remote_path": remote_path,
                             })
            raise DilicomSFTPError(message) from e


    def __enter__(self):
        """Permet d'utiliser le repository dans un contexte de gestion de ressources."""
        self.connect()
        return self


    def __exit__(self, exc_type, exc_value, traceback):
        """Ferme automatiquement la connexion lorsque le contexte est quitté."""
        self.close()


class DilicomConnectionError(Exception):
    """
    Exception levée en cas d'erreur de connexion au serveur SFTP de Dilicom.
    """
    def stdr_message(self):
        """
        Message d'erreur standard pour les problèmes de connexion au serveur SFTP de Dilicom.
        """
        return "Connexion SFTP non établie. Connectez-vous avant de télécharger un fichier."


class DilicomAuthenticationError(Exception):
    """
    Exception levée en cas d'erreur d'authentification au serveur SFTP de Dilicom.
    """
    def stdr_message(self):
        """
        Message d'erreur standard pour les problèmes d'authentification au serveur SFTP de Dilicom.
        """
        return "Erreur d'authentification au serveur SFTP de Dilicom."


class DilicomSFTPError(Exception):
    """
    Exception levée en cas d'erreur lors des opérations SFTP avec le serveur de Dilicom.
    """
    def stdr_message(self):
        """
        Message d'erreur standard pour les problèmes lors des opérations SFTP avec le serveur.
        """
        return "Erreur lors des opérations SFTP avec le serveur de Dilicom."


@dataclass
class RemoteFile:
    """
    Classe représentant un fichier distant sur le serveur SFTP de Dilicom.
    
    Attributes:
         filename (str): Le nom du fichier.
         filepath (str): Le chemin complet du fichier sur le serveur SFTP.
         size (int | None): La taille du fichier en octets, ou None si non disponible.
         modified_time (datetime | None): La date et l'heure de la dernière modification du fichier,
                                          ou None si non disponible.
    """
    filename: str
    filepath: str
    size: int | None
    modified_time: datetime | None

    def __str__(self):
        return f"RemoteFile(filename='{self.filename}', filepath='{self.filepath}', " \
               f"size={self.size}, modified_time={self.modified_time})"
