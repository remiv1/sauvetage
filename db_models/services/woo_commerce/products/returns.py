"""Traitement des retours batch WooCommerce."""

from typing import Any, Callable, Optional, Sequence

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
    ) -> None:
        """Applique les retours batch produits."""
        self._apply_returns_generic(
            returns, products, "object",
            {
                "create": lambda items, item: next(
                    (product for product in items if str(product.id) == str(item.get("sku") or "")),
                    None,
                ),
                "update": lambda items, item: next(
                    (product for product in items if product.wpwc_id == int(item["id"])),
                    None,
                ),
            },
            {
                "create": lambda product, wc_id, _: setattr(
                    product, "wpwc_id", wc_id
                ),
                "delete": lambda product, _, __: setattr(
                    product, "wpwc_id", None
                ),
            },
            lambda wc_id: self.session.execute(
                select(GeneralObjects).where(GeneralObjects.wpwc_id == wc_id)
            ).scalar_one_or_none(),
        )

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
