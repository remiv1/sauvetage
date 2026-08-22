"""Tests sur les payloads WooCommerce de commandes."""

from decimal import Decimal
from unittest.mock import MagicMock

from db_models.objects import (
    CustomerMails,
    CustomerParts,
    Customers,
    GeneralObjects,
    ObjectPrices,
    ObjectVariations,
    Order,
    OrderLine,
    VatRate,
)
from db_models.services.woo_commerce.orders import WCOrdersService


def test_order_line_payload_uses_wc_tax_class_and_variation_id(woo_book_product) -> None:
    """La ligne de commande doit conserver la tax_class et l'ID de variation WooCommerce."""
    product = woo_book_product
    variation = ObjectVariations(
        id=7,
        name="Variante A",
        description="",
        price=15.00,
        wpwc_id=21,
    )
    line = OrderLine(
        id=10,
        order_id=1,
        general_object_id=99,
        quantity=2,
        status="draft",
        unit_price=15.0,
        discount=0,
        vat_rate=20.0,
        create_source="test",
        general_object=product,
        object_variation=variation,
    )

    payload = line.to_dict_for_woo_commerce()

    assert payload["product_id"] == 150
    assert payload["tax_class"] == "standard"
    assert payload["variation_id"] == 21
    assert payload["subtotal"] == "30.0"
    assert payload["total"] == "30.0"


def test_order_line_payload_raises_clear_error_when_product_not_synced_to_woo(
        woo_book_product
    ) -> None:
    """Une ligne de commande sans produit WooCommerce doit produire un message exploitable."""
    product = woo_book_product
    product.wpwc_id = None
    line = OrderLine(
        id=10,
        order_id=1,
        general_object_id=99,
        quantity=2,
        status="draft",
        unit_price=15.0,
        discount=0,
        vat_rate=20.0,
        create_source="test",
        general_object=product,
    )

    try:
        line.to_dict_for_woo_commerce()
    except ValueError as exc:
        assert "non synchronisé" in str(exc).lower() or "wpwc_id" in str(exc).lower()
    else:
        raise AssertionError(
            "Une ValueError était attendue lorsque le produit n'est pas synchronisé."
        )


def test_order_payload_uses_wc_customer_and_line_contract(wc_customer_pro) -> None:
    """
    La commande doit produire le payload WooCommerce attendu avec l'email, l'adresse et
    les lignes.
    """
    customer = wc_customer_pro
    product = GeneralObjects(
        id=12,
        supplier_id=1,
        general_object_type="book",
        ean13="9784444444444",
        name="Produit commande",
        description="Commandable",
        wpwc_id=120,
    )
    product.prices = [
        ObjectPrices(
            price=Decimal("16.00"),
            vat_rate=VatRate(code=1, rate=20.0, label="TVA 20%", wpwc_slug="standard"),
        ),
    ]
    line = OrderLine(
        id=7,
        order_id=1,
        general_object_id=12,
        quantity=2,
        status="draft",
        unit_price=16.0,
        discount=0,
        vat_rate=20.0,
        create_source="test",
        general_object=product,
    )
    order = Order(
        id=1,
        reference="CMD-2401-00001",
        customer_id=999,
        invoice_address_id=1,
        delivery_address_id=1,
        status="draft",
        create_source="test",
        customer=customer,
        invoice_address=customer.addresses[0],
        delivery_address=customer.addresses[0],
        order_lines=[line],
    )

    payload = order.to_dict_for_woo_commerce()

    assert payload["customer_id"] == "42"
    assert payload["billing"]["email"] == "acme@example.com"
    assert payload["shipping"]["postcode"] == "75001"
    assert payload["line_items"][0]["product_id"] == 120
    assert payload["metadata"]["_billing_wooccm10"] == "Professionnel"


