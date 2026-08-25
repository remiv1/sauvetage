"""Synchronisation unitaire et diff des produits WooCommerce."""

import json
import logging
from typing import Any, Sequence

from requests.exceptions import RequestException

from db_models.repositories.objects import GeneralObjects

logger = logging.getLogger(__name__)


class ProductCatalogMixin:
    """Responsabilités de calcul de diff et de mise à jour d'un produit."""

    @staticmethod
    def _get_product_sync_status(has_batch_effect: bool, has_valid_wc_id: bool) -> str:
        """Détermine le statut final d'une synchronisation produit."""
        if has_batch_effect and has_valid_wc_id:
            return "success"
        if has_batch_effect:
            return "error"
        return "no change"

    def _ensure_product_tags_are_synced(self: Any, product: GeneralObjects) -> None:
        """Synchronise les tags d'un produit avant son export."""
        if any(
            object_tag and object_tag.tag and object_tag.tag.wpwc_id is None
            for object_tag in (product.object_tags or [])
        ):
            logger.info("Produit %s: export des tags non synchronisés.", product.id)
            self.export_tags()

    def update_product(self: Any, product_id: int) -> int | None:
        """Crée ou met à jour un produit local dans WooCommerce."""
        product = self.object_repo.get_by_ref(product_id, only_actives=False)
        if product is None:
            return None
        if not product.is_active:
            logger.warning("Produit avec ID %d inactif. Mise à jour ignorée.", product_id)
            return product.wpwc_id

        self._ensure_product_tags_are_synced(product)
        remote_product = self.api_read.get(
            f"products/{product.wpwc_id}"
        ).json() if product.wpwc_id else None
        data = self._diff_objects([product], [remote_product] if remote_product else [])
        returns: list[dict[str, list[dict[str, Any]]] ] = []
        try:
            for batch in data:
                response = self.api_write.post("products/batch", data=batch)
                response.raise_for_status()
                result = response.json()
                logger.info(
                    "Retour WooCommerce produit %d: HTTP %s - %s",
                    product_id,
                    getattr(response, "status_code", "unknown"),
                    (getattr(response, "text", None) or json.dumps(result, default=str))[:1000],
                )
                returns.append(result)
        except (RequestException, ValueError) as exc:
            logger.exception("Erreur de synchronisation WooCommerce du produit %d", product_id)
            self._log_sync(
                entity_type="object", entity_id=product.id, wpwc_id=product.wpwc_id,
                operation="update", sync_status="error", error_message=str(exc),
            )
            self.session.commit()
            return product.wpwc_id

        for result in returns:
            self._apply_product_returns(result, [product])
        self.session.flush()
        self._sync_product_variations(product)
        self.session.commit()
        has_batch_effect = any(result.get("create") or result.get("update") for result in returns)
        status = self._get_product_sync_status(has_batch_effect, bool(product.wpwc_id))
        if status == "error":
            logger.warning("Produit %d sans identifiant WooCommerce après synchronisation.", product_id)
        return product.wpwc_id if status == "success" else None

    def fetch_all_wc_products(self: Any) -> list[dict[str, Any]]:
        """Récupère tous les produits WooCommerce, page par page."""
        products: list[dict[str, Any]] = []
        page = 1
        while True:
            payload = self.api_read.get("products", params={"page": page, "per_page": 100}).json()
            if not payload:
                return products
            products.extend(payload)
            page += 1

    def _diff_objects(
        self: Any,
        objects: Sequence[GeneralObjects],
        remote_objects: list[dict[str, Any]],
    ) -> list[dict[str, list[dict[str, Any]]]]:
        """Calcule les lots de créations, mises à jour et suppressions produit."""
        batches: list[dict[str, list[dict[str, Any]]]] = []
        batch = {"create": [], "update": [], "delete": []}
        remote_ids = {int(item["id"]) for item in remote_objects}
        for index, product in enumerate(objects, start=1):
            remote = next(
                (item for item in remote_objects if int(item["id"]) == int(product.wpwc_id or 0)),
                None,
            )
            if remote:
                payload = self._build_product_payload(product)
                payload["id"] = int(remote["id"])
                batch["update"].append(payload)
                remote_ids.discard(int(remote["id"]))
            else:
                batch["create"].append(self._build_product_payload(product))
            if index % 100 == 0 or index == len(objects):
                batches.append(batch)
                batch = {"create": [], "update": [], "delete": []}
        for remote_id in remote_ids:
            batch["delete"].append({"id": remote_id})
            if sum(len(items) for items in batch.values()) >= 100:
                batches.append(batch)
                batch = {"create": [], "update": [], "delete": []}
        if any(batch.values()):
            batches.append(batch)
        return batches