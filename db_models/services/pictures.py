"""Utilitaires de traitement et de persistance des fichiers image.

Pipeline appliqué à chaque upload :
  1. Lecture du FileStorage WTForms via read_upload_from_entry().
  2. Compression WebP via compress_to_webp() :
       - Redimensionnement à max 800×1200 (ratio conservé, filtre Lanczos).
       - Conversion en WebP avec réduction itérative de la qualité (80→10, pas
         de 5) jusqu'à passer sous 100 Ko.
       - Si Pillow est absent ou si le fichier n'est pas une image reconnue,
         le contenu original est renvoyé avec son extension d'origine.
  3. Écriture sur le volume partagé via save_picture_to_disk().
"""

import io
import os
import uuid
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Constantes de compression
# ---------------------------------------------------------------------------
_IMG_MAX_WIDTH = 800
_IMG_MAX_HEIGHT = 1200
_IMG_TARGET_BYTES = 100 * 1024  # 100 Ko
_IMG_INITIAL_QUALITY = 80
_IMG_MIN_QUALITY = 10
_IMG_QUALITY_STEP = 5


# ---------------------------------------------------------------------------
# Lecture de l'upload WTForms
# ---------------------------------------------------------------------------

def read_upload_from_entry(entry: Any) -> tuple[Optional[bytes], Optional[str]]:
    """Lit le FileStorage d'un champ WTForms et retourne (contenu, nom_original).

    Retourne (None, None) si le champ est absent ou vide.
    """
    file_storage = entry._fields.get("file_data")
    if not (file_storage and hasattr(file_storage.data, "read")):
        return None, None
    original_filename = getattr(file_storage.data, "filename", "") or ""
    content = file_storage.data.read() or None
    return content, original_filename


# ---------------------------------------------------------------------------
# Compression WebP
# ---------------------------------------------------------------------------

def compress_to_webp(content: bytes, original_filename: str) -> tuple[bytes, str]:
    """Compresse le contenu en WebP et retourne (données_finales, extension).

    Si le fichier n'est pas une image ou si Pillow est absent, retourne le
    contenu original avec son extension d'origine.
    """
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        return content, _ext(original_filename)

    try:
        img = Image.open(io.BytesIO(content))
    except OSError:
        return content, _ext(original_filename)

    img.thumbnail((_IMG_MAX_WIDTH, _IMG_MAX_HEIGHT), Image.Resampling.LANCZOS)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    quality = _IMG_INITIAL_QUALITY
    buf = io.BytesIO()
    while quality >= _IMG_MIN_QUALITY:
        buf.seek(0)
        buf.truncate()
        img.save(buf, format="WEBP", quality=quality)
        if buf.tell() <= _IMG_TARGET_BYTES:
            break
        quality -= _IMG_QUALITY_STEP

    return buf.getvalue(), ".webp"


# ---------------------------------------------------------------------------
# Persistance sur le volume
# ---------------------------------------------------------------------------

def save_picture_to_disk(
    content: bytes, original_filename: str, upload_dir: str
) -> str:
    """Compresse si possible et écrit le fichier sur le volume.

    Retourne le nom de fichier généré (UUID + extension).
    """
    processed, ext = compress_to_webp(content, original_filename)
    filename = str(uuid.uuid4()) + ext
    with open(os.path.join(upload_dir, filename), "wb") as fh:
        fh.write(processed)
    return filename


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _ext(filename: str) -> str:
    return os.path.splitext(filename)[1].lower() if filename else ""
