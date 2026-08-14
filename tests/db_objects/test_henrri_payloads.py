"""Tests des contrats de payload et d’orchestration Henri."""

from unittest.mock import MagicMock, patch

from flask import Flask
import pytest
from henrri_connect.models import (
    Customer,
    Document,
    DocumentLine,
    Item as HenriItem,
)
from app_front.blueprints.customer.routes import customer_wc_push
from app_front.blueprints.order import utils as order_utils
from app_front.blueprints.order.routes import order_wc_push
from app_front.blueprints.order.utils_henrri import (
    HenrriSyncError,
    check_customer,
    check_product,
    create_invoice,
)
from db_models.services.henrri.base import HenrriService
from db_models.objects import (
    Customers,
    GeneralObjects,
    Invoice,
    InvoiceLine,
    Order,
    OrderLine,
)

def test_customer_to_dict_henrri_contract_for_professional(
        professional_customer: Customers
    ) -> None:
    """Le payload Henri d'un client pro doit respecter le contrat SDK et les champs métier."""
    customer = professional_customer

    payload = customer.to_dict_henrri()

    assert payload["type"] == "professional"
    assert payload["company_identifier_type"] == "Siret"
    assert payload["siret"] == "12345678901234"
    assert payload["trade_name"] == "ACME SAS"
    assert payload["vat_number"] == "FR01123456789"
    assert payload["contacts"][0]["email"] == "contact@acme.fr"
    assert payload["address"]["city"] == "Paris"
    Customer(**payload)


def test_customer_to_dict_henrri_contract_for_individual(
        individual_customer: Customers
    ) -> None:
    """
    Le payload Henri d'un client particulier doit conserver la bonne structure et les
    champs obligatoires.
    """
    customer = individual_customer

    payload = customer.to_dict_henrri()
    payload_dict = dict(payload)
    customer_name = str(payload_dict["name"]) if "name" in payload_dict else ""
    customer_contacts = payload_dict["contacts"] if "contacts" in payload_dict else []
    customer_address = payload_dict["address"] if "address" in payload_dict else {}

    assert payload_dict["type"] == "individual"
    assert customer_name == "Alice Martin"
    assert customer_contacts[0]["first_name"] == "Alice"
    assert customer_contacts[0]["last_name"] == "Martin"
    assert customer_address["post_code"] == "69000"
    Customer(**payload_dict)


def test_invoice_to_dict_henrri_contract(
    henri_invoice_context: tuple[Customers, Order, Invoice, InvoiceLine, OrderLine],
) -> None:
    """Le payload Henri d'une facture doit respecter le schéma Document attendu par le SDK."""
    _, _, invoice, _, _ = henri_invoice_context

    payload = invoice.to_dict_henrri()

    assert payload["document_type_id"] == 1
    assert payload["customer_id"] == 1
    assert payload["customer"]["type"] == "individual"
    assert payload["customer_address"]["city"] == "Paris"
    assert payload["price_before_tax"] == 150.0
    assert payload["tax_amount"] == 30.0
    assert payload["price_after_tax"] == 180.0
    Document(**payload)


def test_henri_product_contract(henri_book_product: GeneralObjects) -> None:    # pylint: disable=W0621
    """Le payload produit Henri doit respecter le contrat Item du SDK."""
    obj = henri_book_product

    payload = obj.to_dict_henrri()

    assert payload["reference"] == "9781234567890"
    assert payload["description"] == "Description produit Henri"
    assert payload["vat_percent"] == 20.0
    assert payload["selling_price_without_tax"] == 19.99
    assert payload["selling_price_with_tax"] == 23.988
    HenriItem(**payload)


def test_henri_invoice_line_contract_omits_totals_when_tax_is_excluded(
    henri_sync_context: dict[str, object],
) -> None:
    """Une ligne de facture Henrri avec is_tax_included=false ne doit pas envoyer de totaux."""
    line = henri_sync_context["line"]

    payload = line.to_dict_henrri() # type: ignore

    assert payload["is_tax_included"] is False
    assert "total_without_tax" not in payload
    assert "total_with_tax" not in payload


