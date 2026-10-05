"""Traitement des retours batch WooCommerce."""

from typing import Any, Callable, Optional, Sequence

from requests.exceptions import RequestException
from sqlalchemy import select

from db_models.objects.vat import VatRate
from db_models.repositories.objects import GeneralObjects
from db_models.repositories.objects.media import MediaFiles
from db_models.repositories.tags import Tags


class BatchReturnsMixin:    # pylint: disable=R0903
    """Responsabilités d'appariement et de journalisation des retours batch."""

    def _process_returns_action(    # pylint: disable=R0913, R0917
        self: Any,
        action: str,
        items: list[dict[str, Any]],
        locals_: Sequence[Any],
        entity_type: str,
        matcher: Optional[Callable[[Sequence[Any], dict[str, Any]], Optional[Any]]],
        updater: Optional[Callable[[Any, int, dict[str, Any]], None]],
        finder_by_wc_id: Optional[Callable[[int], Optional[Any]]] = None,
    ) -> None:
        """Applique une action batch aux entités locales correspondantes."""
        for item in items:
            wc_id = int(item["id"])
            local = None
            if finder_by_wc_id:
                local = finder_by_wc_id(wc_id)
            elif matcher:
                local = matcher(locals_, item)
            if updater and local:
                updater(local, wc_id, item)
            self._log_sync(
                entity_type=entity_type,
                entity_id=local.id if local else None,
                wpwc_id=wc_id,
                operation=action,
                sync_status="success",
            )

    def _apply_returns_generic(
        self: Any,
        returns: dict[str, list[dict[str, Any]]],
        locals_: Sequence[Any],
        entity_type: str,
        matchers: dict[str, Callable[[Sequence[Any], dict[str, Any]], Optional[Any]]],
        updaters: dict[str, Callable[[Any, int, dict[str, Any]], None]],
        finder_by_wc_id: Optional[Callable[[int], Optional[Any]]] = None,
    ) -> None:
        """Distribue les retours create, update et delete à leur traitement commun."""
        for action in ("create", "update", "delete"):
            self._process_returns_action(
                action,
                returns.get(action, []),
                locals_,
                entity_type,
                matchers.get(action),
                updaters.get(action),
                finder_by_wc_id if action == "delete" else None,
            )

    def _apply_product_returns(
        self: Any,
        returns: dict[str, list[dict[str, Any]]],
        products: Sequence[GeneralObjects],
        batch: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        """Applique les retours batch produits."""
        errors: list[str] = []
        for action in ("create", "update", "delete"):
            errors.extend(self._apply_product_returns_action(
                action, returns.get(action, []), (batch or {}).get(action, []), products,
            ))
        if errors:
            raise ValueError("Échec du lot WooCommerce : " + "; ".join(errors))

    def _apply_product_returns_action(
        self: Any, action: str, items: list[dict[str, Any]],
        requested: list[dict[str, Any]], products: Sequence[GeneralObjects],
    ) -> list[str]:
        errors: list[str] = []
        if not isinstance(items, list):
            items = [{"error": f"Réponse WooCommerce invalide pour {action}."}]
        for index in range(max(len(items), len(requested))):
            payload = requested[index] if index < len(requested) else {}
            item = items[index] if index < len(items) else {}
            try:
                self._apply_product_return(action, item, payload, products)
            except (RequestException, ValueError, TypeError) as exc:
                errors.append(str(exc))
                self._log_product_return_error(action, payload, products, exc)
        return errors

    def _log_product_return_error(
        self: Any, action: str, payload: dict[str, Any],
        products: Sequence[GeneralObjects], exc: Exception,
    ) -> None:
        local = self._local_product_for_payload(action, payload, products)
        self._log_sync(
            entity_type="object", entity_id=local.id if local else None,
            wpwc_id=local.wpwc_id if local else payload.get("id"),
            operation=action, sync_status="error", error_message=str(exc),
        )

    def _apply_product_return(
        self: Any, action: str, item: dict[str, Any], payload: dict[str, Any],
        products: Sequence[GeneralObjects],
    ) -> None:
        if not isinstance(item, dict):
            raise ValueError("Réponse produit WooCommerce invalide.")
        expected = self._local_product_for_payload(action, payload, products)
        item = self._resolve_product_error(action, item, payload, expected)
        wc_id = self._product_wc_id(item)
        local = self._local_product_for_payload(action, {"id": wc_id, "sku": item.get("sku")}, products)
        if local is None and action == "delete":
            local = self.session.execute(
                select(GeneralObjects).where(GeneralObjects.wpwc_id == wc_id)
            ).scalar_one_or_none()
        if local is None and action != "delete":
            raise ValueError(f"Produit WooCommerce {wc_id} sans correspondance locale.")
        if expected is not None and local is not expected:
            raise ValueError(f"Produit WooCommerce {wc_id} différent du produit demandé.")
        if local is not None:
            local.wpwc_id = None if action == "delete" else wc_id
        self._log_sync(
            entity_type="object", entity_id=local.id if local else None,
            wpwc_id=wc_id, operation=action, sync_status="success",
        )

    def _resolve_product_error(
        self: Any, action: str, item: dict[str, Any], payload: dict[str, Any],
        product: GeneralObjects | None,
    ) -> dict[str, Any]:
        error = item.get("error")
        if not error:
            return item
        if action != "create" or product is None or not self._is_sku_conflict(error):
            raise ValueError(str(error))
        return self._reconcile_product_sku(product, payload)

    @staticmethod
    def _local_product_for_payload(
        action: str, payload: dict[str, Any], products: Sequence[GeneralObjects],
    ) -> GeneralObjects | None:
        if action == "create":
            return next((product for product in products if str(product.id) == str(payload.get("sku"))), None)
        wc_id = payload.get("id")
        if wc_id is None:
            return None
        return next((product for product in products if product.wpwc_id == wc_id), None)

    @staticmethod
    def _product_wc_id(item: dict[str, Any]) -> int:
        if not isinstance(item, dict):
            raise ValueError("Réponse produit WooCommerce invalide.")
        value = item.get("id")
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise ValueError("Identifiant produit WooCommerce absent ou invalide.")
        wc_id = int(value)
        if wc_id <= 0:
            raise ValueError("Identifiant produit WooCommerce non positif.")
        return wc_id

    @staticmethod
    def _is_sku_conflict(error: Any) -> bool:
        if not isinstance(error, dict):
            return False
        code = error.get("code")
        if code in ("product_invalid_sku", "woocommerce_rest_product_invalid_sku"):
            return True
        message = str(error.get("message", "")).lower()
        return code == "woocommerce_rest_product_not_created" and (
            "sku" in message or "ugs" in message
        ) and any(word in message for word in ("already", "déjà", "lookup", "consultation"))

    def _find_product_by_sku(self: Any, sku: str) -> dict[str, Any] | None:
        response = self.api_read.get("products", params={"sku": sku})
        response.raise_for_status()
        items = response.json()
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise ValueError("Réponse WooCommerce invalide pour la recherche par UGS.")
        matches = [item for item in items if str(item.get("sku")) == sku]
        if len(matches) > 1:
            raise ValueError(f"UGS WooCommerce ambigu : {sku}.")
        if not matches:
            return None
        self._product_wc_id(matches[0])
        return matches[0]

    def _reconcile_product_sku(
        self: Any, product: GeneralObjects, payload: dict[str, Any],
    ) -> dict[str, Any]:
        remote = self._find_product_by_sku(str(product.id))
        if remote is None:
            raise ValueError(f"Conflit d'UGS {product.id} sans produit WooCommerce retrouvable.")
        product.wpwc_id = self._product_wc_id(remote)
        self._log_sync(
            entity_type="object", entity_id=product.id, wpwc_id=product.wpwc_id,
            operation="reconcile", sync_status="success",
        )
        response = self.api_write.put(f"products/{product.wpwc_id}", data=payload)
        response.raise_for_status()
        item = response.json()
        if not isinstance(item, dict) or item.get("error") or item.get("code"):
            raise ValueError(f"Échec de mise à jour après réconciliation de l'UGS {product.id}.")
        if self._product_wc_id(item) != product.wpwc_id or str(item.get("sku")) != str(product.id):
            raise ValueError(f"Réponse incohérente après réconciliation de l'UGS {product.id}.")
        return item

    def _apply_tag_returns(
        self: Any,
        returns: dict[str, list[dict[str, Any]]],
        tags: Sequence[Tags],
    ) -> None:
        """Applique les retours batch tags."""
        self._apply_returns_generic(
            returns, tags, "tag",
            {
                "create": lambda items, item: next(
                    (tag for tag in items if tag.name == item.get("name")),
                    None,
                ),
                "update": lambda items, item: next(
                    (tag for tag in items if tag.wpwc_id == int(item["id"])),
                    None,
                ),
            },
            {
                "create": lambda tag, wc_id, _: setattr(
                    tag, "wpwc_id", wc_id
                ),
                "delete": lambda tag, _, __: setattr(
                    tag, "wpwc_id", None,
                ),
            },
            lambda wc_id: self.session.execute(
                select(Tags).where(Tags.wpwc_id == wc_id)
            ).scalar_one_or_none(),
        )

    def _apply_picture_returns(
        self: Any,
        returns: dict[str, list[dict[str, Any]]],
        pictures: Sequence[MediaFiles],
    ) -> None:
        """Applique les retours batch médias."""
        self._apply_returns_generic(
            returns, pictures, "media",
            {
                "create": lambda items, item: next(
                    (picture for picture in items if picture.file_link == item.get("name")),
                    None,
                ),
                "update": lambda items, item: next(
                    (picture for picture in items if picture.wpwc_id == int(item["id"])),
                    None,
                ),
            },
            {
                "create": lambda picture, wc_id, _: setattr(
                    picture, "wpwc_id", wc_id
                ),
                "delete": lambda picture, _, __: setattr(
                    picture, "wpwc_id", None
                ),
            },
            lambda wc_id: self.session.execute(
                select(MediaFiles).where(MediaFiles.wpwc_id == wc_id)
            ).scalar_one_or_none(),
        )

    def _apply_vat_returns(
        self: Any,
        returns: dict[str, list[dict[str, Any]]],
        vat_rates: Sequence[VatRate],
    ) -> None:
        """Applique les retours batch taux de TVA."""
        def update_created(rate: VatRate, wc_id: int, item: dict[str, Any]) -> None:
            rate.wpwc_id = wc_id
            rate.wpwc_slug = item.get("class") or ""

        def update_existing(rate: VatRate, _: int, item: dict[str, Any]) -> None:
            if item.get("class") is not None:
                rate.wpwc_slug = item["class"] or ""

        self._apply_returns_generic(
            returns, vat_rates, "vat_rate",
            {
                "create": lambda items, item: next(
                    (rate for rate in items if float(rate.rate) == float(item.get("rate", -1))),
                    None,
                ),
                "update": lambda items, item: next(
                    (rate for rate in items if rate.wpwc_id == int(item["id"])),
                    None,
                ),
            },
            {
                "create": update_created,
                "update": update_existing,
                "delete": lambda rate, _, __: setattr(rate, "wpwc_id", None),
            },
            lambda wc_id: self.session.execute(
                select(VatRate).where(VatRate.wpwc_id == wc_id)
            ).scalar_one_or_none(),
        )
