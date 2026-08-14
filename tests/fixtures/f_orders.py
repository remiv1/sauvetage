"""Module de fixtures pour les tests liés aux objets liées aux commandes"""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from db_models.objects import (
    CustomerAddresses,
    CustomerMails,
    CustomerParts,
    CustomerPhones,
    GeneralObjects,
    Invoice,
    InvoiceLine,
    ObjectPrices,
    Order,
    OrderLine,
    Shipment,
    ShipmentLine,
    VatRate,
    Customers,
)
from tests.fixtures.db_fixture import (  # pylint: disable=unused-import # type: ignore
    db_session_main,  # pylint: disable=unused-import # type: ignore
    engine,  # pylint: disable=unused-import # type: ignore
)  # pylint: disable=unused-import # type: ignore
from tests.fixtures.f_customers import (  # pylint: disable=unused-import # type: ignore
    complete_customer_part,  # pylint: disable=unused-import # type: ignore
)  # pylint: disable=unused-import # type: ignore
from tests.fixtures.f_objects import (  # pylint: disable=unused-import # type: ignore
    book_object,  # pylint: disable=unused-import # type: ignore
)  # pylint: disable=unused-import # type: ignore


@pytest.fixture
def henri_sync_context() -> dict[str, object]:
    """Contexte complet pour le flux d'envoi Henri vers la facture."""
    customer = Customers(wpwc_id="91", henrri_id=None, customer_type="part", is_active=True)
    customer.part = CustomerParts(customer_id=1, first_name="Julie", last_name="Benoit")
    customer.addresses = [
        CustomerAddresses(
            customer_id=1,
            address_name="Facturation",
            address_line1="15 rue de la Paix",
            address_line2="",
            city="Lille",
            state="Hauts-de-France",
            postal_code="59000",
            country="France",
            is_billing=True,
            is_shipping=False,
            is_active=True,
        )
    ]
    customer.emails = [
        CustomerMails(customer_id=1, email_name="Henri", email="julie@example.com", is_active=True)
    ]
    customer.phones = [
        CustomerPhones(customer_id=1, phone_name="Henri", phone_number="0600000000", is_active=True)
    ]

    product = GeneralObjects(
        id=81,
        supplier_id=1,
        general_object_type="book",
        ean13="9780012345678",
        name="Livre sync",
        description="Livre pour sync",
    )
    product.prices = [
        ObjectPrices(
            price=Decimal("42.00"),
            vat_rate=VatRate(code=1, rate=20.0, label="TVA 20%", wpwc_slug="standard"),
        )
    ]

    order = Order(  # pylint: disable=W0621
        id=12,
        reference="ORD-SYNC",
        customer_id=1,
        status="draft",
        create_source="test",
    )
    invoice = Invoice(  # pylint: disable=W0621
        id=31,
        order_id=12,
        customer_id=1,
        reference="INV-SYNC",
        total_amount=42.0,
        vat_amount=8.4,
        create_source="test",
        customer=customer,
        order=order,
    )
    line = InvoiceLine(
        id=41,
        invoice_id=31,
        order_line_id=1,
        reference="ART-SYNC",
        description="Livre sync",
        quantity=1,
        unit_price=42.0,
        discount=0.0,
        vat_rate=20.0,
    )
    line.order_line = OrderLine(
        id=1,
        order_id=12,
        general_object_id=81,
        quantity=1,
        unit_price=42.0,
        vat_rate=20.0,
        create_source="test",
        general_object=product,
    )
    invoice.lines = [line]
    return {
        "customer": customer,
        "product": product,
        "order": order,
        "invoice": invoice,
        "line": line,
    }


@pytest.fixture
def henri_invoice_context() -> tuple[Customers, Order, Invoice, InvoiceLine, OrderLine]:
    """Contexte Henri minimal pour le contrat d'une facture avec client, produit et ligne."""
    customer = Customers(wpwc_id="55", henrri_id="9", customer_type="part", is_active=True)
    customer.part = CustomerParts(customer_id=1, first_name="Bob", last_name="Lenoir")
    customer.addresses = [
        CustomerAddresses(
            customer_id=1,
            address_name="Facturation",
            address_line1="12 rue de la Paix",
            address_line2="",
            city="Paris",
            state="Ile-de-France",
            postal_code="75002",
            country="France",
            is_billing=True,
            is_shipping=False,
            is_active=True,
        )
    ]
    order = Order(  # pylint: disable=W0621
        id=1,
        reference="ORD-1",
        customer_id=1,
        status="paid",
        create_source="e-commerce",
    )
    invoice = Invoice(  # pylint: disable=W0621
        id=11,
        order_id=1,
        customer_id=1,
        reference="INV-1",
        total_amount=150.0,
        vat_amount=30.0,
        create_source="e-commerce",
        order=order,
        customer=customer,
    )
    invoice_line = InvoiceLine(
        id=21,
        invoice_id=11,
        order_line_id=1,
        reference="ART-1",
        description="Produit test",
        quantity=1,
        unit_price=150.0,
        discount=0.0,
        vat_rate=20.0,
    )
    order_line = OrderLine(
        id=1,
        order_id=1,
        quantity=1,
        unit_price=150.0,
        vat_rate=20.0,
        create_source="e-commerce",
    )
    invoice.lines = [invoice_line]
    order.order_lines = [order_line]
    return customer, order, invoice, invoice_line, order_line


