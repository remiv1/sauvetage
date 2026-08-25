"""Tests autour des médias WooCommerce et des URLs de médias."""

from unittest.mock import MagicMock, patch

import struct
import zlib

from db_models.objects import MediaFiles
from db_models.services.woo_commerce.products import WCProductsService
from app_front.blueprints.woocommerce.routes import serve_media


def _make_png_bytes() -> bytes:
    """Crée un PNG minimal, valide et indépendant de Pillow."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(
            ">I", len(data)
        ) + tag + data + struct.pack(
            ">I", zlib.crc32(tag + data) & 0xFFFFFFFF
        )

    raw_scanline = b"\x00\x00\x00\x00\x00"
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw_scanline))
        + chunk(b"IEND", b"")
    )


def test_wc_product_build_media_src_uses_internal_public_host_when_env_missing(monkeypatch) -> None:
    """
    Sans FRONT_BASE_URL explicit, le service doit utiliser le host interne public attendu
    par WooCommerce.
    """
    monkeypatch.setattr("db_models.services.woo_commerce.products.payloads.FRONT_BASE_URL", "")

    service = object.__new__(WCProductsService)
    service.session = MagicMock()
    media = MagicMock(spec=MediaFiles)
    media.id = 42
    media.is_local = True
    media.file_link = "29334045_main.jpg"

    url = service._build_media_src(media)  # pylint: disable=W0212

    assert "https://internal.editions-sauvetage.fr/woocommerce/media/" in url
    assert "/29334045_main.jpg" in url


def test_wc_product_build_media_src_uses_token_for_absolute_local_paths(monkeypatch) -> None:
    """Un chemin de fichier local absolu doit quand même être servi via le jeton publique."""
    monkeypatch.setattr("db_models.services.woo_commerce.products.payloads.FRONT_BASE_URL", "")

    service = object.__new__(WCProductsService)
    service.session = MagicMock()
    media = MagicMock(spec=MediaFiles)
    media.id = 43
    media.is_local = False
    media.file_link = "/app/data-seed/images/29334045_main.jpg"

    with patch(
        "db_models.services.woo_commerce.products.payloads.MediaAccessTokenRepository"
    ) as repo_cls:
        repo = repo_cls.return_value
        repo.get_last_by_media_id.return_value = None
        repo.create.return_value = MagicMock(token="token-abc123")

        url = service._build_media_src(media)  # pylint: disable=W0212

    base_url = "https://internal.editions-sauvetage.fr/woocommerce/media"
    assert f"{base_url}/token-abc123/29334045_main.jpg" in url
    assert "/app/data-seed/images/" not in url


def test_woo_media_route_resolves_media_by_id_and_serves_file(monkeypatch) -> None:
    """La route WooCommerce doit lire le média via son id, pas via un filtre invalide."""
    monkeypatch.setattr("app_front.blueprints.woocommerce.routes._MEDIA_UPLOAD_DIR", "/tmp/images")
    session = MagicMock()
    monkeypatch.setattr(
        "app_front.blueprints.woocommerce.routes.db_conf.get_main_session",
        lambda: session
    )

    token_record = MagicMock()
    token_record.is_valid.return_value = True
    token_record.media_file_id = 77

    media_file = MagicMock()
    media_file.file_link = "cover.jpg"

    with patch(
            "app_front.blueprints.woocommerce.routes.MediaAccessTokenRepository",
        ) as token_repo_cls, \
         patch(
            "app_front.blueprints.woocommerce.routes.MediaRepository",
        ) as media_repo_cls, \
         patch(
            "app_front.blueprints.woocommerce.routes.send_from_directory",
            return_value="OK",
        ):
        token_repo = token_repo_cls.return_value
        token_repo.get.return_value = token_record
        media_repo = media_repo_cls.return_value
        media_repo.get_by_id.return_value = media_file

        response = serve_media("valid-token", "cover.jpg")

    assert response == "OK"
    media_repo.get_by_id.assert_called_once_with(77)


def test_woo_media_route_uses_basename_for_local_file(monkeypatch) -> None:
    """Une URL de média historique avec chemin absolu doit être servie via son nom de fichier."""
    monkeypatch.setattr(
        "app_front.blueprints.woocommerce.routes._MEDIA_UPLOAD_DIR",
        "/tmp/images"
    )
    monkeypatch.setattr(
        "app_front.blueprints.woocommerce.routes.db_conf.get_main_session",
        MagicMock()
    )

    token_record = MagicMock()
    token_record.is_valid.return_value = True
    token_record.media_file_id = 77

    media_file = MagicMock()
    media_file.file_link = "/app/data-seed/images/29334045_main.jpg"

    with patch(
            "app_front.blueprints.woocommerce.routes.MediaAccessTokenRepository",
        ) as token_repo_cls, \
         patch(
            "app_front.blueprints.woocommerce.routes.MediaRepository",
        ) as media_repo_cls, \
         patch(
            "app_front.blueprints.woocommerce.routes.send_from_directory",
            return_value="OK",
        ) as send_mock:
        token_repo = token_repo_cls.return_value
        token_repo.get.return_value = token_record
        media_repo = media_repo_cls.return_value
        media_repo.get_by_id.return_value = media_file

        response = serve_media("valid-token", "29334045_main.jpg")

    assert response == "OK"
    send_mock.assert_called_once_with("/tmp/images", "29334045_main.jpg")


def test_woo_media_route_serves_existing_absolute_local_file(monkeypatch, tmp_path) -> None:
    """
    Quand le média historique est un chemin absolu existant, la route doit servir ce
    fichier lui-même.
    """
    image_path = tmp_path / "29334045_main.png"
    image_path.write_bytes(_make_png_bytes())
    monkeypatch.setattr(
        "app_front.blueprints.woocommerce.routes._MEDIA_UPLOAD_DIR",
        str(tmp_path),
    )
    monkeypatch.setattr(
        "app_front.blueprints.woocommerce.routes.db_conf.get_main_session",
        MagicMock(),
    )

    token_record = MagicMock()
    token_record.is_valid.return_value = True
    token_record.media_file_id = 77

    media_file = MagicMock()
    media_file.file_link = str(image_path)
    media_file.file_type = "img"

    with patch(
            "app_front.blueprints.woocommerce.routes.MediaAccessTokenRepository"
        ) as token_repo_cls, \
         patch(
            "app_front.blueprints.woocommerce.routes.MediaRepository",
        ) as media_repo_cls, \
         patch(
            "app_front.blueprints.woocommerce.routes.send_file",
            return_value="OK",
        ) as send_file_mock:
        token_repo = token_repo_cls.return_value
        token_repo.get.return_value = token_record
        media_repo = media_repo_cls.return_value
        media_repo.get_by_id.return_value = media_file

        response = serve_media("valid-token", image_path.name)

    assert response == "OK"
    send_file_mock.assert_called_once_with(str(image_path), mimetype="image/png")


def test_woo_media_route_detects_real_mime_from_file_content(monkeypatch, tmp_path) -> None:
    """Le type MIME réel du fichier doit prévaloir sur l'étiquette métier `img`."""
    image_path = tmp_path / "example.png"
    image_path.write_bytes(_make_png_bytes())

    monkeypatch.setattr(
        "app_front.blueprints.woocommerce.routes._MEDIA_UPLOAD_DIR",
        str(tmp_path),
    )
    monkeypatch.setattr(
        "app_front.blueprints.woocommerce.routes.db_conf.get_main_session",
        MagicMock(),
    )

    token_record = MagicMock()
    token_record.is_valid.return_value = True
    token_record.media_file_id = 77

    media_file = MagicMock()
    media_file.file_link = str(image_path)
    media_file.file_type = "img"

    with patch(
            "app_front.blueprints.woocommerce.routes.MediaAccessTokenRepository",
        ) as token_repo_cls, \
         patch(
            "app_front.blueprints.woocommerce.routes.MediaRepository",
        ) as media_repo_cls, \
         patch(
            "app_front.blueprints.woocommerce.routes.send_file",
            return_value="OK",
        ) as send_file_mock:
        token_repo = token_repo_cls.return_value
        token_repo.get.return_value = token_record
        media_repo = media_repo_cls.return_value
        media_repo.get_by_id.return_value = media_file

        response = serve_media("valid-token", image_path.name)

    assert response == "OK"
    send_file_mock.assert_called_once_with(str(image_path), mimetype="image/png")
