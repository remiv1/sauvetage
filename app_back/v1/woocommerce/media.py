"""Routes FastAPI — création de jetons d'accès temporaires pour les images WooCommerce."""

import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from app_back.db_connection import config
from app_back.utils.decorators import access_control
from db_models.repositories.objects.media_access_token import MediaAccessTokenRepository

router = APIRouter(prefix="/media", tags=["woo_commerce", "media"])
logger = logging.getLogger(__name__)


@router.post(
    "/{filename}/access",
    responses={500: {"description": "Erreur interne lors de la création du jeton"}},
)
def create_access_token(
    filename: str,
    _access: Annotated[bool, Depends(access_control())],
) -> dict:
    """Crée un jeton d'accès à usage unique (1 heure) pour le fichier ``filename``.

    Le jeton est le nom du fichier lui-même (UUID.webp), ce qui permet à
    WooCommerce d'enregistrer l'image sous ce nom lors du téléchargement.

    Retourne l'URL publique à communiquer à WooCommerce ainsi que la date
    d'expiration du jeton.
    """
    session = next(config.get_main_session())
    repo = MediaAccessTokenRepository(session)

    existing = repo.get(filename)
    if existing and existing.is_valid():
        token = existing
    else:
        try:
            token = repo.create(filename)
        except ValueError as exc:
            logger.exception("Erreur création jeton pour %s : %s", filename, exc)
            raise HTTPException(
                status_code=500,
                detail="Erreur interne lors de la création du jeton."
            ) from exc

    return {
        "token": token.token,
        "valid_until": token.valid_until.isoformat(),
    }
