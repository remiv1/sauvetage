"""Tests de la synchronisation conjointe vers WooCommerce et Henrri."""

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from app_front.blueprints.stock import utils as stock_utils
from app_front.blueprints.stock import routes_htmx_search as stock_routes
from db_models.objects import Customers
from db_models.services.sync import partners


@pytest.mark.parametrize("wpwc_id", [5001, None])
def test_product_partners_push_uses_reader_writer_and_rejects_wc_failure(
    monkeypatch: pytest.MonkeyPatch, wpwc_id: int | None,
) -> None:
    """L'envoi utilise Reader/Writer sans synchroniser le produit sur Henrri."""
    session = MagicMock()
    product = MagicMock(id=859, wpwc_id=None)
    object_repo = MagicMock()
    object_repo.return_value.get_by_ref.return_value = product
    wc_service = MagicMock()
    wc_service.return_value.update_product.return_value = wpwc_id
    henrri_sync = MagicMock()
    monkeypatch.setattr(stock_utils.db_conf, "get_main_session", lambda: session)
    monkeypatch.setattr(stock_utils, "ObjectsRepository", object_repo)
    monkeypatch.setattr(stock_utils, "WCProductsService", wc_service)
    monkeypatch.setattr(stock_utils, "sync_product_to_henrri", henrri_sync, raising=False)

    if wpwc_id is None:
        with pytest.raises(ValueError, match="aucun identifiant confirmé"):
            stock_utils.push_product_partners(859)
    else:
        stock_utils.push_product_partners(859)

    wc_service.assert_called_once_with(session, separated_keys=True)
    wc_service.return_value.update_product.assert_called_once_with(859)
    henrri_sync.assert_not_called()
    session.commit.assert_called_once()


@pytest.mark.parametrize("failed", [False, True])
def test_product_partners_push_notification_reflects_sync_result(
    monkeypatch: pytest.MonkeyPatch, failed: bool,
) -> None:
    """La notification ne présente pas un échec WooCommerce comme un succès."""
    sync = MagicMock()
    if failed:
        sync.side_effect = ValueError("Échec WooCommerce : aucun identifiant confirmé.")
    monkeypatch.setattr(stock_routes, "push_product_partners", sync)

    with Flask(__name__).test_request_context():
        response = stock_routes.product_partners_push(859)

    body = response.get_data(as_text=True)
    if failed:
        assert "alert-danger" in body
        assert "aucun identifiant confirmé" in body
        assert "Produit synchronisé avec succès" not in body
        assert "HX-Trigger" not in response.headers
    else:
        assert "alert-success" in body
        assert "Produit synchronisé avec succès" in body
        assert response.headers["HX-Trigger"] == "refreshTable"


class HenrriValidationErrorWithBody(Exception):
    """Exception Henrri simulée portant le détail de validation de l'API."""

    def __init__(self, message: str, body: dict[str, object]) -> None:
        super().__init__(message)
        self.body = body


def _customer(**overrides) -> Customers:
    """Construit un client minimal pour les tests de synchronisation."""
    defaults = {"customer_type": "part", "is_active": True}
    defaults.update(overrides)
    customer = Customers(**defaults)
    customer.id = overrides.pop("local_id", 7)
    return customer


def test_sync_customer_pushes_to_both_partners() -> None:
    """Un client doit être poussé vers WooCommerce et Henrri au cours de la même opération."""
    customer = _customer(wpwc_id=None, henrri_id=None)
    wc_service = MagicMock()
    wc_service.create_wpwc_customer_if_not_exists.return_value = MagicMock(wpwc_id="1234")

    with patch.object(partners, "SyncLogRepository") as mock_repo_cls, patch.object(
        partners, "sync_customer_to_henrri", return_value=MagicMock(id=5001)
    ) as mock_henrri:
        results = partners.sync_customer(MagicMock(), customer, wc_service=wc_service)

    assert [r.target for r in results] == [partners.WPWC, partners.HENRRI]
    assert all(r.status == "success" for r in results)
    assert results[0].external_id == "1234"
    assert results[1].external_id == "5001"
    wc_service.create_wpwc_customer_if_not_exists.assert_called_once_with(customer)
    mock_henrri.assert_called_once_with(customer)
    assert mock_repo_cls.return_value.log_customer.call_count == 2


