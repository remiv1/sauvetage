"""Module de fixtures pour les tests liés aux objets liées aux commandes"""

from typing import List
import pytest
from sqlalchemy.orm import Session
from db_models.objects.objects import GeneralObjects
from db_models.objects.customers import Customers, CustomerAddresses
from db_models.objects.orders import Order, OrderLine
from db_models.objects.invoices import Invoice
from db_models.objects.shipments import Shipment
from tests.fixtures.sqlite_fixture import db_session, engine  # pylint: disable=unused-import # type: ignore
from tests.fixtures.f_objects import book_object    # pylint: disable=redefined-outer-name # type: ignore
from tests.fixtures.f_customers import complete_customer_part   # pylint: disable=unused-import # type: ignore

@pytest.fixture
def order(db_session: Session, complete_customer_part: Customers,   # pylint: disable=redefined-outer-name # type: ignore
          book_object: GeneralObjects) -> Order: # pylint: disable=redefined-outer-name # type: ignore
    """Fixture pour créer une commande de test."""
    # Récupérer l'adresse de facturation
    invoice_address = (
        db_session.query(CustomerAddresses)
        .filter(
            CustomerAddresses.customer_id == complete_customer_part.id,
            CustomerAddresses.is_billing == True,   # pylint: disable=singleton-comparison
            CustomerAddresses.is_active == True     # pylint: disable=singleton-comparison
        )
        .first()
    )

    # Récupérer l'adresse de livraison
    delivery_address = (
        db_session.query(CustomerAddresses)
        .filter(
            CustomerAddresses.customer_id == complete_customer_part.id,
            CustomerAddresses.is_shipping == True,  # pylint: disable=singleton-comparison
            CustomerAddresses.is_active == True     # pylint: disable=singleton-comparison
        )
        .first()
    )

    order_object = Order(
        reference="ORD123456",
        customer_id=complete_customer_part.id, # type: ignore
        invoice_address_id=invoice_address.id if invoice_address else None,
        delivery_address_id=delivery_address.id if delivery_address else None,
        status="pending",
        create_source="e-commerce"
    )
    db_session.add(order_object)
    db_session.flush()
    order_lines = [
        OrderLine(
            order_id=order_object.id,
            general_object_id=book_object.id, # type: ignore
            quantity=2,
            unit_price=19.99,
            vat_rate=5.5,
            create_source="e-commerce"
        ),
        OrderLine(
            order_id=order_object.id,
            general_object_id=book_object.id, # type: ignore
            quantity=1,
            unit_price=19.99,
            vat_rate=5.5,
            create_source="e-commerce"
        )
    ]
    db_session.add_all(order_lines)
    db_session.flush()
    db_session.commit()
    return order_object

@pytest.fixture
def invoice(db_session: Session, order) -> Invoice: # pylint: disable=redefined-outer-name # type: ignore
    """Fixture pour créer une facture de test."""
    total_amount = sum(ol.unit_price * ol.quantity for ol in order.order_lines) # type: ignore
    vat_amount = sum(ol.unit_price * ol.quantity * ol.vat_rate / 100   # type: ignore
                     for ol in order.order_lines)   # type: ignore
    invoice_object = Invoice(
        reference="INV123456",
        total_amount=total_amount,
        vat_amount=vat_amount,
        create_source="e-commerce"
    )
    db_session.add(invoice_object)
    db_session.flush()
    order.order_lines[0].invoice_id = invoice_object.id  # type: ignore
    order.order_lines[1].invoice_id = invoice_object.id  # type: ignore
    db_session.add_all(order.order_lines)  # type: ignore
    db_session.flush()
    return invoice_object

@pytest.fixture
def shipment(db_session: Session, order) -> Shipment: # pylint: disable=redefined-outer-name # type: ignore
    """Fixture pour créer un envoi de test."""
    shipment_object = Shipment(
        reference="SHP123456",
        carrier="UPS",
        tracking_number="1Z999AA10123456784",
        create_source="e-commerce"
    )
    db_session.add(shipment_object)
    db_session.flush()
    order.order_lines[0].shipment_id = shipment_object.id  # type: ignore
    order.order_lines[1].shipment_id = shipment_object.id  # type: ignore
    db_session.add_all(order.order_lines)  # type: ignore
    db_session.flush()
    db_session.commit()
    return shipment_object