def test_henri_service_configures_http_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le client HTTP Henrri doit exposer un read timeout de secours pour les PDF volumineux."""
    monkeypatch.setenv("HENRRI_API_KEY", "test-key")
    monkeypatch.setenv("HENRRI_API_SECRET", "test-secret")

    service = HenrriService()

    assert service.client._http.timeout.read == 60.0    # pylint: disable=W0212


def test_henri_invoice_orchestrates_customer_product_and_document(
        henri_sync_context: dict[str, object]    # pylint: disable=W0621
    ) -> None:
    """Le flux Henri doit créer le client, le produit et la facture puis finaliser le document."""
    customer = henri_sync_context["customer"]
    product = henri_sync_context["product"]
    invoice = henri_sync_context["invoice"]
    line = henri_sync_context["line"]

    mock_hcs = MagicMock()
    mock_hcs.create_customer.return_value = 5001
    mock_hps = MagicMock()
    mock_hps.create_product.return_value = 8001
    mock_hds = MagicMock()
    remote_customer_payload = customer.to_dict_henrri() # type: ignore
    remote_customer_payload["contacts"][0]["role"] = "administrateur"
    mock_hds.create_document.return_value = Document(**{
        "id": 9001,
        "identity": "INV-SYNC",
        "document_type_id": 1,
        "finalized": False,
        "title": "Facture de la commande du 2026-08-14",
        "subtitle": "Facture Editions Sauvetage du 2026-08-14",
        "price_before_tax": 42.0,
        "tax_amount": 8.4,
        "price_after_tax": 50.4,
        "due_label": "2026-09-12",
        "date": "2026-08-14",
        "validated": True,
        "validation_date": "2026-08-14",
        "customer_id": 1,
        "customer": Customer(**remote_customer_payload),
        "user_can_validate": True,
    })
    mock_hds.add_line.return_value = DocumentLine(**{
        "id": 1001,
        "document_id": 9001,
        "reference": "ART-SYNC",
        "description": "Livre sync",
        "selling_price_without_tax": 42.0,
        "purchasing_price_without_tax": 0.0,
        "vat_percent": 20.0,
        "quantity": 1.0,
        "is_tax_included": False,
        "total_without_tax": 42.0,
        "total_with_tax": 50.4,
        "are_elements_of_group_shown": False,
        "is_a_group": False,
        "does_group_own_different_vat": False,
        "is_member_of_a_group": False,
        "is_adjustment_of_group": False,
        "type_id": 3,
    })
    mock_hds.finalize_document.return_value = Document(**{
        "id": 9001,
        "identity": "INV-SYNC",
        "document_type_id": 1,
        "finalized": True,
        "title": "Facture de la commande du 2026-08-14",
        "price_before_tax": 42.0,
        "tax_amount": 8.4,
        "price_after_tax": 50.4,
        "due_label": "2026-09-12",
        "date": "2026-08-14",
        "validated": True,
        "customer_id": 1,
        "user_can_validate": True,
    })

    with patch(
            "app_front.blueprints.order.utils_henrri.check_customer",
            return_value=False,
        ), \
         patch(
            "app_front.blueprints.order.utils_henrri.check_product",
            return_value=False,
        ), \
         patch(
            "app_front.blueprints.order.utils_henrri.HenrriCustomersService",
            return_value=mock_hcs
        ), \
         patch(
            "app_front.blueprints.order.utils_henrri.HenrriProductsService",
            return_value=mock_hps
        ), \
         patch(
            "app_front.blueprints.order.utils_henrri.HenrriDocumentsService",
            return_value=mock_hds
        ):
        document, synced_invoice = create_invoice(invoice)  # type: ignore

    assert synced_invoice.customer.henrri_id == 5001
    assert product.henrri_id == 8001    # type: ignore
    assert document.id == 9001
    assert line.henrri_id == 1001   # type: ignore
    assert mock_hcs.create_customer.call_count == 1
    assert mock_hps.create_product.call_count == 1
    assert mock_hds.add_line.call_count == 1
    mock_hds.finalize_document.assert_called_once_with(9001)


def test_create_invoice_does_not_send_lines_when_creating_henrri_document(
    henri_sync_context: dict[str, object],
) -> None:
    """
    La création du document Henrri doit être faite sans lignes, puis les lignes
    sont ajoutées séparément.
    """
    invoice = henri_sync_context["invoice"]
    product = henri_sync_context["product"]
    product.henrri_id = None    # type: ignore

    mock_hcs = MagicMock()
    mock_hps = MagicMock()
    mock_hds = MagicMock()
    mock_hds.create_document.return_value = Document(**{
        "id": 901,
        "identity": "INV-CREATE-NO-LINES",
        "document_type_id": 1,
        "finalized": False,
        "title": "Facture de la commande du 2026-08-14",
        "price_before_tax": 42.0,
        "tax_amount": 8.4,
        "price_after_tax": 50.4,
        "due_label": "2026-09-12",
        "date": "2026-08-14",
        "validated": True,
        "customer_id": 1,
        "user_can_validate": True,
    })
    mock_hds.add_line.return_value = DocumentLine(**{
        "id": 1009,
        "document_id": 901,
        "reference": "ART-SYNC",
        "description": "Livre sync",
        "selling_price_without_tax": 42.0,
        "purchasing_price_without_tax": 0.0,
        "vat_percent": 20.0,
        "quantity": 1.0,
        "is_tax_included": False,
        "total_without_tax": 42.0,
        "total_with_tax": 50.4,
        "are_elements_of_group_shown": False,
        "is_a_group": False,
        "does_group_own_different_vat": False,
        "is_member_of_a_group": False,
        "is_adjustment_of_group": False,
        "type_id": 3,
    })
    mock_hds.finalize_document.return_value = Document(**{
        "id": 901,
        "identity": "INV-CREATE-NO-LINES",
        "document_type_id": 1,
        "finalized": True,
        "title": "Facture de la commande du 2026-08-14",
        "price_before_tax": 42.0,
        "tax_amount": 8.4,
        "price_after_tax": 50.4,
        "due_label": "2026-09-12",
        "date": "2026-08-14",
        "validated": True,
        "customer_id": 1,
        "user_can_validate": True,
    })
    with patch(
            "app_front.blueprints.order.utils_henrri.check_customer",
            return_value=False,
        ), \
         patch(
            "app_front.blueprints.order.utils_henrri.check_product",
            return_value=False,
        ), \
         patch(
            "app_front.blueprints.order.utils_henrri.HenrriCustomersService",
            return_value=mock_hcs,
        ), \
         patch(
            "app_front.blueprints.order.utils_henrri.HenrriProductsService",
            return_value=mock_hps,
            ), \
         patch(
            "app_front.blueprints.order.utils_henrri.HenrriDocumentsService",
            return_value=mock_hds,
        ):
        create_invoice(invoice) # type: ignore

    created_document = mock_hds.create_document.call_args.args[0]
    assert getattr(created_document, "lines", None) in (None, [], [])
    assert mock_hds.add_line.call_count == 1


def test_retry_henrri_invoice_is_idempotent_when_remote_document_is_finalized() -> None:
    """Une facture déjà finalisée côté Henrri ne doit pas être recréée localement."""
    invoice = Invoice(
        id=101,
        order_id=12,
        customer_id=1,
        reference="INV-RETRY",
        total_amount=42.0,
        vat_amount=8.4,
        create_source="test",
        henrri_id="9002",
    )

    session = MagicMock()
    with patch(
            "app_front.blueprints.order.utils.InvoiceRepository"
        ) as mock_repo_cls, \
         patch(
            "app_front.blueprints.order.utils.db_conf.get_main_session",
            return_value=session
        ), \
         patch(
            "app_front.blueprints.order.utils.find_henrri_invoice"
        ) as mock_find:
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.get_by_id.return_value = invoice
        mock_find.return_value = MagicMock(id=9002, finalized=True)

        result = order_utils.retry_henrri_invoice(101)

    assert result is invoice
    assert invoice.henrri_id == "9002"
    mock_repo.add_sync_log.assert_called_once()
    assert mock_repo.add_sync_log.call_args.kwargs["sync_status"] == "success"
    mock_find.assert_called_once_with("9002")


def test_sync_invoice_with_henrri_logs_failed_status_when_sync_fails() -> None:
    """Un échec côté Henrri doit produire un log failed avec les détails de l'erreur."""
    invoice = Invoice(
        id=202,
        order_id=12,
        customer_id=1,
        reference="INV-FAIL",
        total_amount=42.0,
        vat_amount=8.4,
        create_source="test",
    )
    invoice_repo = MagicMock()

    with patch(
        "app_front.blueprints.order.utils.create_henrri_invoice",
        side_effect=HenrriSyncError(
            "Échec réseau Henrri",
            status_code=422,
            details={"error": "invalid payload"},
            step="document",
        ),
    ), \
         patch("app_front.blueprints.order.utils.logger"):
        with pytest.raises(HenrriSyncError):
            order_utils._sync_invoice_with_henrri(invoice, invoice_repo)    #pylint: disable=W0212

    invoice_repo.add_sync_log.assert_called_once()
    assert invoice_repo.add_sync_log.call_args.kwargs["sync_status"] == "failed"
    assert "Échec réseau Henrri" in str(invoice_repo.add_sync_log.call_args.kwargs["error_message"])


