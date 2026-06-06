"""Routes FastAPI pour les opérations background liées au site de e-commerce."""

import logging
from typing import Optional
from fastapi import APIRouter, BackgroundTasks
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
    session = next(config.get_main_session())
    wc_service = WCProductsService(session, separated_keys=True)
    if specific and specific_name:
        wc_service.export_vat_rates(name=specific_name)
    else:
        wc_service.export_vat_rates()

@router.post("/update-tags")
def update_tags():
    """Lit les tags WooCommerce et met à jour les tags locaux."""
    try:
        _run_sync_tags()
        return {"status": "synchronisation des tags terminée"}
    except (OSError, ValueError, RuntimeError) as e:
        logger.error("Erreur lors de la synchronisation des tags : %s", str(e))
        return {"status": "erreur lors de la synchronisation des tags", "error": str(e)}


@router.post("/import-vat-slugs")
def import_vat_slugs():
    """Lit les classes de taxe WooCommerce et met à jour wpwc_slug en local."""
    session = next(config.get_main_session())
    wc_service = WCProductsService(session, separated_keys=True)
    updated = wc_service.import_vat_slugs()
    return {"updated": updated}


def _run_sync_catalog() -> None:
    """Tâche exécutée en arrière-plan : synchronise le catalogue vers WooCommerce."""
    session = next(config.get_main_session())
    try:
        wc_service = WCProductsService(session, separated_keys=True)
        wc_service.export_all_products()
    finally:
        session.close()

def _run_sync_tags() -> None:
    """Tâche exécutée en arrière-plan : synchronise les tags vers WooCommerce."""
    session = next(config.get_main_session())
    try:
        wc_service = WCProductsService(session, separated_keys=True)
        wc_service.export_tags()
    finally:
        session.close()


@router.post("/sync-tags", status_code=202)
def sync_tags(background_tasks: BackgroundTasks):
    """Déclenche la synchronisation des tags vers WooCommerce en arrière-plan."""
    background_tasks.add_task(_run_sync_tags)
    return {"status": "synchronisation des tags démarrée"}


@router.post("/sync-catalog", status_code=202)
def sync_catalog(background_tasks: BackgroundTasks):
    """Déclenche la synchronisation du catalogue produits vers WooCommerce en arrière-plan.

    Retourne immédiatement 202 Accepted pendant que la tâche s'exécute.
    """
    background_tasks.add_task(_run_sync_catalog)
    return {"status": "synchronisation démarrée"}
