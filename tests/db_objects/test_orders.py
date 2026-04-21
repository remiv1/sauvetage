"""Test pour les commandes de bout en bout."""

from sqlalchemy.orm import Session, joinedload
from db_models.objects import Order, OrderLine, Invoice, Shipment, InvoiceLine, ShipmentLine


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
