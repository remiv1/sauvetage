"""
Module contenant les services pour les opérations SFTP avec le serveur de Dilicom.
Ce module inclut:
- La classe `DilicomService` qui encapsule les opérations SFTP avec le serveur de Dilicom.
"""

import re
from os import getenv
import logging
from pathlib import Path
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional, cast
from sqlalchemy.orm import Session
from sqlalchemy import select
from onixlib import Notice, Product
from onixlib.models.generated.v3_0 import (
    Extent,
    Language,
    List74,
)
from dilicom_parser.transport import Connector
from dilicom_parser.classifier import FilesClassifier
from dilicom_parser.models import DistributorData, DistributorLineData
from db_models.objects import ObjectPrices
from db_models.objects.stocks import DilicomReferencial
from db_models.services.models import Book
from db_models.repositories.suppliers import SuppliersRepository, Suppliers
from db_models.repositories.objects import (
    ObjectsRepository,
    GeneralObjects,
    Books,
    ObjMetadatas,
)
from db_models.repositories.stocks.dilicom import DilicomReferencialRepository

logger = logging.getLogger("app_back.services.dilicom")

def _deep_getattr(obj: object, attr_path: str, default: str="N/A") -> str | object:
    for attr in attr_path.split("."):
        try:
            obj = getattr(obj, attr)
        except AttributeError:
            return default
    if isinstance(obj, str):
        return str(obj).strip()
    else:
        return obj


def _read_value(value: Any) -> Any:
    """Lit une valeur issue de types xsdata/Enum sans lever d'exception."""
    if value is None:
        return None
    if hasattr(value, "value"):
        inner = getattr(value, "value")
        if inner is not None and not isinstance(inner, (str, int, float, bool)):
            return _read_value(inner)
        return inner
    return value


def _build_label_map(enum_cls: type[Any]) -> dict[str, str]:
    doc = enum_cls.__doc__ or ""
    pattern = r":cvar\s+([A-Z0-9_]+):\s+(.+)"
    matches = re.findall(pattern, doc)
    return {
        (code.split("_", 1)[1] if code.startswith("VALUE_") else code): label.strip()
        for code, label in matches
    }

LANGUAGE_LABEL_MAP = _build_label_map(List74)
LANGUAGE_FRIENDLY_LABEL_MAP = {
    "FRE": "français",
    "FR": "français",
    "ENG": "anglais",
    "EN": "anglais",
}

