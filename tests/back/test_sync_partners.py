"""Tests de la synchronisation conjointe vers WooCommerce et Henrri."""

from unittest.mock import MagicMock, patch

from db_models.objects import Customers
from db_models.services.sync import partners


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
        side_effect=HenrriValidationErrorWithBody("HTTP 400", validation_body),
    ):
        results = partners.sync_customer(MagicMock(), customer, wc_service=wc_service)

    assert results[1].status == "error"
    error_message = mock_repo_cls.return_value.log_customer.call_args_list[1].kwargs[
        "error_message"
    ]
    assert "Détails de validation Henrri" in error_message
    assert "contacts" in error_message


def test_sync_all_products_exports_woocommerce_then_henrri() -> None:
    """Le catalogue doit partir en batch vers WooCommerce puis à l'unité vers Henrri."""
    session = MagicMock()
    product = MagicMock(id=81, henrri_id=None)
    wc_service = MagicMock()

    with patch.object(partners, "SyncLogRepository") as mock_repo_cls, patch.object(
        partners, "WCProductsService", return_value=wc_service
    ), patch.object(
        partners, "_get_active_products", return_value=[product]
    ), patch.object(
        partners, "sync_product_to_henrri", return_value=MagicMock(id=8001)
    ) as mock_henrri:
        results = partners.sync_all_products(session)

    wc_service.export_all_products.assert_called_once()
    mock_henrri.assert_called_once_with(product)
    assert [r.status for r in results] == ["success", "success"]
    assert mock_repo_cls.return_value.log_object.call_args.kwargs["external_id"] == "8001"
    session.commit.assert_called_once()


def test_sync_all_products_reports_woocommerce_failure_without_blocking_henrri() -> None:
    """Un export WooCommerce en échec ne doit pas interrompre l'envoi vers Henrri."""
    session = MagicMock()
    product = MagicMock(id=81, henrri_id=82)
    wc_service = MagicMock()
    wc_service.export_all_products.side_effect = RuntimeError("WooCommerce indisponible")

    with patch.object(partners, "SyncLogRepository"), patch.object(
        partners, "WCProductsService", return_value=wc_service
    ), patch.object(
        partners, "_get_active_products", return_value=[product]
    ), patch.object(
        partners, "sync_product_to_henrri", return_value=MagicMock(id=82)
    ) as mock_henrri:
        results = partners.sync_all_products(session)

    assert results[0].status == "error"
    assert results[1].status == "success"
    mock_henrri.assert_called_once_with(product)
