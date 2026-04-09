"""Utilitaires de génération de documents (PDF + QRCode)."""

from __future__ import annotations

import base64
import io
from typing import Any, Dict, Tuple, Optional

import qrcode  # type: ignore[import-not-found]
from qrcode.image.svg import SvgPathImage  # type: ignore[import-not-found]

from app_front.config import DOCUMENTS, post


def build_qrcode_data_uri(target_url: str) -> str:
    """Construit un QRCode SVG encodé en data URI."""
    qr = qrcode.QRCode(
        error_correction=qrcode.ERROR_CORRECT_M,
        box_size=8,
        border=1,
    )
    qr.add_data(target_url)
    qr.make(fit=True)
    image = qr.make_image(image_factory=SvgPathImage)

    svg_raw = image.to_string()
    svg_bytes = svg_raw if isinstance(svg_raw, bytes) else svg_raw.encode("utf-8")
    encoded = base64.b64encode(svg_bytes).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def create_pdf_from_template(
    template: str,
    data: Dict[str, Any],
    *,
    fallback_filename: str,
    filename: Optional[str] = None,
) -> Tuple[io.BytesIO, Optional[str]]:
    """Appelle l'API documents et renvoie un flux PDF et un nom de fichier."""
    payload = {
        "template": template,
        "data": data,
    }
    if filename:
        payload["filename"] = filename
    resp = post(DOCUMENTS["create"], payload)

    content = resp.get("content")
    if not content:
        raise ValueError("Le service documents n'a retourné aucun contenu PDF.")

    pdf_bytes = base64.b64decode(content)
    filename = resp.get("filename") or fallback_filename
    return io.BytesIO(pdf_bytes), filename