def test_wc_orders_service_uses_customer_woo_email_and_remote_customer_payload(
        wc_customer_part
    ) -> None:
    """
    Le service de commande doit utiliser l'email WooCommerce du client et le payload distant.
    """
    service = object.__new__(WCOrdersService)
    service.customer_repo = MagicMock()
    service.customer_service = MagicMock()
    service.api_write = MagicMock()
    service.order_repo = MagicMock()

    customer = wc_customer_part
    customer.id = 12
    customer.part.customer_id = 12
    customer.emails[0].customer_id = 12
    customer.addresses[0].customer_id = 12
    service.customer_repo.get_by_email.return_value = customer
    service.customer_service.get_by_mail.return_value = {
        "id": 42,
        "email": "alice@example.com",
    }

    order = Order(
        id=1,
        reference="CMD-2501-00001",
        customer_id=12,
        invoice_address_id=1,
        delivery_address_id=1,
        status="draft",
        create_source="web",
        customer=customer,
        invoice_address=customer.addresses[0],
        delivery_address=customer.addresses[0],
        order_lines=[],
    )
    created_order = Order(
        id=1,
        reference="CMD-2501-00001",
        customer_id=12,
        status="draft",
        create_source="web",
        customer=customer,
        wpwc_id=99,
    )
    service.order_repo.create_from_woo_commerce.return_value = created_order
    response = MagicMock(status_code=201)
    response.json.return_value = {"id": 99, "customer_id": 42, "line_items": []}
    service.api_write.post.return_value = response

    result = service.create_order(order)

    assert result.wpwc_id == 99
    service.customer_service.diff_customer.assert_called_once_with(
        local_customer=customer,
        wc_customer={"id": 42, "email": "alice@example.com"},
        from_local=True,
    )


def test_wc_orders_service_creates_missing_remote_customer_when_local_customer_exists() -> None:
    """
    Si le client local existe mais pas dans WooCommerce, le service doit créer le client distant.
    """
    service = object.__new__(WCOrdersService)
    service.customer_repo = MagicMock()
    service.customer_service = MagicMock()
    service.api_write = MagicMock()
    service.order_repo = MagicMock()

    customer = Customers(
        id=77,
        wpwc_id=None,
        customer_type="part",
    )
    customer.part = CustomerParts(
        customer_id=77,
        first_name="Bob",
        last_name="Martin",
    )
    customer.emails = [
        CustomerMails(
            customer_id=77,
            email_name="WooCommerce",
            email="bob@example.com",
            is_active=True,
        ),
    ]

    service.customer_repo.get_by_email.return_value = customer
    service.customer_service.get_by_mail.return_value = None
    response = MagicMock(status_code=201)
    response.json.return_value = {"id": 321, "customer_id": 77, "line_items": []}
    service.api_write.post.return_value = response

    order = Order(
        id=5,
        reference="CMD-2501-00002",
        customer_id=77,
        status="draft",
        create_source="web",
        customer=customer,
        order_lines=[],
    )

    service.create_order(order)

    service.customer_service.create_wpwc_customer_if_not_exists.assert_called_once_with(customer)


def test_wc_orders_service_preserves_existing_line_ids() -> None:
    """Le synchroniseur conserve la liaison WooCommerce déjà connue d'une ligne."""
    service = object.__new__(WCOrdersService)
    product = GeneralObjects(
        id=8,
        supplier_id=1,
        general_object_type="book",
        ean13="9786666666666",
        name="Produit ligne",
        description="desc",
        wpwc_id=101,
    )
    variation = ObjectVariations(
        id=31,
        name="Variation B",
        description="",
        price=12.0,
        wpwc_id=201,
    )
    line = OrderLine(
        id=11,
        order_id=1,
        general_object_id=8,
        quantity=1,
        status="draft",
        unit_price=12.0,
        discount=0,
        vat_rate=20.0,
        create_source="test",
        general_object=product,
        object_variation=variation,
        wpwc_id=999,
    )
    order = Order(
        id=2,
        reference="CMD-2501-00003",
        customer_id=12,
        status="draft",
        create_source="test",
        order_lines=[line],
        customer=Customers(id=12, customer_type="part"),
    )

    service._sync_line_ids(  # pylint: disable=W0212
        order,
        [{"id": 77, "product_id": 101, "variation_id": 201}],
        clear_all_cancelled=False,
    )

    assert line.wpwc_id == 999


