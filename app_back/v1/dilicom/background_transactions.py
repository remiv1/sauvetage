"""Routes FastAPI pour les opérations background liées à Dilicom.

Ce module contient toute la logique métier :
- Dépose de fichiers sur le serveur Dilicom (référentiels à créer/supprimer)
- Récupération des fichiers déposés par Dilicom (distributeurs, services, retours de commandes)
- Traitement des fichiers récupérés pour mettre à jour les statuts des commandes
- Gestion des erreurs et des logs pour le suivi des opérations
- Traitement des fichiers récupérés pour mettre à jour les données de référence
    (distributeurs, livres, etc.)
"""

import logging
from typing import Annotated, Any
from pathlib import Path
from os import getenv
from fastapi import APIRouter, Depends, Form, Body
from sqlalchemy.orm import Session
from app_back.db_connection import config
from db_models.services.dilicom import DilicomService


router = APIRouter(prefix="/background", tags=["dilicom", "background"])
logger = logging.getLogger(__name__)
SERVICES_NOT_IMPLEMENTED_MESSAGE = "_update_services non implémenté."
FILE_REMOVAL_ERROR_MESSAGE = "Impossible de supprimer %s: %s"


def _resolve_file_parameters(
    filename: str | None,
    remove_after: bool,
    payload: dict | None,
) -> tuple[str | None, bool]:
    if payload and isinstance(payload, dict):
        filename = filename or payload.get("filename")
        if payload.get("remove_after") is not None:
            remove_after = bool(payload["remove_after"])
    return filename, remove_after


def _classify_dilicom_file(
    ds: DilicomService,
    file_path: Path,
) -> tuple[dict[str, Any], list[Path]]:
    from dilicom_parser.classifier import FilesClassifier  # pylint: disable=C0415

    ds.classifier = FilesClassifier([file_path], streaming_option=True)
    classified = ds.classifier.classify().parse()
    books = ds._books_target_path(ds.classifier.heavy_files)  # pylint: disable=protected-access
    return classified, books


def _update_classified_objects(
    ds: DilicomService,
    objects_to_merge: dict[str, Any],
) -> dict[str, int]:
    processed = {"distributor": 0, "services": 0}
    distributors = objects_to_merge.get("distributor", [])
    if distributors:
        ds._update_distributors(distributors)  # pylint: disable=protected-access
        processed["distributor"] = len(distributors)

    for service_type in ("eancom", "gencod"):
        services = objects_to_merge.get(service_type, [])
        if not services:
            continue
        try:
            ds._update_services(services)  # pylint: disable=protected-access
            processed["services"] += len(services)
        except NotImplementedError:
            logger.warning(SERVICES_NOT_IMPLEMENTED_MESSAGE)
    return processed


def _remove_processed_file(file_path: Path) -> None:
    try:
        file_path.unlink()
        logger.info("Fichier %s supprimé après traitement.", file_path)
    except OSError as exc:
        logger.exception(FILE_REMOVAL_ERROR_MESSAGE, file_path, exc)


@router.post("/post-referencial")
def post_referencial_dilicom(
    session: Annotated[Session, Depends(config.get_main_session)],
):
    """
    Route pour déclencher la création de référentiels Dilicom pour les objets à supprimer
    ou à créer. C'est une route de test, destinée à être appelée manuellement pour les tests.
    """
    try:
        ds = DilicomService(session=session)
        ds.send_updates()
        return {"status": "success", "message": "Référentiel Dilicom créé et déposé avec succès."}
    except ValueError as e:
        logger.exception("Erreur lors de la création du référentiel Dilicom: %s", e)
        return {"status": "error", "message": str(e)}

@router.post("/fetch-returns")
def fetch_returns_dilicom(
    session: Annotated[Session, Depends(config.get_main_session)],
    archives: bool = False,
):
    """
    Route pour déclencher la récupération des fichiers de retour de Dilicom.
    C'est une route de test, destinée à être appelée manuellement pour les tests.
    """
    try:
        ds = DilicomService(session=session)
        ds.fetch_returns(archives=archives)
        return {"status": "success", "message": "Fichiers de retour récupérés avec succès."}
    except ValueError as e:
        return {"status": "error", "message": str(e)}

