"""Module de routage principal pour l'application Sauvetage (sensible, async et background)."""

from fastapi import APIRouter
from app_back.v1 import user_router, inventory_router

v1_api_router = APIRouter(prefix="/v1")
v1_api_router.include_router(user_router)
v1_api_router.include_router(inventory_router)
