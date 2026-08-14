"""Routes FastAPI — création de jetons d'accès temporaires pour les images WooCommerce."""

import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from app_back.db_connection import config
from app_back.utils.decorators import access_control
from db_models.objects import MediaFiles
from db_models.repositories.objects import MediaRepository
from db_models.repositories.objects.media_access_token import MediaAccessTokenRepository

router = APIRouter(prefix="/media", tags=["woo_commerce", "media"])
logger = logging.getLogger(__name__)


@router.post(
    "/{media_id}/access",
    responses={
        500: {"description": "Erreur interne lors de la création du jeton"},
        404: {"description": "Fichier média introuvable"},
    },
)
def create_access_token(
    media_id: int,
    _access: Annotated[bool, Depends(access_control())],
) -> dict:
    """Crée un jeton temporaire associé à un média local existant.

    Le flux s'appuie sur l'identifiant ``media_id`` de la ligne ``MediaFiles``.
    Le jeton généré est opaque et lié à ``media_file_id`` pour sécuriser le
    téléchargement sans dépendre du nom du fichier.
    """
    session = next(config.get_main_session())
    repo = MediaAccessTokenRepository(session)
    mrepo = MediaRepository(session)

    media = mrepo.get_one(model=MediaFiles, filters={"id": media_id})

    if media is None:
        raise HTTPException(status_code=404, detail="Fichier média introuvable.")

    existing = repo.get_last_by_media_id(media.id)

    try:
        token = existing if existing and existing.is_valid() else repo.create(media_id=media.id)
    except ValueError as exc:
        logger.exception("Erreur création jeton pour %s : %s", media_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Erreur interne lors de la création du jeton.",
        ) from exc

    return {
        "token": token.token,
        "valid_until": token.valid_until.isoformat(),
    }
