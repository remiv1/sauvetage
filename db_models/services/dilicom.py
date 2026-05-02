"""
Module contenant les services pour les opérations SFTP avec le serveur de Dilicom.
Ce module inclut:
- La classe `DilicomService` qui encapsule les opérations SFTP avec le serveur de Dilicom.
"""

from os import getenv
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Sequence, Any, Optional, cast
from sqlalchemy.orm import Session
from sqlalchemy import select
from dilicom_parser.transport import Connector
from dilicom_parser.classifier import FilesClassifier
from dilicom_parser.models import DistributorData, DistributorLineData
from db_models.objects.stocks import DilicomReferencial
from db_models.repositories.suppliers import SuppliersRepository, Suppliers
from onixlib import Notice
from db_models.repositories.objects import (
    ObjectsRepository,
    GeneralObjects,
    Books,
    ObjMetadatas,
)
from db_models.repositories.suppliers import SuppliersRepository, Suppliers

logger = logging.getLogger("app_back.services.dilicom")

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
        self.objects_repo = ObjectsRepository(self.session)
        self.supplier_repo = SuppliersRepository(self.session)

    def send_updates(self) -> None:
        """
        Envoie les mises à jour des référentiels au serveur de Dilicom.
        Cette méthode récupère les données nécessaires dans la base de données,
        génère le fichier de mise à jour, et le transfère via SFTP.
        """
        txt_content: str | bool = self._build_refel_content(to_file=False)
        byte_content = txt_content.encode(encoding="utf-8") \
                            if isinstance(txt_content, str) \
                            else None
        logger.debug("Contenu du fichier de mise à jour (REFEL) généré: %s", txt_content)
        if isinstance(txt_content, bool):
            raise ValueError("Erreur lors de la création du fichier de mise à jour.")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H-%M-%S")
        filename = f"{self.connect.config.username}_MVT-REF_{timestamp}.txt"
        logger.info(
            "Envoi du fichier de mise à jour (REFEL) au serveur de Dilicom avec le nom: %s",
            filename
        )
        remote_path = str(Path('/I') / filename)
        with self.connect as server:
            server.upload_from_memory(byte_content, remote_path=remote_path)
            logger.info(
                "REF FEL envoyé avec succès au serveur de Dilicom à l'emplacement: %s",
                remote_path,
            )

    def fetch_returns(self, archives: bool = False) -> None:
        """
        Récupère les fichiers de retour du serveur de Dilicom.
        Cette méthode se connecte au serveur SFTP, télécharge les fichiers de retour,
        et les traite pour mettre à jour les statuts des commandes dans la base de données.
        """
        # Vidage du dossier local de réception avant téléchargement pour éviter les confusions
        local_dir = Path(getenv("DILICOM_IN_DIR", "dilicom_returns"))
        self._clear_directory(local_dir)
        with self.connect as server:
            files_list = server.download_all(archive=archives)
        logger.debug(
            "Fichiers téléchargés de Dilicom: %s",
            [file.name for file in files_list]
            )
        self.classifier = FilesClassifier(files_list, streaming_option=True)
        objects_to_merge = self.classifier.classify().parse()
        books_to_merge = self.classifier.heavy_files
        total_by_type = self.classifier.count_by_type()
        total_by_type["books"] = len(books_to_merge)
        logger.info(
            "objets trouvés après classification et parsing: %s",
            total_by_type.values()
        )
        if not books_to_merge and not objects_to_merge:
            message = "Aucun fichier de retour trouvé ou reconnu après classification."
            logger.warning(message)
            raise FileNotFoundError(message)
        if not objects_to_merge:
            message = "Aucun type de fichier reconnu dans les fichiers de retour."
            logger.warning(message)
        elif not books_to_merge:
            message = "Aucun fichier de type 'books' trouvé dans les fichiers de retour."
            logger.warning(message)

        if "distributor" in objects_to_merge:
            self._update_distributors(objects_to_merge["distributor"])
        if "eancom" in objects_to_merge:
            self._update_services(objects_to_merge["eancom"])
        if "gencod" in objects_to_merge:
            self._update_services(objects_to_merge["gencod"])
        if books_to_merge:
            self._update_books(books_to_merge)

        # Suppression des fichiers locaux après traitement
        for file in files_list:
            try:
                file.unlink()
                logger.info("Fichier %s supprimé avec succès après traitement.", file.name)
            except (FileNotFoundError, RuntimeError) as e:
                logger.error("Erreur lors de la suppression du fichier %s: %s", file, e)

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
            if not unsynced_refs:
                logger.info(
                    "Rien à synchroniser avec Dilicom, REF-FEL non généré.",
                    )
                return False
            txt_content = "BEGIN|MAJREF|\n"  \
                            + "\n".join(ref.to_pipe() for ref in unsynced_refs) \
                            + "\n"
            if to_file:
                with open("refel.txt", "w", encoding="utf-8") as f:
                    f.write(txt_content)
                value_to_return = True
            else:
                value_to_return = txt_content
            self._update_synced(unsynced_refs)
            logger.info(
                "Contenu du fichier REFEL construit avec succès. Nombre de références incluses: %d",
                len(unsynced_refs)
            )
            return value_to_return
        except Exception as e:
            message = f"Erreur lors de la construction du contenu REFEL: {e}"
            raise RuntimeError(message) from e

    def _update_books(self, books_list: list[Path]) -> None:
        """
        Met à jour les informations des livres dans la base de données en fonction des
        données extraites d'un fichier de retour de type "books". Cette méthode prend une
        liste de données de livres, et met à jour les informations correspondantes dans la
        base de données.
        
        param :
            - books_list: liste des données de livres extraites du fichier de retour.
        """
        def _deep_getattr(obj: object, attr_path: str, default: str="N/A") -> str | object:
            for attr in attr_path.split("."):
                try:
                    obj = getattr(obj, attr)
                except AttributeError:
                    return default
            return str(obj)


        for book_file in books_list:
            logger.debug(
                "Traitement du fichier de livres: %s",
                book_file.name
            )
            for product in Notice.parse_full(book_file, version="3.0").products:
                isbn = _deep_getattr(product, "isbn")
                title = _deep_getattr(product, "title")
                supplier_gln = cast(str, _deep_getattr(product, "publisher.gln"))
                editor_gln = cast(str, _deep_getattr(product, "editor.gln"))
                description = _deep_getattr(product, "collateral.description")
                price_ht = cast(float, _deep_getattr(product, "price.ht", default="0.0"))
                vat_rate = cast(float, _deep_getattr(product, "price.vat_rate", default="0.0"))
                authors = _deep_getattr(product, "authors")
                authors = [a.full_name for a in authors if hasattr(a, "full_name")] \
                                if isinstance(authors, list) \
                                else []
                authors_str = ", ".join(authors) if authors else ""
                logger.debug("Mise à jour du livre avec ISBN %s et titre %s", isbn, title)
                supplier_match = self.supplier_repo.get_by_gln13(supplier_gln)
                editor_match = self.supplier_repo.get_by_gln13(editor_gln)
                vat_rate_id = self.objects_repo.get_vat_rate_id(vat_rate)
                if not supplier_match or not editor_match:
                    logger.info("Création d'un nouveau fournisseur %s nécessaire.", supplier_gln)
                    break
                supplier_id = supplier_match.id
                g_o = GeneralObjects(
                    supplier_id=supplier_id,
                    general_object_type="book",
                    ean13=isbn,
                    name=title,
                    description=description,
                    price=float(price_ht),
                    purchase_price=None,
                    vat_rate_id=vat_rate_id,
                    )
                b = Books(
                    author=authors_str,
                    diffuser=supplier_match.name,
                    editor=editor_match.name,
                    genre="",
                    publication_year=None,
                    pages=None,
                )
                metadatas: dict[str, str] = {}

                self.objects_repo.save_or_update_from_object(g_o, b)


    def _update_distributors(self, distributor_list: list[DistributorData]) -> None:
        """
        Met à jour les informations des distributeurs dans la base de données en fonction des
        données extraites d'un fichier de retour de type "distributor". Cette méthode prend une
        liste de données de distributeurs, et met à jour les informations correspondantes dans la
        base de données.
        
        param :
            - distributor_list: liste des données de distributeurs extraites du fichier de retour.
        """
        repo = SuppliersRepository(self.session)
        suppliers_dict: dict[str, Suppliers] = {}
        for d in distributor_list:
            for l in d.lines:
                s = self.__generate_supplier_from_distributor_line(l)
                if s:
                    logger.debug(
                        "Ajout du fournisseur %s avec GLN %s au dictionnaire.",
                        s.name,
                        s.gln13
                    )
                    suppliers_dict[s.gln13] = s
            repo.sync_supplier(list(suppliers_dict.values()))

    def _clear_directory(self, directory: Path) -> None:
        """
        Supprime tous les fichiers d'un répertoire donné. Cette méthode prend un objet `Path`
        représentant le répertoire à nettoyer, et supprime tous les fichiers qu'il contient.
        
        param :
            - directory: Le répertoire à nettoyer.
        """
        if directory.exists() and directory.is_dir():
            for file in directory.iterdir():
                if file.is_file():
                    try:
                        file.unlink()
                        logger.info(
                            "Fichier %s supprimé avec succès dans le répertoire %s.",
                            file.name,
                            directory
                        )
                    except (FileNotFoundError, RuntimeError) as e:
                        logger.error(
                            "Erreur lors de la suppression du fichier %s dans le répertoire %s: %s",
                            file.name,
                            directory,
                            e
                        )

    def __generate_supplier_from_distributor_line(
            self, line: DistributorLineData
        ) -> Optional[Suppliers]:
        """
        Génère un objet `Suppliers` à partir d'une ligne de données de distributeur.
        Cette méthode prend une ligne de données de distributeur, et crée un objet `Suppliers`
        avec les informations correspondantes, en fonction du type de mouvement (mvt) indiqué
        dans la ligne.
        
        param :
            - line: La ligne de données de distributeur à partir de laquelle générer
                    l'objet `Suppliers`.
        """
        l = _clean_fields_in_lines(line)
        b1, b2, _ = l.bloc1, l.bloc2, l.bloc3
        global_address = _generate_address_from_distributor_line(line)
        if b1.mvt in ["00", "01", "03", "04"]:
            logger.debug(
                "Génération d'un objet Suppliers pour le distributeur %s avec mvt %s",
                b1.rs1,
                b1.mvt
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
                is_active=True,
                edi_active=b2.type_connection == "02",
                collect_days=_convert_collect_days(b2.jours_collecte),
                cutoff_time=_convert_cutoff_time(b2.heure_limite),
            )
        elif b1.mvt == "05":
            logger.debug(
                "Génération d'un objet Suppliers bloc 1 pour le distributeur %s avec mvt %s",
                b1.rs1,
                b1.mvt
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
                is_active=bool(b1.gln_repreneur),
            )
        elif b1.mvt == "06":
            logger.debug(
                "Génération d'un objet Suppliers bloc 2 pour le distributeur %s avec mvt %s",
                b1.rs1,
                b1.mvt
            )
            s = Suppliers(
                gln13=b1.gln,
                edi_active=b2.type_connection == "02",
                collect_days=_convert_collect_days(b2.jours_collecte),
                cutoff_time=_convert_cutoff_time(b2.heure_limite),
            )
        elif b1.mvt == "08":
            logger.debug(
                "Génération d'un objet Suppliers pour suppression du distributeur %s avec mvt %s",
                b1.rs1,
                b1.mvt
            )
            s = Suppliers(
                gln13=b1.gln,
                is_active=False,
            )
        else:
            logger.warning(
                "Mouvement (mvt) non reconnu %s pour le distributeur %s, aucune action réalisée.",
                b1.mvt,
                b1.rs1
            )
            s = None
        return s

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

