"""Module d'API pour les opérations liées à Dilicom."""

from fastapi import APIRouter
from .orders import router as orders_router

dilicom_router = APIRouter(prefix="/dilicom")
dilicom_router.include_router(orders_router)
