"""Construction des payloads produits WooCommerce."""

import os
from decimal import Decimal, InvalidOperation
from typing import Any

from db_models.repositories.objects import GeneralObjects
from db_models.repositories.objects.media import MediaFiles
from db_models.repositories.objects.media_access_token import MediaAccessTokenRepository
from db_models.repositories.stocks.inventory import InventoryRepository
from db_models.services.woo_commerce.utils import _merge_attribute_lists

from .constants import FRONT_BASE_URL, OBJECT_TYPE_MAPPING, PROTOCOL


class ProductPayloadMixin:  # pylint: disable=R0903
    """Responsabilités de sérialisation d'un produit pour WooCommerce."""

    @staticmethod
    def _build_variation_attribute(product: GeneralObjects) -> dict[str, Any] | None:
        """Construit l'attribut WooCommerce porté par les variations actives."""
        options = [
            variation.name
            for variation in product.object_variations
            if variation.is_active and variation.name
        ]
        if not options:
            return None
        if not product.object_variation_attribut:
            raise ValueError(
                f"Le produit {product.id} possède des variations sans attribut défini."
            )
        return {
            "name": product.object_variation_attribut,
            "options": list(dict.fromkeys(options)),
            "visible": True,
            "variation": True,
        }

    def _merge_product_variation_attribute(
        self: Any,
        product: GeneralObjects,
        payload: dict[str, Any],
    ) -> None:
        """Ajoute l'attribut de variation aux attributs du produit parent."""
        attribute = self._build_variation_attribute(product)
        if attribute is None:
            return
        current = payload.get("attributes", [])
        payload["attributes"] = _merge_attribute_lists(
            current if isinstance(current, list) else [],
            [attribute],
        )

    def _update_stock_quantity(
        self: Any,
        product: GeneralObjects,
        payload: dict[str, Any],
    ) -> None:
        """Met à jour la quantité en stock dans le payload produit."""
        inventory_repo = InventoryRepository(self.session)
        payload["stock_quantity"] = inventory_repo.get_available_quantity(product.id)

    def _update_categories(
        self: Any,
        product: GeneralObjects,
        payload: dict[str, Any],
    ) -> None:
        """Met à jour les catégories dans le payload produit."""
        payload["categories"] = [
            {"id": category_id}
            for category_id in self._get_product_category_ids(product)
        ]
    def _build_product_payload(self: Any, product: GeneralObjects) -> dict[str, Any]:
        """Construit le payload produit complet destiné à WooCommerce."""
        payload = product.to_dict_for_woo_commerce()
        self._update_categories(product, payload)
        self._update_stock_quantity(product, payload)
        self._merge_product_attributes(product, payload)
        self._add_product_measurements(product, payload)
        self._add_synced_tags(product, payload)
        self._add_media(product, payload)
        return payload

    @staticmethod
    def _get_product_category_ids(product: GeneralObjects) -> list[int]:
        """Retourne les catégories WooCommerce correspondant au type d'objet."""
        return OBJECT_TYPE_MAPPING.get(product.general_object_type, [15])

    def _merge_product_attributes(
        self: Any,
        product: GeneralObjects,
        payload: dict[str, Any],
    ) -> None:
        """Fusionne les attributs spécialisés et les attributs de variation."""
        for related_object in (product.book, product.other_object, product.obj_metadatas):
            if related_object is None:
                continue
            attributes = related_object.to_dict_for_woo_commerce().get("attributes", [])
            current = payload.get("attributes", [])
            payload["attributes"] = _merge_attribute_lists(
                current if isinstance(current, list) else [],
                attributes,
            )
        self._merge_product_variation_attribute(product, payload)

    def _add_product_measurements(
        self: Any, product: GeneralObjects, payload: dict[str, Any],
    ) -> None:
        if product.obj_metadatas is None:
            return
        metadata = product.obj_metadatas.semistructured_data
        if not isinstance(metadata, dict):
            return
        weight = self._measurement_string(metadata.get("poids_grammes"))
        if weight is not None:
            payload["weight"] = weight
        raw_dimensions = metadata.get("dimensions_mm")
        if not isinstance(raw_dimensions, str):
            return
        parts = raw_dimensions.split("*")
        if len(parts) != 3:
            return
        dimensions = [self._measurement_string(part) for part in parts]
        if any(value is None for value in dimensions):
            return
        payload["dimensions"] = dict(zip(("length", "width", "height"), dimensions))

    @staticmethod
    def _measurement_string(value: Any) -> str | None:
        if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
            return None
        try:
            measurement = Decimal(str(value).strip())
        except InvalidOperation:
            return None
        if not measurement.is_finite() or measurement < 0:
            return None
        return format(measurement, "f")

    @staticmethod
    def _add_synced_tags(product: GeneralObjects, payload: dict[str, Any]) -> None:
        """Ajoute uniquement les tags déjà synchronisés vers WooCommerce."""
        tags = [
            {"id": object_tag.tag.wpwc_id}
            for object_tag in (product.object_tags or [])
            if object_tag and object_tag.tag and object_tag.tag.wpwc_id is not None
        ]
        if tags:
            payload["tags"] = tags

    def _add_media(self: Any, product: GeneralObjects, payload: dict[str, Any]) -> None:
        """Ajoute les images du produit au payload WooCommerce."""
        if not product.media_files:
            return
        payload["images"] = [
            self._build_media_payload(product, media)
            for media in product.media_files
        ]

    def _build_media_payload(
        self: Any,
        product: GeneralObjects,
        media: MediaFiles,
    ) -> dict[str, str]:
        """Construit le payload d'une image WooCommerce."""
        filename = os.path.basename(media.file_link or "") or media.file_link or ""
        return {
            "src": self._build_media_src(media),
            "name": filename,
            "alt": f"{product.name} - {media.alt_text or filename}",
        }

    def _build_media_src(self: Any, media: MediaFiles) -> str:
        """Construit une URL publique ou protégée pour un média WooCommerce."""
        file_link = media.file_link or ""
        is_local = bool(media.is_local) or not file_link.startswith(
            (f"{PROTOCOL}://", f"{PROTOCOL}s://")
        )
        if not is_local:
            return file_link

        base_url = (FRONT_BASE_URL or "https://internal.editions-sauvetage.fr").strip().rstrip("/")
        token_repo = MediaAccessTokenRepository(self.session)
        existing = token_repo.get_last_by_media_id(media.id)
        if existing and existing.is_valid():
            token = existing
        elif existing:
            token = token_repo.renew(existing)
        else:
            token = token_repo.create(media_id=media.id)
        filename = os.path.basename(file_link) or f"media_{media.id}"
        return f"{base_url}/woocommerce/media/{token.token}/{filename}"
