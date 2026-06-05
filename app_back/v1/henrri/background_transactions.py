"""Routes FastAPI pour les opérations background liées à Henrri.

Ce module contient toute la logique métier :
- Mise à jour des clients et produits sur Henrri
- Récupération des commandes depuis Henrri
- Récupération du CA depuis Henrri
"""

import logging
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app_back.db_connection import config
from db_models.services.henrri import HenrriProductsService
from db_models.objects.objects import GeneralObjects


router = APIRouter(prefix="/background", tags=["henrri", "background"])
logger = logging.getLogger(__name__)

@router.post("/update-products/{product_id}")
def update_henrri_product(
    session: Annotated[Session, Depends(config.get_main_session)],
    product_id: str,
):
    """
    Route pour déclencher la mise à jour d'un produit sur Henrri.
    C'est une route de test, destinée à être appelée manuellement pour les tests.
    """
    stmt = select(GeneralObjects).where(GeneralObjects.id == product_id)
    product = session.execute(stmt).scalars().one()
    try:
        ps = HenrriProductsService()
        ps.update_product(product_id=product_id, updated_product=product)
        return {"status": "success", "message": "Produit mis à jour avec succès."}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
