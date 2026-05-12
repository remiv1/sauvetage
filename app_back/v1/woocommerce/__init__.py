"""Module d'API pour les opérations liées au site de e-commerce."""

from fastapi import APIRouter
from .background_transactions import router as background_router
from .media import router as media_router

router = APIRouter(prefix="/woo-commerce")
router.include_router(background_router)
router.include_router(media_router)
