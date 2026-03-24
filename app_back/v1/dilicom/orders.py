"""Routes FastAPI pour le workflow d'inventaire.

Ce module contient toute la logique métier :
- Normalisation et validation des EAN13
- Détection des produits inconnus
- Calcul du stock théorique par mouvements
- Validation des écarts et préparation des mouvements
- Tâche asynchrone de commit (thread Python)
- Fichier JSON d'état pour le suivi
"""

from typing import List
from fastapi import APIRouter
from app_back.v1.schems.dilicom import DilicomReferencialSchema


router = APIRouter(prefix="/orders", tags=["dilicom"])


@router.post("/send", response_model=List[DilicomReferencialSchema])
def send_dilicom_order():
    """Route pour envoyer les commandes Dilicom à partir des références à créer/supprimer.

    Cette route récupère les références à créer/supprimer, les traite et retourne la liste
    des références traitées avec leur statut de synchronisation.
    # TODO: Documenter les paramètres attendus et les réponses possibles.
    """
    pass  # TODO: implémenter la logique d'envoi des commandes Dilicom
