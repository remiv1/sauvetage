"""Module de routage pour les utilisateurs (users) de l'application Sauvetage."""

from fastapi import APIRouter

router = APIRouter(
    prefix="/users",
    tags=["users", "admin", "auth"],
)

@router.get("/")
async def read_users():
    """Endpoint de test pour vérifier que le routage fonctionne."""
    return {"message": "Endpoint /users/ est opérationnel."}
