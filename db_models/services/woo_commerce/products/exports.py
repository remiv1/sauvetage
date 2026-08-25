"""Exports batch des produits, tags et médias WooCommerce."""

import logging
import os
from typing import Any, Sequence

from db_models.repositories.objects import GeneralObjects
from db_models.repositories.objects.media import MediaFiles
from db_models.repositories.tags import Tags
from db_models.services.utils import slugify

logger = logging.getLogger(__name__)


class ProductExportsMixin:
    """Responsabilités d'export batch vers WooCommerce."""

    def export_all_products(self: Any) -> None:
        """Exporte tous les produits actifs et leurs variations."""
        products = self.object_repo.get_all(only_actives=True)
        data = self._diff_objects(products, self.fetch_all_wc_products())
        returns: list[dict[str, list[dict[str, Any]]]] = []
        try:
            for batch in data:
                response = self.api_write.post("products/batch", data=batch)
                response.raise_for_status()
                returns.append(response.json())
        except Exception as exc:  # pylint: disable=broad-except
            self._log_export_failure("object", products, "batch", exc)
            return
        for result in returns:
            self._apply_product_returns(result, products)
        try:
            for product in products:
                self._sync_product_variations(product)
        except Exception as exc:  # pylint: disable=broad-except
            self._log_export_failure("object", products, "batch", exc)
            return
        self.session.commit()

    def export_tags(self: Any) -> None:
        """Exporte les tags actifs vers WooCommerce."""
        tags = self.tag_repo.get_all(only_actives=True)
        if not tags:
            return
        try:
            result = self.api_write.post(
                "products/tags/batch",
                data=self._diff_tags(tags, self.api_read.get("products/tags").json()),
            ).json()
        except Exception as exc:  # pylint: disable=broad-except
            self._log_export_failure("tag", tags, "batch", exc)
            return
        self._apply_tag_returns(result, tags)
        self.session.commit()

    def export_pictures(self: Any) -> None:
        """Exporte les médias locaux vers WooCommerce."""
        pictures = self.media_repo.get_all()
        if not pictures:
            return
        try:
            result = self.api_write.post(
                "media/batch",
                data=self._diff_pictures(pictures, self.api_read.get("media").json()),
            ).json()
        except Exception as exc:  # pylint: disable=broad-except
            self._log_export_failure("media", pictures, "batch", exc)
            return
        self._apply_picture_returns(result, pictures)
        self.session.commit()

    def _log_export_failure(self: Any, entity_type: str, entities: Sequence[Any], operation: str, exc: Exception) -> None:
        """Journalise une erreur d'export et confirme la transaction."""
        logger.exception("Erreur d'export WooCommerce des %s", entity_type)
        for entity in entities:
            self._log_sync(
                entity_type=entity_type, entity_id=entity.id, wpwc_id=entity.wpwc_id,
                operation=operation, sync_status="error", error_message=str(exc),
            )
        self.session.commit()

    def _diff_tags(self, tags: Sequence[Tags], remote_tags: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Calcule le diff des tags locaux et distants."""
        data = {"create": [], "update": [], "delete": []}
        remote_ids = {int(tag["id"]) for tag in remote_tags}
        for tag in tags:
            remote = next((item for item in remote_tags if int(item["id"]) == int(tag.wpwc_id or 0)), None)
            payload = {"name": tag.name, "slug": slugify(tag.name), "description": tag.description or ""}
            if remote:
                payload["id"] = int(remote["id"])
                data["update"].append(payload)
                remote_ids.discard(payload["id"])
            else:
                data["create"].append(payload)
        data["delete"] = [{"id": remote_id} for remote_id in remote_ids]
        return data

    def _diff_pictures(self, pictures: Sequence[MediaFiles], remote_pictures: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Calcule le diff des médias locaux et distants."""
        data = {"create": [], "update": [], "delete": []}
        remote_ids = {int(picture["id"]) for picture in remote_pictures}
        for picture in pictures:
            remote = next((item for item in remote_pictures if int(item["id"]) == int(picture.wpwc_id or 0)), None)
            payload = {
                "name": os.path.basename(picture.file_link or "") or picture.file_link or "",
                "alt": picture.alt_text or "",
                "src": self._build_media_src(picture),
            }
            if remote:
                payload["id"] = int(remote["id"])
                data["update"].append(payload)
                remote_ids.discard(payload["id"])
            else:
                data["create"].append(payload)
        data["delete"] = [{"id": remote_id} for remote_id in remote_ids]
        return data