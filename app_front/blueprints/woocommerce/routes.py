"""Blueprint WooCommerce — service d'images par jeton temporaire.

Routes :
  GET /woocommerce/media/<token>
      Sert le fichier image si le jeton associé est valide et non consommé.
      Marque le jeton comme consommé après le premier téléchargement réussi.

La création des jetons est assurée par l'API back (FastAPI) via la route
POST /api/v1/woo-commerce/media/<filename>/access, sécurisée par X-Internal-Token.
"""

import logging
import os
from flask import Blueprint, abort, send_file, send_from_directory
from app_front.config import db_conf
from db_models.repositories.objects import MediaAccessTokenRepository, MediaRepository
from db_models.objects import MediaFiles
bp_woocommerce = Blueprint("woocommerce", __name__, url_prefix="/woocommerce")

logger = logging.getLogger(__name__)
_MEDIA_UPLOAD_DIR = os.environ.get("MEDIA_UPLOAD_DIR", "")


@bp_woocommerce.get("/media/<path:token>")
def serve_media(token: str):
    """Sert le fichier image si le jeton est valide et non consommé.

    Le token est lu depuis le chemin l'URL ; le fichier physique est ensuite
    résolu via la relation MediaAccessToken -> MediaFiles.
    """

    session = db_conf.get_main_session()
    repo = MediaAccessTokenRepository(session)
    mrepo = MediaRepository(session)
    record = repo.get(token)

    if record is None or not record.is_valid():
        abort(403)

    media_file = mrepo.get_one(MediaFiles, id=record.media_file_id)
    logger.debug("Jeton %s valide pour le média %s", token, media_file.id if media_file else None)
    logger.debug("Fichier associé : %s", media_file.file_link if media_file else None)

    if media_file is None or not media_file.file_link:
        logger.warning("Jeton %s valide mais média introuvable ou sans fichier", token)
        abort(404)

    if not _MEDIA_UPLOAD_DIR:
        logger.error("MEDIA_UPLOAD_DIR non configuré")
        abort(503)

    file_link = (media_file.file_link or "").strip()
    file_name = os.path.basename(file_link)
    if not file_name:
        logger.warning(
            "Jeton %s valide mais fichier introuvable pour le média %s",
            token,
            media_file.id,
        )
        abort(404)

    # Priorité : servir le chemin absolu réel si présent sur le disque.
    try:
        if os.path.isabs(file_link) and os.path.isfile(file_link):
            response = send_file(file_link, mimetype=getattr(media_file, "file_type", None) or None)
        else:
            # Essayer le fichier dans le répertoire d'upload configuré
            candidate = os.path.join(_MEDIA_UPLOAD_DIR, file_name)
            if os.path.isfile(candidate):
                response = send_file(candidate, mimetype=getattr(media_file, "file_type", None) or None)
            else:
                # Dernier recours : send_from_directory (lève 404 si absent)
                response = send_from_directory(_MEDIA_UPLOAD_DIR, file_name)
    except FileNotFoundError:
        abort(404)

    try:
        repo.consume(record)
    except ValueError as exc:
        logger.warning("Impossible de consommer le jeton %s : %s", token, exc)

    return response
