"""Tests backend de validité des TVA et de leur synchronisation WooCommerce."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from db_models.objects import VatRate
from db_models.services.vat import close_superseded_vat_rates
from db_models.services.woo_commerce.products import WCProductsService


def _vat_rate(
    rate_id: int,
    code: int,
    rate: float,
    label: str,
    slug: str,
) -> VatRate:
    return VatRate(
        id=rate_id,
        code=code,
        rate=rate,
        label=label,
        wpwc_slug=slug,
        date_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_new_vat_rate_closes_superseded_rate_at_its_effective_time(
    db_session_main: Session,
) -> None:
    """Un nouveau taux clôture l'ancien à sa date de début, borne exclusive."""
    effective_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
    previous_rate = VatRate(
        code=1,
        rate=5.5,
        label="TVA réduite",
        date_start=effective_at - timedelta(days=365),
    )
    new_rate = VatRate(
        code=1,
        rate=6.0,
        label="TVA réduite 2026",
        date_start=effective_at,
    )
    db_session_main.add_all([previous_rate, new_rate])
    db_session_main.flush()

    closed_rates = close_superseded_vat_rates(
        db_session_main, new_rate.code, effective_at, new_rate.id
    )

    assert closed_rates == [previous_rate]
    assert previous_rate.date_end == effective_at
    assert previous_rate.is_current(effective_at - timedelta(microseconds=1))
    assert not previous_rate.is_current(effective_at)
    assert new_rate.is_current(effective_at)


def test_vat_slug_duplicates_are_rejected_before_woocommerce_sync() -> None:
    """Deux taux actifs ne peuvent pas publier la même classe de taxe WooCommerce."""
    service = object.__new__(WCProductsService)
    service.session = MagicMock()
    service.api_read = MagicMock()
    service.api_write = MagicMock()
    duplicate_slug = "taux-reduit"
    rates = [
        _vat_rate(1, 1, 5.5, "TVA réduite", duplicate_slug),
        _vat_rate(2, 2, 10.0, "TVA intermédiaire", duplicate_slug),
    ]
    scalars = service.session.execute.return_value.scalars.return_value
    scalars.all.return_value = rates

    with pytest.raises(ValueError, match="Slugs WooCommerce dupliqués"):
        service.export_vat_rates()

    service.api_read.get.assert_not_called()
    service.api_write.post.assert_not_called()


def test_vat_sync_is_skipped_when_woocommerce_already_matches() -> None:
    """Le rapprochement nocturne ne lance aucun batch quand les TVA sont identiques."""
    local_rate = _vat_rate(1, 1, 5.5, "TVA réduite", "taux-reduit")
    service = object.__new__(WCProductsService)
    service.session = MagicMock()
    service.api_read = MagicMock()
    service.api_write = MagicMock()
    service._ensure_wc_tax_classes = MagicMock()    # pylint: disable=W0212
    scalars = service.session.execute.return_value.scalars.return_value
    scalars.all.return_value = [local_rate]
    service.api_read.get.return_value.json.return_value = [
        {"id": 42, "rate": "5.5", "name": "TVA réduite", "class": "taux-reduit"}
    ]

    synchronized = service.export_vat_rates()

    assert synchronized is False
    service.api_write.post.assert_not_called()
    service.session.commit.assert_called_once()


def test_vat_slug_change_triggers_woocommerce_resynchronization() -> None:
    """Un changement de slug actif produit un batch WooCommerce de remplacement."""
    local_rate = _vat_rate(1, 1, 5.5, "TVA réduite", "taux-reduit-2026")
    service = object.__new__(WCProductsService)
    service.session = MagicMock()
    service.api_read = MagicMock()
    service.api_write = MagicMock()
    service._ensure_wc_tax_classes = MagicMock()    # pylint: disable=W0212
    service._apply_vat_returns = MagicMock()    # pylint: disable=W0212
    scalars = service.session.execute.return_value.scalars.return_value
    scalars.all.return_value = [local_rate]
    service.api_read.get.return_value.json.return_value = [
        {"id": 42, "rate": "5.5", "name": "TVA réduite", "class": "taux-reduit"}
    ]
    service.api_write.post.return_value.json.return_value = {
        "create": [], "update": [], "delete": []
    }

    synchronized = service.export_vat_rates()

    assert synchronized is True
    service.api_write.post.assert_called_once_with(
        "taxes/batch",
        data={
            "create": [{"rate": "5.5", "name": "TVA réduite", "class": "taux-reduit-2026"}],
            "update": [],
            "delete": [{"id": 42}],
        },
    )
