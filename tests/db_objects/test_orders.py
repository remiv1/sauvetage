"""Test pour les commandes de bout en bout."""

from sqlalchemy.orm import Session, joinedload
from db_models.objects.orders import Order, OrderLine
from db_models.objects.invoices import Invoice
from db_models.objects.shipments import Shipment

def test_create_order_with_invoice_and_shipment(db_session: Session, order: Order,  # pylint: disable=redefined-outer-name # type: ignore
                                                invoice: Invoice,   # pylint: disable=redefined-outer-name # type: ignore
                                                shipment: Shipment) -> None:    # pylint: disable=redefined-outer-name # type: ignore
    """Test de création d'une commande avec une facture et un envoi associés."""
    db_session.add(order)
    db_session.commit()
    db_session.add(invoice)
    db_session.commit()
    db_session.add(shipment)
    db_session.commit()
    created_order = db_session.query(Order).options(
        joinedload(Order.order_lines),
        joinedload(Order.order_lines).joinedload(OrderLine.invoice),
        joinedload(Order.order_lines).joinedload(OrderLine.shipment)
        ).where(Order.id == order.id).first() # type: ignore
    assert created_order is not None
    assert created_order.order_lines[0].invoice is not None    # type: ignore
    assert created_order.order_lines[0].invoice.reference == "INV123456" # type: ignore
    assert created_order.order_lines[0].shipment is not None   # type: ignore
    assert created_order.order_lines[0].shipment.reference == "SHP123456"   # type: ignore
