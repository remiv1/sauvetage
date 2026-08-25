"""Synchronisation des taux de TVA WooCommerce."""

import logging
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import or_, select

from db_models.objects.vat import VatRate
from db_models.services.utils import slugify

logger = logging.getLogger(__name__)


class VatRatesMixin:
    """Responsabilités de synchronisation des taux de TVA."""

    def _diff_vat_rates(
        self: Any,
        vat_rates: Sequence[VatRate],
        remote_rates: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Calcule le diff des taux de TVA locaux et WooCommerce."""
        data = {"create": [], "update": [], "delete": []}
        remote_ids = {int(rate["id"]) for rate in remote_rates}
        for rate in vat_rates:
            target_slug = rate.wpwc_slug or slugify(rate.label)
            remote = next((item for item in remote_rates if item.get("class") == target_slug), None)
            if remote is None and rate.wpwc_id:
                remote = next(
                    (item for item in remote_rates if int(item["id"]) == rate.wpwc_id),
                    None,
                )
            if remote:
                payload = {
                    "id": int(remote["id"]),
                    "rate": str(rate.rate),
                    "name": rate.label,
                    "class": target_slug,
                }
                rate.wpwc_id = payload["id"]
                if (
                    float(remote.get("rate", 0)) != float(rate.rate)
                    or remote.get("name") != rate.label
                    or remote.get("class") != target_slug
                ):
                    data["update"].append(payload)
                remote_ids.discard(payload["id"])
            else:
                data["create"].append(
                    {
                        "rate": str(rate.rate),
                        "name": rate.label,
                        "class": target_slug,
                    },
                )
        data["delete"] = [{"id": remote_id} for remote_id in remote_ids]
        return data

    def _ensure_wc_tax_classes(self: Any, vat_rates: Sequence[VatRate]) -> None:
        """Crée les classes de taxe WooCommerce manquantes."""
        try:
            classes = self.api_read.get("taxes/classes").json()
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Erreur de récupération des classes de taxe: %s", exc)
            return
        slugs = {item["slug"] for item in classes}
        for rate in vat_rates:
            expected_slug = slugify(rate.label)
            if expected_slug in slugs:
                rate.wpwc_slug = expected_slug
                continue
            try:
                response = self.api_write.post("taxes/classes", data={"name": rate.label})
                response.raise_for_status()
                rate.wpwc_slug = response.json().get("slug") or expected_slug
                slugs.add(rate.wpwc_slug)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Erreur de création de la classe de taxe %r: %s", rate.label, exc)
        self.session.flush()

    @staticmethod
    def _validate_current_vat_slugs(vat_rates: Sequence[VatRate]) -> None:
        """Vérifie l'unicité des slugs parmi les taux de TVA en vigueur."""
        slugs: dict[str, list[VatRate]] = {}
        for rate in vat_rates:
            slugs.setdefault(rate.wpwc_slug or slugify(rate.label), []).append(rate)
        duplicates = {slug: rates for slug, rates in slugs.items() if len(rates) > 1}
        if duplicates:
            details = ", ".join(
                f"{slug} ({', '.join(str(rate.id) for rate in rates)})"
                for slug, rates in duplicates.items()
            )
            raise ValueError(f"Slugs WooCommerce dupliqués pour les TVA en vigueur : {details}.")

    def export_vat_rates(self: Any, name: str | None = None) -> bool:
        """Exporte les taux de TVA actuellement en vigueur."""
        now = datetime.now(timezone.utc)
        stmt = select(VatRate).where(
            VatRate.date_start <= now,
            or_(
                VatRate.date_end == None,   # pylint: disable C0121
                VatRate.date_end > now,
            ),
        )
        if name:
            stmt = stmt.where(VatRate.label == name)
        rates = self.session.execute(stmt).scalars().all()
        self._validate_current_vat_slugs(rates)
        self._ensure_wc_tax_classes(rates)
        data = self._diff_vat_rates(rates, self.api_read.get("taxes").json())
        if not any(data.values()):
            self.session.commit()
            return False
        try:
            result = self.api_write.post("taxes/batch", data=data).json()
        except Exception as exc:  # pylint: disable=broad-except
            for rate in rates:
                self._log_sync(
                    entity_type="vat_rate",
                    entity_id=rate.id,
                    wpwc_id=rate.wpwc_id,
                    operation="batch",
                    sync_status="error",
                    error_message=str(exc),
                )
            self.session.commit()
            return False
        self._apply_vat_returns(result, rates)
        self.session.commit()
        return True

    def import_vat_slugs(self: Any) -> int:
        """Récupère les classes de taxe WooCommerce et met à jour les taux locaux.

        Returns:
            Nombre de taux locaux mis à jour.
        """
        remote_rates: list[dict[str, Any]] = self.api_read.get(
            "taxes", params={"per_page": 100}
        ).json()
        local_rates = self.session.execute(select(VatRate)).scalars().all()
        updated = 0

        for remote_rate in remote_rates:
            remote_id = remote_rate.get("id")
            remote_slug = remote_rate.get("class") or ""
            remote_value = float(remote_rate.get("rate", 0))
            local_rate = next(
                (
                    rate for rate in local_rates
                    if round(float(rate.rate), 3) == round(remote_value, 3)
                ),
                None,
            )
            if local_rate is None:
                local_rate = next(
                    (rate for rate in local_rates if rate.wpwc_id == remote_id),
                    None,
                )
            if local_rate is None:
                continue

            changed = False
            if local_rate.wpwc_id != remote_id:
                local_rate.wpwc_id = remote_id
                changed = True
            if local_rate.wpwc_slug != remote_slug:
                local_rate.wpwc_slug = remote_slug
                changed = True
            if changed:
                updated += 1
                logger.info(
                    "VatRate id=%d (rate=%.3f) : wpwc_id=%d, wpwc_slug=%r",
                    local_rate.id,
                    float(local_rate.rate),
                    remote_id,
                    remote_slug,
                )

        self.session.commit()
        logger.info("import_vat_slugs : %d taux mis à jour.", updated)
        return updated