def test_customer_wc_push_returns_http_error_when_sync_fails() -> None:
    """Un push WooCommerce en échec doit renvoyer un statut HTTP d'erreur et non un 204."""
    app = Flask(__name__)
    app.secret_key = "test-secret"
    with app.test_request_context("/customer/42/wc-push", method="POST") as request_ctx:
        request_ctx.session["permissions"] = "3"    # type: ignore
        request_ctx.session["username"] = "alice"   # type: ignore
        with patch(
            "app_front.blueprints.customer.routes.push_customer_wc",
            return_value=(False, "Erreur WooCommerce"),
        ), patch(
            "app_front.blueprints.customer.routes.log_client_event"
        ) as mock_log, patch(
            "app_front.blueprints.customer.routes.url_for",
            return_value="/customer/42",
        ):
            response = customer_wc_push(42)

    assert response.status_code == 500
    assert response.get_data(as_text=True) == "Erreur WooCommerce"
    assert mock_log.call_args.kwargs["status_code"] == 500


def test_order_wc_push_returns_http_error_when_sync_fails() -> None:
    """Un push commande WooCommerce en échec doit remonter un statut HTTP explicite."""
    app = Flask(__name__)
    app.secret_key = "test-secret"
    with app.test_request_context("/order/view/42/wc-push", method="POST") as request_ctx:
        request_ctx.session["permissions"] = "3"    # type: ignore
        request_ctx.session["username"] = "alice"   # type: ignore
        with patch(
            "app_front.blueprints.order.routes.push_order_wc",
            return_value=(False, "Erreur WooCommerce"),
        ), patch(
            "app_front.blueprints.order.routes.log_metier_event"
        ) as mock_log, patch(
            "app_front.blueprints.order.routes.url_for",
            return_value="/order/view/42",
        ):
            response = order_wc_push(42)

    assert response.status_code == 500
    assert response.get_data(as_text=True) == "Erreur WooCommerce"
    assert mock_log.call_args.kwargs["status_code"] == 500


