"""
Module contenant les services pour les opérations SFTP avec le serveur de Dilicom.
Ce module inclut:
- La classe `DilicomService` qui encapsule les opérations SFTP avec le serveur de Dilicom.
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import Sequence, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from dilicom_parser.transport import Connector
from dilicom_parser.classifier import FilesClassifier
from dilicom_parser.models import DistributorData
from db_models.objects.stocks import DilicomReferencial
from db_models.repositories.suppliers import SuppliersRepository, Suppliers


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

        if not objects_to_merge:
            message = "Aucun type de fichier reconnu dans les fichiers de retour."
            raise ValueError(message)

        if "distributor" in objects_to_merge:
            self._update_distributors(objects_to_merge["distributor"])
        if "eancom" in objects_to_merge:
            self._update_services(objects_to_merge["eancom"])
        if "gencod" in objects_to_merge:
            self._update_services(objects_to_merge["gencod"])

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
        suppliers_list: list[Suppliers] = []
        for d in distributor_list:
            for l in d.lines:
                b1, b2, _ = l.bloc1, l.bloc2, l.bloc3
                global_address = "".join(
                        [b1.numero_voie or "", b1.adresse_l1 or "", b1.adresse_l2 or "",
                        b1.adresse_l3 or "", b1.code_postal or "", b1.ville or "", b1.pays or ""]
                    )
                s = Suppliers(
                    name=b1.rs1,
                    gln13=b1.gln,
                    siren_siret=b1.siren_or_siret,
                    vat_number=b1.num_tva_intracom,
                    address=global_address,
                    contact_email=b1.email,
                    contact_phone=b1.num_tel,
                    contact_fax=b1.num_fax,
                    web_site=b1.website,
                    is_active=b1.gln_repreneur is None,
                    edi_active=b2.type_connection == "02",
                    collect_days=__convert_collect_days(b2.jours_collecte),
                    cutoff_time=__convert_cutoff_time(b2.heure_limite),
                )
                suppliers_list.append(s)
        repo = SuppliersRepository(self.session)
        repo.sync_supplier(suppliers_list)

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

def __convert_collect_days(collect_days_str: Optional[str]) -> Optional[str]:
    """
    Convertit une chaîne de caractères représentant les jours de collecte binaire en une chaîne
    de rang de jours de la semaine (1-7). Par exemple, "1010100" devient "135".
    """
    if collect_days_str is None:
        return None
    return "".join(str(i) for i, bit in enumerate(collect_days_str, start=1) if bit == "1")

def __convert_cutoff_time(cutoff_time_str: Optional[str]) -> Optional[str]:
    """
    Convertit une chaîne de caractères représentant l'heure limite de collecte au format "HHMM"
    en une chaîne au format "HH:MM". Par exemple, "1730" devient "17:30".
    """
    if cutoff_time_str is None or len(cutoff_time_str) != 4:
        return None
    return f"{cutoff_time_str[:2]}:{cutoff_time_str[2:]}"