def test_sync_customer_isolates_partner_failures() -> None:
    """Un échec WooCommerce ne doit pas empêcher la synchronisation Henrri."""
    customer = _customer(wpwc_id=None, henrri_id="81")
    wc_service = MagicMock()
    wc_service.create_wpwc_customer_if_not_exists.side_effect = RuntimeError("API HS")

    with patch.object(partners, "SyncLogRepository") as mock_repo_cls, patch.object(
        partners, "sync_customer_to_henrri", return_value=MagicMock(id=81)
    ):
        results = partners.sync_customer(MagicMock(), customer, wc_service=wc_service)

    wpwc_result = results[0]    # pylint: disable=W0632
    henrri_result = results[1]
    assert wpwc_result.status == "error"
    assert "API HS" in str(wpwc_result.error)
    assert henrri_result.status == "success"

    statuses = [
        call.kwargs["sync_status"]
        for call in mock_repo_cls.return_value.log_customer.call_args_list
    ]
    assert statuses == ["failed", "success"]


def test_sync_customer_logs_update_operation_for_known_partners() -> None:
    """Un client déjà connu des deux partenaires doit être journalisé en mise à jour."""
    customer = _customer(wpwc_id="1234", henrri_id="81")
    wc_service = MagicMock()
    wc_service.create_wpwc_customer_if_not_exists.return_value = MagicMock(wpwc_id="1234")

    with patch.object(partners, "SyncLogRepository") as mock_repo_cls, patch.object(
        partners, "sync_customer_to_henrri", return_value=MagicMock(id=81)
    ):
        partners.sync_customer(MagicMock(), customer, wc_service=wc_service)

    operations = [
        call.kwargs["operation"]
        for call in mock_repo_cls.return_value.log_customer.call_args_list
    ]
    assert operations == ["update", "update"]


def test_sync_customer_logs_henrri_validation_details() -> None:
    """Le journal Henrri doit conserver le détail retourné par l'API."""
    customer = _customer(wpwc_id="1234", henrri_id=None)
    wc_service = MagicMock()
    wc_service.create_wpwc_customer_if_not_exists.return_value = MagicMock(wpwc_id="1234")
    validation_body = {"errors": {"contacts": ["Le contact est invalide."]}}

    with patch.object(partners, "SyncLogRepository") as mock_repo_cls, patch.object(
        partners,
        "sync_customer_to_henrri",
        side_effect=HenrriValidationErrorWithBody("HTTP 400", validation_body), # type: ignore
    ):
        results = partners.sync_customer(MagicMock(), customer, wc_service=wc_service)

    assert results[1].status == "error"
    error_message = mock_repo_cls.return_value.log_customer.call_args_list[1].kwargs[
        "error_message"
    ]
    assert "Détails de validation Henrri" in error_message
    assert "contacts" in error_message


def test_sync_all_products_exports_only_woocommerce() -> None:
    """Le catalogue doit partir vers WooCommerce sans aucune écriture Henrri."""
    session = MagicMock()
    wc_service = MagicMock()

    with patch.object(partners, "SyncLogRepository") as mock_repo_cls, patch.object(
        partners, "WCProductsService", return_value=wc_service
    ), patch.object(
        partners, "sync_product_to_henrri", create=True
    ) as mock_henrri:
        results = partners.sync_all_products(session)

    wc_service.export_all_products.assert_called_once()
    mock_henrri.assert_not_called()
    assert [(result.target, result.status) for result in results] == [(partners.WPWC, "success")]
    mock_repo_cls.assert_not_called()
    session.commit.assert_called_once()


def test_sync_all_products_reports_woocommerce_failure_without_henrri() -> None:
    """Un échec WooCommerce ne déclenche pas d'envoi Henrri de remplacement."""
    session = MagicMock()
    wc_service = MagicMock()
    wc_service.export_all_products.side_effect = RuntimeError("WooCommerce indisponible")

    with patch.object(partners, "SyncLogRepository"), patch.object(
        partners, "WCProductsService", return_value=wc_service
    ), patch.object(
        partners, "sync_product_to_henrri", create=True
    ) as mock_henrri:
        results = partners.sync_all_products(session)

    assert results[0].status == "error"
    assert len(results) == 1
    mock_henrri.assert_not_called()
