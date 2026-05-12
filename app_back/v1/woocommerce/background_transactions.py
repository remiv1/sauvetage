"""Routes FastAPI pour les opérations background liées au site de e-commerce."""

import logging
from typing import Optional
from fastapi import APIRouter
from app_back.db_connection import config
from db_models.services.woo_commerce.products import WCProductsService


router = APIRouter(prefix="/background", tags=["woo_commerce", "background"])
logger = logging.getLogger(__name__)


@router.post("/update-vat-rates")
def update_vat_rates(specific: bool = False, specific_name: Optional[str] = None):
    """
    Route pour déclencher la mise à jour de tous les taux de TVA ou d'un taux de TVA
    spécifique en fonction du nom fourni.
    """
    wc_service = WCProductsService(config.get_main_session(),separated_keys=True)
    if specific and specific_name:
        wc_service.export_vat_rates(name=specific_name)
    else:
        wc_service.export_vat_rates()
