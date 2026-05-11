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
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Annotated
from app_back.db_connection import config
from db_models.services.dilicom import DilicomService


router = APIRouter(prefix="/background", tags=["dilicom", "background"])
logger = logging.getLogger(__name__)


@router.post("/parse-returns")
def send_dilicom_order(
    session: Annotated[Session, Depends(config.get_main_session)],
    archives: bool = False,
):
    """
    Route pour déclencher la récupération et le traitement des fichiers de retour de Dilicom.
    C'est une route de test, destinée à être appelée manuellement pour les tests.
    """
    try:
        ds = DilicomService(session=session)
        ds.fetch_returns(archives=archives)
        return {"status": "success", "message": "Fichiers de retour traités avec succès."}
    except ValueError as e:
        return {"status": "error", "message": str(e)}

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
