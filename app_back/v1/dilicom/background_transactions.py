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
from typing import Annotated
from pathlib import Path
from os import getenv
from typing import Any
from fastapi import APIRouter, Depends, Form, Body
from sqlalchemy.orm import Session
from app_back.db_connection import config
from db_models.services.dilicom import DilicomService


router = APIRouter(prefix="/background", tags=["dilicom", "background"])
logger = logging.getLogger(__name__)


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


@router.post("/process-file")
def process_dilicom_file(
    session: Annotated[Session, Depends(config.get_main_session)],
    filename: str | None = Form(None),
    remove_after: bool = Form(False),
    payload: dict | None = Body(None),
):
    """
    Route pour traiter un fichier déposé localement dans le répertoire d'entrée Dilicom.
    - `filename`: nom de fichier relatif dans le répertoire `DILICOM_IN_DIR`.
    - `remove_after`: si True, supprime le fichier après traitement.

    Cette route permet d'appeler depuis le conteneur 
        `curl -X POST http://localhost:8000/api/v1/background/process-file -d 'filename=...'
    et de faire parser le fichier comme s'il venait du serveur Dilicom.
    """
    try:
        # support form-data (`-d`) or JSON body {"filename":..., "remove_after":...}
        if not filename and payload and isinstance(payload, dict):
            filename = payload.get("filename")
            if filename is None:
                # allow boolean string values in JSON
                remove_after = bool(payload.get("remove_after", remove_after))

        if not filename:
            message = "Paramètre 'filename' manquant dans la requête (formulaire ou JSON)."
            logger.warning(message)
            return {"status": "error", "message": message}

        in_dir = Path(getenv("DILICOM_IN_DIR", "dilicom_in"))
        file_path = in_dir / filename
        if not file_path.exists() or not file_path.is_file():
            message = f"Fichier introuvable: {file_path}"
            logger.warning(message)
            return {"status": "error", "message": message}

        # Import localement le classifier pour éviter dépendance inutile au module si non utilisé
        from dilicom_parser.classifier import FilesClassifier  # type: ignore

        ds = DilicomService(session=session)
        # Construire le classifier à partir du fichier local
        ds.classifier = FilesClassifier([file_path], streaming_option=True)
        objects_to_merge = ds.classifier.classify().parse()
        books_to_merge = ds.classifier.heavy_files
        # Transformer les chemins lourds en chemins cibles attendus par la logique
        try:
            books_to_merge = ds._books_target_path(books_to_merge)
        except ValueError as e:
            logger.exception("Erreur lors du calcul des chemins de books: %s", e)
            return {"status": "error", "message": str(e)}

        processed: dict[str, Any] = {"distributor": 0, "services": 0, "books": 0}

        if objects_to_merge:
            if "distributor" in objects_to_merge and objects_to_merge["distributor"]:
                ds._update_distributors(objects_to_merge["distributor"])  # pylint: disable=protected-access
                processed["distributor"] = len(objects_to_merge["distributor"])
            if "eancom" in objects_to_merge and objects_to_merge["eancom"]:
                try:
                    ds._update_services(objects_to_merge["eancom"])  # pylint: disable=protected-access
                    processed["services"] += len(objects_to_merge["eancom"])
                except NotImplementedError:
                    logger.warning("_update_services non implémenté.")
            if "gencod" in objects_to_merge and objects_to_merge["gencod"]:
                try:
                    ds._update_services(objects_to_merge["gencod"])  # pylint: disable=protected-access
                    processed["services"] += len(objects_to_merge["gencod"])
                except NotImplementedError:
                    logger.warning("_update_services non implémenté.")

        if books_to_merge:
            ds._update_books(books_to_merge)  # pylint: disable=protected-access
            processed["books"] = len(books_to_merge)

        if remove_after:
            try:
                file_path.unlink()
                logger.info("Fichier %s supprimé après traitement.", file_path)
            except Exception as e:
                logger.exception("Impossible de supprimer %s: %s", file_path, e)

        return {"status": "success", "processed": processed}
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("Erreur lors du traitement du fichier Dilicom %s: %s", filename, e)
        return {"status": "error", "message": str(e)}
