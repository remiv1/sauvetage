"""Test pour les commandes de bout en bout."""

from unittest.mock import MagicMock

from sqlalchemy.orm import Session, joinedload
from db_models.objects import Order, OrderLine, Invoice, Shipment, InvoiceLine, ShipmentLine
from db_models.repositories.orders.repository import OrdersRepository


def test_cancel_order_cancels_lines_and_releases_reservations() -> None:
    """L'annulation complète doit restituer chaque réservation dans une transaction."""
    session = MagicMock()
    repository = OrdersRepository(session)
    order = Order(
        id=7,
        reference="CMD-2608-00007",
        customer_id=1,
        status="draft",
        create_source="test",
    )
    order.order_lines = [
        OrderLine(
            id=1,
            order_id=7,
            general_object_id=10,
            quantity=2,
            status="draft",
            unit_price=12,
            discount=0,
            vat_rate=20,
            create_source="test",
        ),
        OrderLine(
            id=2,
            order_id=7,
            general_object_id=11,
            quantity=3,
            status="invoiced",
            unit_price=8,
            discount=0,
            vat_rate=20,
            create_source="test",
        ),
    ]

    repository.cancel_order(order, update_source="backoffice")

    assert order.status == "cancelled"
    assert order.order_lines[0].status == "cancelled"
    assert order.order_lines[1].status == "invoiced"
    movements = [call.args[0] for call in session.add.call_args_list]
    assert [movement.quantity for movement in movements] == [-2]
    session.commit.assert_called_once()


def test_create_order_with_invoice_and_shipment(
    db_session_main: Session,
    order: Order,  # pylint: disable=redefined-outer-name # type: ignore
    invoice: Invoice,  # pylint: disable=redefined-outer-name # type: ignore
    shipment: Shipment,
) -> None:  # pylint: disable=redefined-outer-name # type: ignore
    """Test de création d'une commande avec une facture et un envoi associés."""
    db_session_main.add(order)
    db_session_main.commit()
    db_session_main.add(invoice)
    db_session_main.commit()
    db_session_main.add(shipment)
    db_session_main.commit()
    created_order = (
        db_session_main.query(Order)
        .options(
            joinedload(Order.order_lines),
            joinedload(Order.order_lines).joinedload(OrderLine.invoice_lines).joinedload(InvoiceLine.invoice),
            joinedload(Order.order_lines).joinedload(OrderLine.shipment_lines).joinedload(ShipmentLine.shipment),
        )
        .where(Order.id == order.id)
        .first()
    )  # type: ignore
    assert created_order is not None
    assert created_order.order_lines[0].invoice_lines is not None  # type: ignore
    assert len(created_order.order_lines[0].invoice_lines) > 0  # type: ignore
    assert created_order.order_lines[0].invoice_lines[0].invoice.reference == "INV123456"  # type: ignore
    assert created_order.order_lines[0].shipment_lines is not None  # type: ignore
    assert len(created_order.order_lines[0].shipment_lines) > 0  # type: ignore
    assert created_order.order_lines[0].shipment_lines[0].shipment.reference == "SHP123456"  # type: ignore