def _convert_collect_days(collect_days_str: Optional[str]) -> Optional[str]:
    """
    Convertit une chaîne de caractères représentant les jours de collecte binaire en une chaîne
    de rang de jours de la semaine (1-7). Par exemple, "1010100" devient "135".
    """
    if collect_days_str is None or collect_days_str == "0000000":
        return None
    return "".join(str(i) for i, bit in enumerate(collect_days_str, start=1) if bit == "1")

def _convert_cutoff_time(cutoff_time_str: Optional[str]) -> Optional[str]:
    """
    Convertit une chaîne de caractères représentant l'heure limite de collecte au format "HHMM"
    en une chaîne au format "HH:MM". Par exemple, "1730" devient "17:30".
    """
    if cutoff_time_str is None or len(cutoff_time_str) != 4:
        return None
    return f"{cutoff_time_str[:2]}:{cutoff_time_str[2:]}"

def _clean_fields_in_lines(line: DistributorLineData) -> DistributorLineData:
    """
    Nettoie les champs vides dans les lignes de données en les remplaçant par None.
    Cette fonction modifie les objets de ligne en place, en vérifiant les champs
    bloc1, bloc2, et bloc3.
    
    param :
        - line: La ligne à nettoyer.
    """
    for field in [line.bloc1, line.bloc2, line.bloc3]:
        if field == "":
            field = None
    return line

def _generate_address_from_distributor_line(line: DistributorLineData) -> str:
    """
    Génère une adresse complète à partir d'une ligne de données de distributeur.
    Cette fonction prend les différents champs d'adresse de la ligne, et les concatène
    pour former une adresse complète.
    
    param :
        - line: La ligne de données de distributeur à partir de laquelle générer l'adresse.
    """
    b1 = line.bloc1
    x: str = ""
    x += b1.numero_voie + " " if b1.numero_voie else ""
    x += b1.adresse_l1 + " " if b1.adresse_l1 else ""
    x += b1.adresse_l2 + " " if b1.adresse_l2 else ""
    x += b1.adresse_l3 + " " if b1.adresse_l3 else ""
    x += b1.code_postal + " " if b1.code_postal else ""
    x += b1.ville + " " if b1.ville else ""
    x += b1.pays if b1.pays else ""
    return x.strip()
