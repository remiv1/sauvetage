"""Module d'API pour les opérations liées à Henrri."""

from fastapi import APIRouter
from .background_transactions import router as background_transactions_router

henrri_router = APIRouter(prefix="/henrri")
henrri_router.include_router(background_transactions_router)
