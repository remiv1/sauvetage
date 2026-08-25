"""Construction des payloads produits WooCommerce."""

import os
from typing import Any

from db_models.repositories.objects import GeneralObjects
from db_models.repositories.objects.media import MediaFiles
from db_models.repositories.objects.media_access_token import MediaAccessTokenRepository
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

    def _build_product_payload(self: Any, product: GeneralObjects) -> dict[str, Any]:
        """Construit le payload produit complet destiné à WooCommerce."""
        payload = product.to_dict_for_woo_commerce()
        payload["categories"] = [
            {"id": category_id}
            for category_id in self._get_product_category_ids(product)
        ]
        self._merge_product_attributes(product, payload)
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
