"""Routes FastAPI pour les opérations background liées à Dilicom.

Ce module contient toute la logique métier :
- Dépose de fichiers sur le serveur Dilicom (référentiels à créer/supprimer)
- Récupération des fichiers déposés par Dilicom (distributeurs, services, retours de commandes)
- Traitement des fichiers récupérés pour mettre à jour les statuts des commandes
- Gestion des erreurs et des logs pour le suivi des opérations
- Traitement des fichiers récupérés pour mettre à jour les données de référence
    (distributeurs, livres, etc.)
"""

from fastapi import APIRouter
from app_back.db_connection import config
from db_models.services.dilicom import DilicomService


router = APIRouter(prefix="/background", tags=["dilicom", "background"])


@router.post("/parse-returns")
def send_dilicom_order(archives: bool = False):
    """
    Route pour déclencher la récupération et le traitement des fichiers de retour de Dilicom.
    C'est une route de test, destinée à être appelée manuellement pour les tests.
    """
    ds = DilicomService(session=config.get_main_session())
    try:
        ds.fetch_returns(archives=archives)
        return {"status": "success", "message": "Fichiers de retour traités avec succès."}
    except ValueError as e:
        return {"status": "error", "message": str(e)}

@router.post("/post-referencial")
def post_referencial_dilicom():
    """
    Route pour déclencher la création de référentiels Dilicom pour les objets à supprimer
    ou à créer. C'est une route de test, destinée à être appelée manuellement pour les tests.
    """
    ds = DilicomService(session=config.get_main_session())
    try:
        ds.send_updates()
        return {"status": "success", "message": "Référentiel Dilicom créé et déposé avec succès."}
    except ValueError as e:
        return {"status": "error", "message": str(e)}

@router.post("/fetch-returns")
def fetch_returns_dilicom(archives: bool = False):
    """
    Route pour déclencher la récupération des fichiers de retour de Dilicom.
    C'est une route de test, destinée à être appelée manuellement pour les tests.
    """
    ds = DilicomService(session=config.get_main_session())
    try:
        ds.fetch_returns(archives=archives)
        return {"status": "success", "message": "Fichiers de retour récupérés avec succès."}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