@router.post("/test-book-processing")
def test_book_processing(
    session: Annotated[Session, Depends(config.get_main_session)],
):
    """
    Route pour tester le traitement d'un livre à partir d'un fichier ONIX.
    C'est une route de test, destinée à être appelée manuellement pour les tests.
    """
    try:
        ds = DilicomService(session=session)
        # Simuler le traitement d'un livre à partir d'un fichier ONIX
        ds._update_books([Path("/home/root/app/dilicom_in/489084922.xml")]) # pylint: disable=protected-access

        return {
            "status": "success",
            "message": "Traitement du livre testé avec succès.",
            }
    except ValueError as e:
        return {"status": "error", "message": str(e)}


@router.post("/process-single-xml")
def process_single_xml_dilicom(
    session: Annotated[Session, Depends(config.get_main_session)],
    file_path: Annotated[str | None, Form()] = None,
    remove_after: Annotated[bool, Form()] = False,
    payload: Annotated[dict | None, Body()] = None,
):
    """
    Route provisoire pour tester un fichier XML unique sans relancer les archives complètes.
    Utile pour reproduire un cas précis de fusion livre / EAN / métadonnées.
    
    eg:
    - curl -X POST "http://127.0.0.1:8000/api/v1/dilicom/background/process-single-xml"
        -F "file_path=/home/root/app/dilicom_in/DIF492327800/492327800.xml"
    """
    try:
        if not file_path and payload and isinstance(payload, dict):
            file_path = payload.get("file_path") or payload.get("filename")
            if payload.get("remove_after") is not None:
                remove_after = bool(payload.get("remove_after"))

        if not file_path:
            message = "Paramètre 'file_path' manquant dans la requête (formulaire ou JSON)."
            logger.warning(message)
            return {"status": "error", "message": message}

        xml_path = Path(file_path)
        if not xml_path.is_absolute():
            xml_path = (Path(getenv("DILICOM_IN_DIR", "dilicom_in")) / xml_path).resolve()

        if not xml_path.exists() or not xml_path.is_file():
            message = f"Fichier XML introuvable: {xml_path}"
            logger.warning(message)
            return {"status": "error", "message": message}

        ds = DilicomService(session=session)
        ds._update_books([xml_path])  # pylint: disable=protected-access

        if remove_after:
            try:
                xml_path.unlink()
                logger.info("Fichier %s supprimé après traitement unique.", xml_path)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception(FILE_REMOVAL_ERROR_MESSAGE, xml_path, exc)

        return {
            "status": "success",
            "processed": {"books": 1, "file": str(xml_path)},
        }
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        logger.exception("Erreur lors du traitement du fichier XML Dilicom %s: %s", file_path, exc)
        return {"status": "error", "message": str(exc)}


@router.post("/process-file")
def process_dilicom_file(
    session: Annotated[Session, Depends(config.get_main_session)],
    filename: Annotated[str | None, Form()] = None,
    remove_after: Annotated[bool, Form()] = False,
    payload: Annotated[dict | None, Body()] = None,
):
    """
    Route pour traiter un fichier déposé localement dans le répertoire d'entrée Dilicom.
    - `filename`: nom de fichier relatif dans le répertoire `DILICOM_IN_DIR`.
    - `remove_after`: si True, supprime le fichier après traitement.

    Cette route permet d'appeler depuis le conteneur 
        `curl -X POST http://localhost:8000/api/v1/background/process-file -d 'filename=...'
    et de faire parser le fichier comme s'il venait du serveur Dilicom.
    """
    filename, remove_after = _resolve_file_parameters(filename, remove_after, payload)
    if not filename:
        message = "Paramètre 'filename' manquant dans la requête (formulaire ou JSON)."
        logger.warning(message)
        return {"status": "error", "message": message}

    file_path = Path(getenv("DILICOM_IN_DIR", "dilicom_in")) / filename
    if not file_path.exists() or not file_path.is_file():
        message = f"Fichier introuvable: {file_path}"
        logger.warning(message)
        return {"status": "error", "message": message}

    try:
        ds = DilicomService(session=session)
        objects_to_merge, books_to_merge = _classify_dilicom_file(ds, file_path)
        processed = _update_classified_objects(ds, objects_to_merge)
        processed["books"] = len(books_to_merge)
        if books_to_merge:
            ds._update_books(books_to_merge)  # pylint: disable=protected-access
        if remove_after:
            _remove_processed_file(file_path)
        return {"status": "success", "processed": processed}
    except (ImportError, KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
        logger.exception("Erreur lors du traitement du fichier Dilicom %s: %s", filename, exc)
        return {"status": "error", "message": str(exc)}