def test_invoice_order_rejects_already_fully_invoiced_order() -> None:
    """Une commande déjà entièrement facturée ne doit pas être refacturée dans le flux standard."""
    order = Order(
        id=77,
        reference="CMD-ALREADY-INVOICED",
        customer_id=1,
        status="invoiced",
        create_source="test",
    )

    session = MagicMock()
    with patch(
        "app_front.blueprints.order.utils.db_conf.get_main_session",
        return_value=session,
    ), patch(
        "app_front.blueprints.order.utils.OrdersRepository"
    ) as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = order
        mock_repo_cls.return_value = mock_repo

        with pytest.raises(ValueError, match="déjà facturée|facture d'avoir"):
            order_utils.invoice_order(77, [{"order_line_id": 12, "quantity": 1}])


def test_check_product_returns_true_when_item_exists_in_henrri() -> None:
    """Une vérification d’existence doit retourner vrai quand le produit existe chez Henrri."""
    mock_service = MagicMock()
    mock_service.client.items.get.return_value = MagicMock(id=123)

    with patch(
        "app_front.blueprints.order.utils_henrri.HenrriProductsService",
        return_value=mock_service,
    ):
        assert check_product("123") is True


def test_check_customer_returns_false_when_customer_lookup_fails() -> None:
    """La vérification de client doit retourner false sur une erreur d’accès ou d’absence."""
    mock_service = MagicMock()
    mock_service.client.customers.get.side_effect = ValueError("missing")

    with patch(
        "app_front.blueprints.order.utils_henrri.HenrriCustomersService",
        return_value=mock_service,
    ):
        assert check_customer("999") is False


