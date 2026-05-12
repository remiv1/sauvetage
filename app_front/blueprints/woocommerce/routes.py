"""Blueprint WooCommerce — service d'images par jeton temporaire.

Routes :
  GET /woocommerce/media/<filename>
      Sert le fichier image si le jeton associé est valide et non consommé.
      Marque le jeton comme consommé après le premier téléchargement réussi.
      Route publique — le nom de fichier (UUID.webp) tient lieu de jeton.

La création des jetons est assurée par l'API back (FastAPI) via la route
POST /api/v1/woo-commerce/media/<filename>/access, sécurisée par X-Internal-Token.
"""

import logging
import os
from flask import Blueprint, abort, send_from_directory
from app_front.config import db_conf
from db_models.repositories.objects.media_access_token import MediaAccessTokenRepository

bp_woocommerce = Blueprint("woocommerce", __name__, url_prefix="/woocommerce")

logger = logging.getLogger(__name__)

_MEDIA_UPLOAD_DIR = os.environ.get("MEDIA_UPLOAD_DIR", "")


@bp_woocommerce.get("/media/<path:filename>")
def serve_media(filename: str):
    """Sert le fichier image si le jeton est valide et non consommé.

    Le jeton est consommé après le premier téléchargement réussi.
    """
    if not _MEDIA_UPLOAD_DIR:
        logger.error("MEDIA_UPLOAD_DIR non configuré")
        abort(503)

    repo = MediaAccessTokenRepository(db_conf.get_main_session())
    token = repo.get(filename)

    if token is None or not token.is_valid():
        abort(403)

    try:
        response = send_from_directory(_MEDIA_UPLOAD_DIR, filename)
    except FileNotFoundError:
        abort(404)

    try:
        repo.consume(token)
    except ValueError as exc:
        logger.warning("Impossible de consommer le jeton %s : %s", filename, exc)

    return response