class DilicomServiceBase:
    """
    Service de base pour les opérations SFTP avec le serveur de Dilicom.
    Cette classe garde les helpers et le flux partagé pour les traitements
    des fichiers de retour et de référentiel.
    """
    def __init__(self, session: Session):
        self.session = session
        env_path = Path(__file__).resolve().parents[2] / "config" / "logs" / ".env.dilicom"
        self.connect = Connector(env_path=str(env_path))
        self.classifier: FilesClassifier
        self.parser: list[Any] = []
        self.objects_repo = ObjectsRepository(self.session)
        self.supplier_repo = SuppliersRepository(self.session)
        self.dilicom_referencial_repo = DilicomReferencialRepository(self.session)
        self.vat_rates_by_value: dict[float, int] = {}
        self.vat_rates_by_id: dict[int, float] = {}
        self.refresh_vat_rate_cache()

    def refresh_vat_rate_cache(self) -> None:
        """Charge les taux de TVA actifs et les mappe vers l'identifiant associé."""
        self.vat_rates_by_value = self.objects_repo.get_current_vat_rates()
        self.vat_rates_by_id = {
            vat_id: vat_rate for vat_rate, vat_id in self.vat_rates_by_value.items()
        }

    def _get_vat_rate_id(self, vat_rate_value: float | str | Decimal | None) -> Optional[int]:
        """Retourne l'ID TVA actif correspondant, sans requête SQL supplémentaire."""
        if vat_rate_value is None:
            return None
        normalized = float(Decimal(str(vat_rate_value)).quantize(Decimal("0.01")))
        return self.vat_rates_by_value.get(normalized)

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
        remote_path = str(Path('I') / filename)
        with self.connect as server:
            server.upload_from_memory(byte_content, remote_path=remote_path)
            logger.info(
                "REF FEL envoyé avec succès au serveur de Dilicom à l'emplacement: %s",
                remote_path,
            )

    def _books_target_path(self, list_path: list[Path]) -> list[Path]:
        """
        Génère le chemin de destination pour les fichiers de livres à partir du chemin local.
        Cette méthode prend un chemin local, et génère le chemin de destination correspondant
        pour les fichiers de livres à envoyer au serveur de Dilicom.

        param :
        path: Le chemin local du fichier de livres.
        """
        target_files: list[Path] = []
        for file_path in list_path:
            base = file_path.name.split(".", 1)[0]
            code_start = len(base)
            while code_start > 0 and base[code_start - 1].isdigit():
                code_start -= 1
            code = base[code_start:]
            if not code:
                raise ValueError(
                    f"Aucun code numérique trouvé dans le nom du fichier: {file_path.name}"
                )

            target_dir = file_path.parent / base
            target_files.append(target_dir / f"{code}.xml")

        return target_files

    def fetch_returns(self, archives: bool = False) -> None:
        """
        Récupère les fichiers de retour du serveur de Dilicom.
        Cette méthode se connecte au serveur SFTP, télécharge les fichiers de retour,
        et les traite pour mettre à jour les statuts des commandes dans la base de données.
        """
        local_dir = Path(getenv("DILICOM_IN_DIR", "dilicom_returns"))

        # Vidage du dossier local de réception avant téléchargement pour éviter les confusions
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
            total_by_type
        )
        # Suppression des extensions de fichiers sur les `books_to_merge` qui ont été extraits
        books_to_merge = self._books_target_path(books_to_merge)
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
            logger.info(
                "Mise à jour des distributeurs avec %d entrées à traiter.",
                len(objects_to_merge["distributor"])
            )
            self._update_distributors(objects_to_merge["distributor"])
        if "eancom" in objects_to_merge:
            logger.info(
                "Mise à jour des services avec %d entrées à traiter.",
                len(objects_to_merge["eancom"])
            )
            self._update_services(objects_to_merge["eancom"])
        if "gencod" in objects_to_merge:
            logger.info(
                "Mise à jour des services avec %d entrées à traiter.",
                len(objects_to_merge["gencod"])
            )
            self._update_services(objects_to_merge["gencod"])
        if books_to_merge:
            logger.info(
                "Mise à jour des livres avec %d entrées à traiter.",
                len(books_to_merge)
            )
            self.refresh_vat_rate_cache()
            self._update_books(books_to_merge)

        # Suppression des fichiers locaux après traitement
        for file in files_list:
            try:
                file.unlink()
                logger.info("Fichier %s supprimé avec succès après traitement.", file.name)
            except (FileNotFoundError, RuntimeError) as e:
                logger.exception("Erreur lors de la suppression du fichier %s: %s", file, e)

    def _update_synced(self, references: list[str]) -> None:
        """
        Met à jour le statut de synchronisation des références dans la base de données.
        Cette méthode prend une liste de références, et met à jour leur champ `dilicom_synced`
        pour indiquer qu'elles ont été synchronisées avec le serveur de Dilicom.
        
        param :
            - references: La liste des références à mettre à jour.
        """
        for ref in references:
            self.dilicom_referencial_repo.update_status(ean13=ref)
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
            self._update_synced([ref.ean13 for ref in unsynced_refs])
            logger.info(
                "Contenu du fichier REFEL construit avec succès. Nombre de références incluses: %d",
                len(unsynced_refs)
            )
            return value_to_return
        except Exception as e:
            message = f"Erreur lors de la construction du contenu REFEL: {e}"
            raise RuntimeError(message) from e

    def _extract_price_and_vat_from_onix(self, onix_product: Product) -> dict[str, float]:
        """Extrait le prix HT et le taux TVA depuis les blocs ONIX et leurs taxes.

        Les fichiers Dilicom exposent souvent le HT dans le bloc de taxe sous la clé
        ``TaxableAmount`` et le TTC dans ``PriceAmount`` pour un prix de type 04.
        Dans ce cas, la base taxable est le montant réellement utilisé pour la TVA.
        """
        entries = self._extract_prices_and_vats_from_onix(onix_product)
        if entries:
            first = entries[0]
            return {"price_ht": float(first["price_ht"]), "vat_rate": float(first["vat_rate"])}
        return {"price_ht": 0.0, "vat_rate": 0.0}

    @staticmethod
    def _add_unique_price_entry(
        entries: list[dict[str, float]],
        seen: set[tuple[float, float]],
        price_ht: float,
        vat_rate: float,
    ) -> None:
        """Ajoute une entrée de prix s'il n'existe pas déjà avec la même paire HT/TVA."""
        key = (round(price_ht, 3), round(vat_rate, 3))
        if key not in seen:
            seen.add(key)
            entries.append({"price_ht": price_ht, "vat_rate": vat_rate})

    def _iter_raw_prices(self, raw_product: Any) -> list[Any]:
        """Itère sur les blocs de prix ONIX brut sans aplatir toute la logique métier."""
        prices: list[Any] = []
        for supply in getattr(raw_product, "product_supply", []) or []:
            for supply_detail in getattr(supply, "supply_detail", []) or []:
                prices.extend(getattr(supply_detail, "price", []) or [])
        return prices

    @staticmethod
    def _tax_entries(raw_price: Any) -> list[dict[str, float]]:
        """Extrait les variations de prix liées aux taxes d'un bloc ONIX."""
        entries: list[dict[str, float]] = []
        for tax in getattr(raw_price, "tax", []) or []:
            rate_value = _read_value(getattr(getattr(tax, "tax_rate_percent", None), "value", None))
            taxable_value = _read_value(
                getattr(getattr(tax, "taxable_amount", None),"value", None)
            )
            if rate_value is not None and taxable_value is not None:
                entries.append({"price_ht": float(taxable_value), "vat_rate": float(rate_value)})
        return entries

    @staticmethod
    def _price_type_amount(raw_price: Any) -> tuple[str | None, float | None]:
        """Retourne le type de prix et le montant brut associated au bloc ONIX."""
        price_type = _read_value(getattr(raw_price, "price_type", None))
        price_type_code = _read_value(getattr(price_type, "value", None))
        price_amount = _read_value(getattr(raw_price, "price_amount", None))
        price_amount_value = _read_value(getattr(price_amount, "value", None))
        return price_type_code, None if price_amount_value is None else float(price_amount_value)

    def _extract_raw_price_entries(self, raw_product: Any) -> list[dict[str, float]]:
        """Extrait les entrées de prix issue des blocs de prix brute ONIX."""
        seen: set[tuple[float, float]] = set()
        entries: list[dict[str, float]] = []
        for raw_price in self._iter_raw_prices(raw_product):
            taxes = getattr(raw_price, "tax", []) or []
            for tax_entry in self._tax_entries(raw_price):
                self._add_unique_price_entry(
                    entries,
                    seen,
                    tax_entry["price_ht"],
                    tax_entry["vat_rate"],
                )
            if taxes:
                continue
            price_type_code, price_amount_value = self._price_type_amount(raw_price)
            if price_type_code in {"01", "04"} and price_amount_value is not None:
                self._add_unique_price_entry(entries, seen, price_amount_value, 0.0)
        return entries

    def _extract_prices_and_vats_from_onix(self, onix_product: Product) -> list[dict[str, float]]:
        """Extrait toutes les combinaisons prix HT / taux TVA présentes dans le produit."""
        aggregated = getattr(onix_product, "price", None)
        default_entries: list[dict[str, float]] = []
        if aggregated is not None and aggregated.ht is not None and aggregated.vat_rate is not None:
            default_entries.append(
                {"price_ht": float(aggregated.ht), "vat_rate": float(aggregated.vat_rate)}
            )

        raw_product = getattr(onix_product, "raw", None)
        entries = self._extract_raw_price_entries(raw_product)
        return entries or default_entries

    @staticmethod
    def _coerce_year_candidate(value: Any) -> Optional[int]:
        """Convertit une valeur ONIX en année si elle est exploitable."""
        extracted = _read_value(value)
        if extracted is None:
            return None
        if isinstance(extracted, (int, float)):
            year = int(extracted)
            return year if 1900 <= year <= 2100 else None
        digits = re.sub(r"\D", "", str(extracted))
        if len(digits) < 4:
            return None
        year = int(digits[:4])
        return year if 1900 <= year <= 2100 else None

    def _iter_publication_candidates(self, onix_product: Product) -> list[Any]:
        """Regroupe les valeurs de dates de publication ONIX dans un seul flux itérable."""
        candidates: list[Any] = []
        for source in (
            getattr(onix_product, "publishing", None),
            getattr(onix_product, "_raw", None)
        ):
            if source is None:
                continue
            for attr in ("publication_date", "publishing_date", "date"):
                value = getattr(source, attr, None)
                if value is not None:
                    candidates.append(value)

        raw_product = getattr(onix_product, "_raw", None)
        publishing_detail = getattr(raw_product, "publishing_detail", None)
        if publishing_detail is not None:
            for publication_date in getattr(publishing_detail, "publishing_date", []) or []:
                if publication_date is not None:
                    candidates.extend((getattr(publication_date, "date", None), publication_date))
        return candidates

    def _extract_publication_year_from_onix(self, onix_product: Product) -> Optional[int]:
        """Extrait l’année de publication ONIX en supportant plusieurs variantes de structure."""
        for candidate in self._iter_publication_candidates(onix_product):
            year = self._coerce_year_candidate(candidate)
            if year is not None:
                return year
        return None

    @staticmethod
    def _normalise_list(value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    @staticmethod
    def _format_measurement(value: Any) -> Optional[str]:
        if value is None:
            return None
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return None
        if numeric_value.is_integer():
            return str(int(numeric_value))
        return str(numeric_value).rstrip("0").rstrip(".")

    @staticmethod
    def _convert_to_mm(value: Any, unit: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return None
        unit_key = str(unit or "").strip().lower()
        conversion_factors = {
            "mm": 1,
            "cm": 10,
            "m": 1000,
            "in": 25.4,
            "inch": 25.4,
            "inches": 25.4,
        }
        factor = conversion_factors.get(unit_key)
        if factor is None:
            return numeric_value
        return numeric_value * factor

    @staticmethod
    def _convert_to_grams(value: Any, unit: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return None
        unit_key = str(unit or "").strip().lower()
        conversion_factors = {
            "mg": 0.001,
            "g": 1,
            "gr": 1,
            "kg": 1000,
            "lb": 453.59237,
            "oz": 28.349523125,
        }
        factor = conversion_factors.get(unit_key)
        if factor is None:
            return numeric_value
        return numeric_value * factor

    def _extract_language_metadata(self, raw_product: Any, onix_product: Product) -> dict[str, Any]:
        metadatas: dict[str, Any] = {}
        descriptive_detail = getattr(raw_product, "descriptive_detail", None)
        language_values: list[str] = []
        raw_languages = getattr(descriptive_detail, "language", []) or []
        if not raw_languages and hasattr(onix_product, "descriptive"):
            raw_languages = cast(
                list[Language],
                _deep_getattr(onix_product, "descriptive.languages"),
            ) or []
        for language in self._normalise_list(raw_languages):
            if not language:
                continue
            code = _read_value(getattr(language, "language_code", None))
            if code is not None:
                language_values.append(str(code))
        language_code = next(
            (
                code for candidate in ["01", "02", "fr", "fre", "FRE"]
                for code in language_values
                if str(code).upper() == str(candidate).upper()),
            None,
        )
        if language_code is None and language_values:
            language_code = language_values[0]
        if not language_code:
            return metadatas

        normalized_code = str(language_code).upper()
        if normalized_code.startswith("VALUE_"):
            normalized_code = normalized_code.split("VALUE_", 1)[1]
        metadatas["code_langue"] = normalized_code
        metadatas["langue"] = LANGUAGE_FRIENDLY_LABEL_MAP.get(
            normalized_code,
            LANGUAGE_LABEL_MAP.get(normalized_code, normalized_code),
        )
        return metadatas

    @staticmethod
    def _iter_collection_titles(collection: Any) -> list[str]:
        """Extrait les titres d'une collection ONIX sans imbriquer les boucles métier."""
        title_texts: list[str] = []
        for title_detail in DilicomServiceBase._normalise_list(
            getattr(collection, "title_detail", []) or []
        ):
            for title_element in DilicomServiceBase._normalise_list(
                getattr(title_detail, "title_element", []) or []
            ):
                title_text = _read_value(getattr(title_element, "title_text", None))
                if title_text is not None:
                    title_texts.append(str(title_text))
        return title_texts

    def _extract_collection_metadata(self, raw_product: Any) -> dict[str, Any]:
        metadatas: dict[str, Any] = {}
        descriptive_detail = getattr(raw_product, "descriptive_detail", None)
        collection_names: list[str] = []
        for collection in self._normalise_list(getattr(descriptive_detail, "collection", []) or []):
            if not collection:
                continue
            for title_text in self._iter_collection_titles(collection):
                if title_text not in collection_names:
                    collection_names.append(title_text)
        if collection_names:
            metadatas["collection"] = collection_names[0]
            metadatas["collections"] = collection_names
        return metadatas

    def _extract_dimensions_metadata(self, raw_product: Any) -> dict[str, Any]:
        metadatas: dict[str, Any] = {}
        descriptive_detail = getattr(raw_product, "descriptive_detail", None)
        measures = getattr(descriptive_detail, "measure", []) or []
        width_value: Optional[float] = None
        height_value: Optional[float] = None
        thickness_value: Optional[float] = None
        for measure in measures:
            measure_type = _read_value(getattr(measure, "measure_type", None))
            measure_value = _read_value(getattr(measure, "measurement", None))
            measure_unit = _read_value(getattr(measure, "measure_unit_code", None))
            if measure_type == "01":
                width_value = self._convert_to_mm(measure_value, measure_unit)
            elif measure_type == "02":
                height_value = self._convert_to_mm(measure_value, measure_unit)
            elif measure_type == "03":
                thickness_value = self._convert_to_mm(measure_value, measure_unit)
        dimensions = [
            self._format_measurement(width_value),
            self._format_measurement(height_value),
            self._format_measurement(thickness_value),
        ]
        dimensions_values = [dimension for dimension in dimensions if dimension is not None]
        if dimensions_values:
            metadatas["dimensions_mm"] = "*".join(dimensions_values)
        return metadatas

    def _extract_weight_metadata(self, raw_product: Any) -> dict[str, Any]:
        metadatas: dict[str, Any] = {}
        descriptive_detail = getattr(raw_product, "descriptive_detail", None)
        for measure in getattr(descriptive_detail, "measure", []) or []:
            measure_type = _read_value(getattr(measure, "measure_type", None))
            measure_value = _read_value(getattr(measure, "measurement", None))
            measure_unit = _read_value(getattr(measure, "measure_unit_code", None))
            if measure_type == "08":
                grams = self._convert_to_grams(measure_value, measure_unit)
                if grams is not None:
                    metadatas["poids_grammes"] = self._format_measurement(grams) or str(grams)
                    break
        return metadatas

    def _extract_bnf_metadata(self, raw_product: Any) -> dict[str, Any]:
        metadatas: dict[str, Any] = {}
        for identifier in getattr(raw_product, "product_identifier", []) or []:
            product_id_type = _read_value(getattr(identifier, "product_idtype", None))
            id_value = _read_value(getattr(getattr(identifier, "idvalue", None), "value", None))
            if product_id_type == "31" and id_value is not None:
                metadatas["ref_bnf"] = str(id_value)
            elif product_id_type == "35" and id_value is not None:
                metadatas["notice_bnf"] = str(id_value)
        return metadatas

    def _get_metadatas_from_onix(self, onix_product: Product) -> dict[str, Optional[str]]:
        """Extrait les métadonnées utiles, y compris les variantes d’images ONIX."""
        raw_product = getattr(onix_product, "_raw", None)
        if raw_product is None:
            return {}

        metadatas: dict[str, Any] = {}
        metadatas.update(self._extract_bnf_metadata(raw_product))
        metadatas.update(self._extract_language_metadata(raw_product, onix_product))
        metadatas.update(self._extract_collection_metadata(raw_product))
        metadatas.update(self._extract_dimensions_metadata(raw_product))
        metadatas.update(self._extract_weight_metadata(raw_product))
        return metadatas


    def _build_book_from_onix(self, onix_product: Product) -> Book:
        book = Book(title=cast(str, _deep_getattr(onix_product, "title")))
        book.isbn = cast(str, _deep_getattr(onix_product, "isbn"))
        book.title = cast(str, _deep_getattr(onix_product, "title"))
        book.supplier_gln = cast(str, _deep_getattr(onix_product, "publisher.gln"))
        book.editor_gln = cast(str, _deep_getattr(onix_product, "editor.gln"))
        book.description = cast(str, _deep_getattr(onix_product, "collateral.description"))

        price_data = self._extract_price_and_vat_from_onix(onix_product)
        book.price_ht = float(price_data["price_ht"])
        book.vat_rate = float(price_data["vat_rate"])

        authors = _deep_getattr(onix_product, "authors")
        if isinstance(authors, list):
            book.authors = ", ".join(
                author.full_name for author in authors if hasattr(author, "full_name")
            )
        else:
            book.authors = ""
        return book

    def _hydrate_book_year_and_pages(self, onix_product: Product, book: Book) -> None:
        publication_year = self._extract_publication_year_from_onix(onix_product)
        if publication_year is not None:
            book.year = str(publication_year)

        extents = cast(list[Extent], _deep_getattr(onix_product, "_raw.descriptive_detail.extent"))
        for extent in extents:
            extent_type = _read_value(getattr(extent, "extent_type", None))
            extent_unit = _read_value(getattr(extent, "extent_unit", None))
            extent_value = _read_value(getattr(extent, "extent_value", None))
            if extent_type == "00" and extent_unit == "03" and extent_value is not None:
                book.pages = int(extent_value)
                break

    def _build_object_prices(self, onix_product: Product, book: Book) -> list[ObjectPrices]:
        price_rows = self._extract_prices_and_vats_from_onix(onix_product)
        object_prices = [
            ObjectPrices(
                price=float(price_row["price_ht"]),
                vat_rate_id=self._get_vat_rate_id(price_row["vat_rate"]),
                from_date=date.today(),
                to_date=None,
            )
            for price_row in price_rows
            if price_row["price_ht"] is not None and price_row["vat_rate"] is not None
        ]
        if object_prices:
            return object_prices
        return [
            ObjectPrices(
                price=float(book.price_ht or 0.0),
                vat_rate_id=self._get_vat_rate_id(book.vat_rate),
                from_date=date.today(),
                to_date=None,
            )
        ]

    def _get_values_from_onix(self, onix_product: Product) -> Optional[dict[str, Any]]:
        """
        Extrait les valeurs pertinentes d'un objet `Notice` ONIX pour un produit.
        Cette méthode prend un objet `Notice` représentant un produit ONIX, et extrait les
        informations nécessaires pour la mise à jour des livres dans la base de données.

        param :
            - onix_product: L'objet `Notice` ONIX à partir duquel extraire les valeurs.
        """
        book = self._build_book_from_onix(onix_product)
        logger.debug("Mise à jour du livre avec ISBN %s et titre %s", book.isbn, book.title)
        book.supplier = self.supplier_repo.get_by_gln13(book.supplier_gln or "")
        book.editor = self.supplier_repo.get_by_gln13(book.editor_gln or "")
        self._hydrate_book_year_and_pages(onix_product, book)

        vat_rate_id = self._get_vat_rate_id(book.vat_rate)
        if book.vat_rate is not None and vat_rate_id is None:
            logger.warning(
                "Aucun taux de TVA actif trouvé pour la valeur %.2f lors de l'import ONIX %s.",
                float(book.vat_rate),
                book.isbn,
            )

        if not book.supplier:
            logger.info("Création d'un nouveau fournisseur %s nécessaire.", book.supplier_gln)
            return None

        if not book.editor:
            book.editor_name = cast(str, _deep_getattr(onix_product, "editor.name"))

        supplier_id = book.supplier.id
        book.supplier_name = book.supplier.name
        g_o = GeneralObjects(
            supplier_id=supplier_id,
            general_object_type="book",
            ean13=book.isbn,
            name=book.title,
            description=book.description,
        )
        b = Books(
            author=book.authors,
            diffuser=book.supplier_name,
            publication_year=int(book.year) if book.year is not None else None,
        )
        if book.pages:
            b.pages = cast(int, book.pages)
        if book.editor:
            b.editor = book.editor.name

        metadatas = ObjMetadatas(semistructured_data=self._get_metadatas_from_onix(onix_product))
        logger.debug(
            "Génération d'un objet avec EAN13 %s: GeneralObjects: %s, Book: %s, metadatas: %s",
            book.isbn,
            g_o,
            b,
            metadatas,
        )
        object_prices = self._build_object_prices(onix_product, book)
        return {
            "general_object": g_o,
            "book": b,
            "obj_metadatas": metadatas,
            "object_price": object_prices[0] if object_prices else None,
            "object_prices": object_prices,
        }


    def _update_books(self, books_list: list[Path]) -> None:
        """
        Met à jour les informations des livres dans la base de données en fonction des
        données extraites d'un fichier de retour de type "books". Cette méthode prend une
        liste de données de livres, et met à jour les informations correspondantes dans la
        base de données.
        
        param :
            - books_list: liste des données de livres extraites du fichier de retour.
        """
        for book_file in books_list:
            logger.debug(
                "Traitement du fichier de livres: %s",
                book_file.name
            )
            list_ean13: list[str] = []
            for i, product in enumerate(Notice.parse_full(book_file, version="3.0").products):
                values = self._get_values_from_onix(product)
                if values:
                    g_o = values["general_object"]
                    b = values["book"]
                    m = values["obj_metadatas"]
                else:
                    logger.warning(
                        "Eléments manquants pour le livre %s avec les données ONIX du fichier %s,",
                        i, book_file.name)
                    continue
                self.objects_repo.save_or_update_from_object(
                    general_object=g_o,
                    book=b,
                    obj_metadatas=m,
                    object_price=values.get("object_prices", values.get("object_price")),
                )
                list_ean13.append(g_o.ean13)
            self.objects_repo.commit_object()
            self._update_synced(list_ean13)


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
                        logger.exception(
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
            logger.info(
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
            logger.info(
                "Génération d'un Supplier inactif pour le distributeur %s avec mvt %s",
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
            logger.info(
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
            logger.info(
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


DilicomService = DilicomServiceBase