def test_create_invoice_reuses_existing_remote_customer_and_product(
    henri_sync_context: dict[str, object],
) -> None:
    """Le flux doit réutiliser le client et le produit déjà connus par la fixture Henri."""
    customer = henri_sync_context["customer"]
    customer.id = 81    # type: ignore
    product = henri_sync_context["product"]
    product.id = 81 # type: ignore
    invoice = henri_sync_context["invoice"]

    mock_hcs = MagicMock()
    mock_hps = MagicMock()
    mock_hds = MagicMock()
    mock_hds.create_document.return_value = Document(**{
        "id": 9001,
        "identity": "INV-SYNC",
        "document_type_id": 1,
        "finalized": False,
        "title": "Facture de la commande du 2026-08-14",
        "subtitle": "Facture Editions Sauvetage du 2026-08-14",
        "price_before_tax": 42.0,
        "tax_amount": 8.4,
        "price_after_tax": 50.4,
        "due_label": "2026-09-12",
        "date": "2026-08-14",
        "validated": True,
        "validation_date": "2026-08-14",
        "customer_id": 1,
        "customer": Customer(**customer.to_dict_henrri()),  # type: ignore
        "user_can_validate": True,
    })
    mock_hds.add_line.return_value = DocumentLine(**{
        "id": 1001,
        "document_id": 9001,
        "reference": "ART-SYNC",
        "description": "Livre sync",
        "selling_price_without_tax": 42.0,
        "purchasing_price_without_tax": 0.0,
        "vat_percent": 20.0,
        "quantity": 1.0,
        "is_tax_included": False,
        "total_without_tax": 42.0,
        "total_with_tax": 50.4,
        "are_elements_of_group_shown": False,
        "is_a_group": False,
        "does_group_own_different_vat": False,
        "is_member_of_a_group": False,
        "is_adjustment_of_group": False,
        "type_id": 3,
    })
    mock_hds.finalize_document.return_value = Document(**{
        "id": 9001,
        "identity": "INV-SYNC",
        "document_type_id": 1,
        "finalized": True,
        "title": "Facture de la commande du 2026-08-14",
        "price_before_tax": 42.0,
        "tax_amount": 8.4,
        "price_after_tax": 50.4,
        "due_label": "2026-09-12",
        "date": "2026-08-14",
        "validated": True,
        "customer_id": 1,
        "user_can_validate": True,
    })

    with patch(
            "app_front.blueprints.order.utils_henrri.check_customer",
            return_value=True,
        ), \
         patch(
            "app_front.blueprints.order.utils_henrri.check_product",
            return_value=True,
        ), \
         patch(
            "app_front.blueprints.order.utils_henrri.HenrriCustomersService",
            return_value=mock_hcs,
        ), \
         patch(
            "app_front.blueprints.order.utils_henrri.HenrriProductsService",
            return_value=mock_hps,
        ), \
         patch(
            "app_front.blueprints.order.utils_henrri.HenrriDocumentsService",
            return_value=mock_hds,
        ):
        document, synced_invoice = create_invoice(invoice)  # type: ignore

    assert document.id == 9001
    assert synced_invoice.customer.henrri_id == "81"
    assert product.id == 81 # type: ignore
    assert product.henrri_id == "81"    # type: ignore
    mock_hcs.create_customer.assert_not_called()
    mock_hps.create_product.assert_not_called()
    mock_hds.add_line.assert_called_once()
