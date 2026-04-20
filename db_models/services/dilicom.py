"""
Module contenant les services pour les opérations SFTP avec le serveur de Dilicom.
Ce module inclut:
- La classe `DilicomService` qui encapsule les opérations SFTP avec le serveur de Dilicom.
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import Sequence, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from dilicom_parser.transport import Connector
from dilicom_parser.classifier import FilesClassifier
from dilicom_parser.models import DistributorData
from db_models.objects.stocks import DilicomReferencial

class DilicomService:
    """
    Service pour les opérations SFTP avec le serveur de Dilicom.
    Cette classe utilise `Connector` pour gérer les connexions et les opérations SFTP.
    """
    def __init__(self, session: Session):
        self.session = session
        self.connect = Connector(env_path=".env.dilicom")
        self.classifier: FilesClassifier
        self.parser: list[Any] = []

    def send_updates(self) -> None:
        """
        Envoie les mises à jour des référentiels au serveur de Dilicom.
        Cette méthode récupère les données nécessaires dans la base de données,
        génère le fichier de mise à jour, et le transfère via SFTP.
        """
        txt_content: str | bool = self._build_refel_content(to_file=False)
        if isinstance(txt_content, bool):
            raise ValueError("Erreur lors de la création du fichier de mise à jour.")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H-%M-%S")
        filename = f"{self.connect.config.username}_MVT-REF_{timestamp}.txt"
        with self.connect as server:
            server.upload_from_memory(txt_content, filename)

    def fetch_returns(self) -> None:
        """
        Récupère les fichiers de retour du serveur de Dilicom.
        Cette méthode se connecte au serveur SFTP, télécharge les fichiers de retour,
        et les traite pour mettre à jour les statuts des commandes dans la base de données.
        """
        with self.connect as server:
            files_list = server.download_all(archive=False)
        self.classifier = FilesClassifier(files_list)
        objects_to_merge = self.classifier.classify().parse()
        match objects_to_merge.items():
            case {"distributor": distributor_list}:
                self._update_distributors(distributor_list)
            case {"eancom": eancom_list}:
                self._update_services(eancom_list)
            case {"gencod": gencod_list}:
                self._update_services(gencod_list)
            case _:
                message = "Aucun type de fichier reconnu dans les fichiers de retour."
                raise ValueError(message)

    def fetch_archives(self) -> list[Path]:
        """
        Récupère les fichiers d'archives du serveur de Dilicom.
        Cette méthode se connecte au serveur SFTP, télécharge les fichiers d'archives,
        et les stocke localement pour référence future.
        """
        with self.connect as server:
            files_list = server.download_all(archive=True)
        return files_list

    def _update_synced(self, references: Sequence[DilicomReferencial]):
        """
        Met à jour le statut de synchronisation des références dans la base de données.
        Cette méthode prend une liste de références, et met à jour leur champ `dilicom_synced`
        pour indiquer qu'elles ont été synchronisées avec le serveur de Dilicom.
        
        param :
            - references: La liste des références à mettre à jour.
        """
        for ref in references:
            ref.dilicom_synced = True
        self.session.commit()

    def _build_refel_content(self, to_file: bool = False) -> str | bool:
        """
        Construit le contenu du fichier de mise à jour (REFEL) à envoyer à Dilicom.
        Cette méthode récupère les données nécessaires dans la base de données,
        et formate le contenu selon les spécifications de Dilicom.
        """
        stmt = select(DilicomReferencial).where(DilicomReferencial.dilicom_synced == False) # pylint: disable=C0121
        try:
            unsynced_refs = self.session.execute(stmt).scalars().all()
            txt_content = "BEGIN|MAJREF|" + "\n".join(ref.to_pipe() for ref in unsynced_refs)
            if to_file:
                with open("refel.txt", "w", encoding="utf-8") as f:
                    f.write(txt_content)
                value_to_return = True
            else:
                value_to_return = txt_content
            self._update_synced(unsynced_refs)
            return value_to_return
        except Exception as e:
            message = f"Erreur lors de la construction du contenu REFEL: {e}"
            raise RuntimeError(message) from e

    def _update_book_from_return(self, return_data):
        """
        Met à jour les informations d'un livre dans la base de données en fonction des données
        extraites d'un fichier de retour. Cette méthode prend les données extraites du fichier
        de retour, et met à jour les statuts des commandes, les quantités disponibles, ou toute
        autre information pertinente dans la base de données.
        
        param :
            - return_data: Les données extraites du fichier de retour pour un livre spécifique.
        """
        m = f"La méthode _update_book_from_return doit être implémentée pour {return_data}."
        raise NotImplementedError(m)

    def _update_distributors(self, distributor_list: list[DistributorData]) -> None:
        """
        Met à jour les informations des distributeurs dans la base de données en fonction des
        données extraites d'un fichier de retour de type "distributor". Cette méthode prend une
        liste de données de distributeurs, et met à jour les informations correspondantes dans la
        base de données.
        
        param :
            - distributor_list: liste des données de distributeurs extraites du fichier de retour.
        """
        print("Données de distributeurs à mettre à jour:", distributor_list)
        m = "Méthode _update_distributors non implémentée."
        raise NotImplementedError(m)

    def _update_services(self, service_list: list[Any]) -> None:
        """
        Met à jour les informations des services dans la base de données en fonction des
        données extraites d'un fichier de retour de type "eancom" ou "gencod". Cette méthode prend
        une liste de données de services, et met à jour les informations correspondantes dans la
        base de données.
        
        param :
            - service_list: liste des données de services extraites du fichier de retour.
        """
        print("Données de services à mettre à jour:", service_list)
        m = "Méthode _update_services non implémentée."
        raise NotImplementedError(m)
