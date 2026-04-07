"""Routes FastAPI pour le workflow d'inventaire.

Ce module contient toute la logique métier :
- Normalisation et validation des EAN13
- Détection des produits inconnus
- Calcul du stock théorique par mouvements
- Validation des écarts et préparation des mouvements
- Tâche asynchrone de commit (thread Python)
- Fichier JSON d'état pour le suivi
"""

from typing import List, Annotated
from fastapi import APIRouter, Depends
from app_back.v1.schems.dilicom import DilicomReferencialSchema
from app_back.db_connection import config
from app_back.utils.decorators import access_control
from db_models.services.dilicom import DilicomService


router = APIRouter(prefix="/orders", tags=["dilicom"])


@router.post("/send", response_model=List[DilicomReferencialSchema])
def send_dilicom_order():
    """Route pour envoyer les commandes Dilicom à partir des références à créer/supprimer.

    Cette route récupère les références à créer/supprimer, les traite et retourne la liste
    des références traitées avec leur statut de synchronisation.
    # TODO: Documenter les paramètres attendus et les réponses possibles.
    """
    pass  # pylint: disable=unnecessary-pass


@router.get("/send-referentials")
async def send_dilicom_referentials(_=Annotated[Depends(access_control(restrict_ip=True))]):
    """Route pour envoyer les référentiels à Dilicom.

    Cette route déclenche l'envoi des référentiels à Dilicom en utilisant `DilicomService`.
    """
    session = config.get_main_session()
    service = DilicomService(session=session)
    service.send_updates()
    return {"message": "Référentiels envoyés avec succès."}


@router.get("/fetch-returns")
async def fetch_dilicom_returns(_=Annotated[Depends(access_control(restrict_ip=True))]):
    """Route pour récupérer les retours de Dilicom.

    Cette route déclenche la récupération des retours de Dilicom en utilisant `DilicomService`.
    """
    session = config.get_main_session()
    service = DilicomService(session=session)
    service.fetch_returns()
    return {"message": "Retours récupérés avec succès."}
