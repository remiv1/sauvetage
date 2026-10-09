"""Synchronisation unitaire et diff des produits WooCommerce."""

import logging
from typing import Any, Sequence

from requests.exceptions import RequestException

from db_models.repositories.objects import GeneralObjects

logger = logging.getLogger(__name__)
PRODUCT_BATCH_SIZE = 15


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

        stage = "prepare"
        try:
            self._ensure_product_tags_are_synced(product)
            if product.wpwc_id:
                response = self.api_read.get(f"products/{product.wpwc_id}")
                response.raise_for_status()
                remote_product = response.json()
                if not isinstance(remote_product, dict):
                    raise ValueError("Réponse WooCommerce invalide pour le produit.")
            else:
                remote_product = self._find_product_by_sku(str(product.id))
            data = self._diff_objects([product], [remote_product] if remote_product else [])
            for batch in data:
                stage = "batch"
                self._send_product_batch(batch, [product])
            stage = "variations"
            self._sync_product_variations(product)
            self.session.commit()
        except (RequestException, ValueError) as exc:
            logger.exception("Erreur de synchronisation WooCommerce du produit %d", product_id)
            if stage != "batch":
                self._log_sync(
                    entity_type="object", entity_id=product.id, wpwc_id=product.wpwc_id,
                    operation="update", sync_status="error", error_message=str(exc),
                )
            self.session.commit()
            return None

        has_batch_effect = any(batch.get("create") or batch.get("update") for batch in data)
        status = self._get_product_sync_status(has_batch_effect, bool(product.wpwc_id))
        if status == "error":
            logger.warning(
                "Produit %d sans identifiant WooCommerce après synchronisation.",
                product_id,
            )
        return product.wpwc_id if status == "success" else None

    def fetch_all_wc_products(self: Any) -> list[dict[str, Any]]:
        """Récupère tous les produits WooCommerce, page par page."""
        products: list[dict[str, Any]] = []
        page = 1
        while True:
            response = self.api_read.get("products", params={"page": page, "per_page": 100})
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("Catalogue WooCommerce invalide : une liste est attendue.")
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
        remote_ids = {self._product_wc_id(item) for item in remote_objects}
        for index, product in enumerate(objects, start=1):
            remote = self._match_remote_product(product, remote_objects)
            if remote:
                product.wpwc_id = int(remote["id"])
                payload = self._build_product_payload(product)
                payload["id"] = int(remote["id"])
                batch["update"].append(payload)
                remote_ids.discard(int(remote["id"]))
            else:
                batch["create"].append(self._build_product_payload(product))
            if index % PRODUCT_BATCH_SIZE == 0 or index == len(objects):
                batches.append(batch)
                batch = {"create": [], "update": [], "delete": []}
        for remote_id in remote_ids:
            batch["delete"].append({"id": remote_id})
            if sum(len(items) for items in batch.values()) >= PRODUCT_BATCH_SIZE:
                batches.append(batch)
                batch = {"create": [], "update": [], "delete": []}
        if any(batch.values()):
            batches.append(batch)
        return batches

    @staticmethod
    def _match_remote_product(
        product: GeneralObjects, remote_objects: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        remote = next((
            item for item in remote_objects if int(item["id"]) == int(product.wpwc_id or 0)
        ), None)
        if remote is not None:
            return remote
        matches = [item for item in remote_objects if str(item.get("sku")) == str(product.id)]
        if len(matches) > 1:
            raise ValueError(f"UGS WooCommerce ambigu pour le produit {product.id}.")
        return matches[0] if matches else None