def test_wc_orders_service_creates_missing_products_before_push() -> None:
    """
    Le push d'une commande doit créer les produits WooCommerce manquants avant de
    serialiser la commande.
    """
    service = object.__new__(WCOrdersService)
    service.session = MagicMock()
    service.api_read = MagicMock()
    service.api_write = MagicMock()
    service.sync_log_repo = MagicMock()
    service.product_service = MagicMock()

    product = GeneralObjects(
        id=9,
        supplier_id=1,
        general_object_type="book",
        ean13="9788888888888",
        name="Produit auto-sync",
        description="desc",
        wpwc_id=None,
    )
    line = OrderLine(
        id=12,
        order_id=2,
        general_object_id=9,
        quantity=2,
        status="draft",
        unit_price=10.0,
        discount=0,
        vat_rate=20.0,
        create_source="test",
        general_object=product,
        wpwc_id=50,
    )
    customer = Customers(id=12, wpwc_id="42", customer_type="part")
    customer.emails = [
        CustomerMails(
            customer_id=12,
            email_name="WooCommerce",
            email="x@example.com",
            is_active=True,
        ),
    ]
    order = Order(
        id=2,
        reference="CMD-2501-00005",
        customer_id=12,
        status="draft",
        create_source="test",
        customer=customer,
        order_lines=[line],
        wpwc_id=221,
    )
    service.api_write.put.return_value = MagicMock(
        status_code=200,
        json=MagicMock(
            return_value={
                "id": 221,
                "line_items": [{"id": 50, "product_id": 111, "variation_id": 0}],
            },
        ),
    )
    service.product_service.update_product.side_effect = lambda pid: setattr(
        product,
        "wpwc_id",
        111,
    )

    success, error = service.push_order(order)

    assert success is True
    assert error is None
    service.product_service.update_product.assert_called_once_with(product.id)


def test_wc_orders_service_push_order_updates_remote_order_and_logs_success() -> None:
    """
    Le push de commande doit appeler le bon endpoint de mise à jour et journaliser le succès.
    """
    service = object.__new__(WCOrdersService)
    service.session = MagicMock()
    service.api_read = MagicMock()
    service.api_write = MagicMock()
    service.sync_log_repo = MagicMock()

    product = GeneralObjects(
        id=9,
        supplier_id=1,
        general_object_type="book",
        ean13="9787777777777",
        name="Produit push",
        description="desc",
        wpwc_id=111,
    )
    line = OrderLine(
        id=12,
        order_id=2,
        general_object_id=9,
        quantity=2,
        status="draft",
        unit_price=10.0,
        discount=0,
        vat_rate=20.0,
        create_source="test",
        general_object=product,
        wpwc_id=50,
    )
    customer = Customers(id=12, wpwc_id="42", customer_type="part")
    customer.emails = [
        CustomerMails(
            customer_id=12,
            email_name="WooCommerce",
            email="x@example.com",
            is_active=True,
        ),
    ]
    order = Order(
        id=2,
        reference="CMD-2501-00004",
        customer_id=12,
        status="draft",
        create_source="test",
        customer=customer,
        order_lines=[line],
        wpwc_id=221,
    )
    service.api_read.get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(
            return_value={"line_items": [{"id": 50, "product_id": 111, "variation_id": 0}]}
        ),
    )
    service.api_write.put.return_value = MagicMock(
        status_code=200,
        json=MagicMock(
            return_value={
                "id": 221,
                "line_items": [
                    {
                        "id": 50,
                        "product_id": 111,
                        "variation_id": 0
                    },
                ],
            },
        ),
    )

    success, error = service.push_order(order)

    assert success is True
    assert error is None
    service.api_write.put.assert_called_once()
    service.sync_log_repo.log_order.assert_called_with(
        order_id=order.id,
        external_id="221",
        sync_direction="outbound",
        operation="update",
        sync_status="success",
    )
