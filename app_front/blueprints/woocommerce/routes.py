"""Blueprint WooCommerce — service d'images par jeton temporaire."""

import logging
import os

import magic
from flask import Blueprint, abort, send_file, send_from_directory

from app_front.config import db_conf
from db_models.repositories.objects import MediaAccessTokenRepository, MediaRepository

bp_woocommerce = Blueprint("woocommerce", __name__, url_prefix="/woocommerce")
_MEDIA_UPLOAD_DIR = os.environ.get("MEDIA_UPLOAD_DIR", "")
logger = logging.getLogger(__name__)


def _detect_mime_type(file_path: str) -> str:
    """Retourne le vrai type MIME du fichier à partir de son contenu."""
    try:
        detected = magic.from_file(file_path, mime=True)
        logger.info("MIME détecté pour %s : %s", file_path, detected)
        if detected:
            return detected
    except (AttributeError, OSError, ValueError):
        logger.warning("Impossible de détecter le MIME réel pour %s", file_path)

    fallback = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(os.path.splitext(file_path.lower())[1], "application/octet-stream")
    logger.info("MIME de repli pour %s : %s", file_path, fallback)
    return fallback


@bp_woocommerce.get("/media/<token>/<path:filename>")
def serve_media(token: str, filename: str):
    """Retourne le fichier média associé au jeton WooCommerce et au nom demandé."""
    session = db_conf.get_main_session()
    repo = MediaAccessTokenRepository(session)
    record = repo.get(token)
    if record is None or not record.is_valid():
        logger.warning("Jeton WooCommerce invalide ou expiré : %s", token)
        abort(403)

    media_file = MediaRepository(session).get_by_id(record.media_file_id)
    if media_file is None or not media_file.file_link:
        logger.warning("Fichier média introuvable pour le jeton WooCommerce : %s", token)
        abort(404)

    file_link = media_file.file_link.strip()
    expected_filename = os.path.basename(file_link)
    requested_filename = os.path.basename(filename)
    if not expected_filename or requested_filename != expected_filename:
        logger.warning(
            "Nom de fichier demandé incohérent pour le jeton WooCommerce %s : attendu %s, reçu %s",
            token,
            expected_filename,
            requested_filename,
        )
        abort(404)

    if os.path.isabs(file_link) and os.path.isfile(file_link) and os.access(file_link, os.R_OK):
        candidate = file_link
    elif _MEDIA_UPLOAD_DIR:
        candidate = os.path.join(_MEDIA_UPLOAD_DIR, expected_filename)
        if not os.path.isfile(candidate):
            logger.warning(
                "Fichier média introuvable dans le répertoire upload pour le jeton "
                "WooCommerce : %s",
                token,
            )
            return send_from_directory(_MEDIA_UPLOAD_DIR, expected_filename)
    else:
        logger.warning(
            "Chemin de fichier média non absolu et répertoire upload non défini pour le jeton"
            " WooCommerce : %s",
            token,
        )
        abort(405)

    try:
        response = send_file(candidate, mimetype=_detect_mime_type(candidate))
    except OSError:
        logger.error(
            "Erreur lors de l'envoi du fichier média pour le jeton WooCommerce : %s",
            token,
        )
        abort(403)

    try:
        repo.consume(record)
    except ValueError:
        logger.error("Erreur lors de la consommation du jeton WooCommerce : %s", token)
    return response