@pytest.fixture
def order(
    db_session_main: Session,  # pylint: disable=redefined-outer-name # type: ignore
    complete_customer_part: Customers,  # pylint: disable=redefined-outer-name # type: ignore
    book_object: GeneralObjects,  # pylint: disable=redefined-outer-name # type: ignore
) -> Order:  # pylint: disable=redefined-outer-name # type: ignore
    """Fixture pour créer une commande de test."""
    # Récupérer l'adresse de facturation
    invoice_address = (
        db_session_main.query(CustomerAddresses)
        .filter(
            CustomerAddresses.customer_id == complete_customer_part.id,
            CustomerAddresses.is_billing == True,  # pylint: disable=singleton-comparison
            CustomerAddresses.is_active == True,  # pylint: disable=singleton-comparison
        )
        .first()
    )

    # Récupérer l'adresse de livraison
    delivery_address = (
        db_session_main.query(CustomerAddresses)
        .filter(
            CustomerAddresses.customer_id == complete_customer_part.id,
            CustomerAddresses.is_shipping == True,  # pylint: disable=singleton-comparison
            CustomerAddresses.is_active == True,  # pylint: disable=singleton-comparison
        )
        .first()
    )

    order_object = Order(
        reference="ORD123456",
        customer_id=complete_customer_part.id,  # type: ignore
        invoice_address_id=invoice_address.id if invoice_address else None,
        delivery_address_id=delivery_address.id if delivery_address else None,
        status="pending",
        create_source="e-commerce",
    )
    db_session_main.add(order_object)
    db_session_main.flush()
    order_lines = [
        OrderLine(
            order_id=order_object.id,
            general_object_id=book_object.id,  # type: ignore
            quantity=2,
            unit_price=19.99,
            vat_rate=5.5,
            create_source="e-commerce",
        ),
        OrderLine(
            order_id=order_object.id,
            general_object_id=book_object.id,  # type: ignore
            quantity=1,
            unit_price=19.99,
            vat_rate=5.5,
            create_source="e-commerce",
        ),
    ]
    db_session_main.add_all(order_lines)
    db_session_main.flush()
    db_session_main.commit()
    return order_object


@pytest.fixture
def invoice(
    db_session_main: Session,  # pylint: disable=redefined-outer-name # type: ignore
    order,  # pylint: disable=redefined-outer-name # type: ignore
) -> Invoice:  # pylint: disable=redefined-outer-name # type: ignore
    """Fixture pour créer une facture de test."""
    total_amount = sum(ol.unit_price * ol.quantity for ol in order.order_lines)  # type: ignore
    vat_amount = sum(
        ol.unit_price * ol.quantity * ol.vat_rate / 100  # type: ignore
        for ol in order.order_lines
    )  # type: ignore
    invoice_object = Invoice(
        order_id=order.id,
        customer_id=order.customer_id,
        reference="INV123456",
        total_amount=total_amount,
        vat_amount=vat_amount,
        create_source="e-commerce",
    )
    db_session_main.add(invoice_object)
    db_session_main.flush()

    # Créer les lignes de facture associées à chaque ligne de commande
    for order_line in order.order_lines:  # type: ignore
        invoice_line = InvoiceLine(
            invoice_id=invoice_object.id,
            order_line_id=order_line.id,  # type: ignore
            reference=f"INVL-{invoice_object.id}-{order_line.id}",
            description=f"Article ligne {order_line.id}",  # type: ignore
            quantity=order_line.quantity,  # type: ignore
            unit_price=order_line.unit_price,  # type: ignore
            discount=order_line.discount,  # type: ignore
            vat_rate=order_line.vat_rate,  # type: ignore
        )
        db_session_main.add(invoice_line)

    db_session_main.flush()
    return invoice_object


@pytest.fixture
def shipment(
    db_session_main: Session,  # pylint: disable=redefined-outer-name # type: ignore
    order,  # pylint: disable=redefined-outer-name # type: ignore
) -> Shipment:  # pylint: disable=redefined-outer-name # type: ignore
    """Fixture pour créer un envoi de test."""
    shipment_object = Shipment(
        order_id=order.id,
        reference="SHP123456",
        carrier="UPS",
        tracking_number="1Z999AA10123456784",
        create_source="e-commerce",
    )
    db_session_main.add(shipment_object)
    db_session_main.flush()

    # Créer les lignes d'envoi associées à chaque ligne de commande
    for order_line in order.order_lines:  # type: ignore
        shipment_line = ShipmentLine(
            shipment_id=shipment_object.id,
            order_line_id=order_line.id,  # type: ignore
            quantity=order_line.quantity,  # type: ignore
        )
        db_session_main.add(shipment_line)

    db_session_main.flush()
    db_session_main.commit()
    return shipment_object
