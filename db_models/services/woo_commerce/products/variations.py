"""Synchronisation des variations produits WooCommerce."""

import logging
from typing import Any

from requests.exceptions import RequestException

from db_models.objects import ObjectVariations

logger = logging.getLogger(__name__)


class ProductVariationsMixin:
    """Responsabilités de synchronisation des variations produit."""

    def _fetch_all_wc_variations(self: Any, product_id: int) -> list[dict[str, Any]]:
        """Récupère toutes les pages de variations d'un produit WooCommerce."""
        variations: list[dict[str, Any]] = []
        page = 1
        while True:
            response = self.api_read.get(
                f"products/{product_id}/variations",
                params={"page": page, "per_page": 100},
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError(
                    f"Réponse WooCommerce invalide pour les variations du produit {product_id}."
                )
            variations.extend(payload)
            if len(payload) < 100:
                return variations
            page += 1

    def _sync_product_variations(self: Any, product: Any) -> None:
        """Crée, met à jour ou supprime les variations WooCommerce d'un produit."""
        if not product.wpwc_id or not product.object_variations:
            return
        remote_variations = self._fetch_all_wc_variations(product.wpwc_id)
        by_id = {int(item["id"]): item for item in remote_variations}
        by_sku = {
            str(item.get("sku")): item
            for item in remote_variations
            if item.get("sku") not in (None, "")
        }
        for variation in product.object_variations:
            matched = by_id.get(int(variation.wpwc_id or 0)) or by_sku.get(
                f"{product.id}-{variation.id}"
            )
            if matched:
                variation.wpwc_id = int(matched["id"])
            self._sync_product_variation(product.wpwc_id, variation, matched)

    def _sync_product_variation(
        self: Any,
        product_id: int,
        variation: ObjectVariations,
        matched: dict[str, Any] | None,
    ) -> None:
        """Synchronise une variation via son endpoint WooCommerce individuel."""
        payload: dict[str, Any] | None = None
        if variation.is_active:
            payload = variation.to_dict_for_woo_commerce()
            if matched:
                action = "update"
                response = self.api_write.put(
                    f"products/{product_id}/variations/{int(matched['id'])}", data=payload
                )
            else:
                action = "create"
                response = self.api_write.post(f"products/{product_id}/variations", data=payload)
        elif matched:
            action = "delete"
            response = self.api_write.delete(
                f"products/{product_id}/variations/{int(matched['id'])}",
                params={"force": True},
            )
        else:
            variation.wpwc_id = None
            return

        try:
            response.raise_for_status()
        except RequestException as exc:
            logger.error(
                "Échec WooCommerce variation locale=%d action=%s url=%s payload=%s réponse=%s",
                variation.id,
                action,
                getattr(response, "url", ""),
                payload,
                (getattr(response, "text", "") or "")[:1000],
            )
            raise exc
        item = response.json()
        if not isinstance(item, dict) or not item.get("id"):
            raise ValueError(f"Réponse WooCommerce invalide pour la variation {variation.id}.")
        wc_id = int(item["id"])
        variation.wpwc_id = None if action == "delete" else wc_id
        self._log_sync(
            entity_type="variation",
            entity_id=variation.id,
            wpwc_id=wc_id,
            operation=action,
            sync_status="success",
        )
