"""Tests pour les modèles d'objets dans la base de données."""

from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from db_models.objects import (
    InventoryMovements,
    GeneralObjects,
    Books,
    Suppliers,
    ObjectPrices,
    VatRate,
    Order,
    OrderLine,
)
from db_models.repositories.orders import OrdersRepository
from app_front.blueprints.order.utils import invoice_order, ship_order
from app_front.main import app


def test_multiple_prices_can_have_distinct_vat_rates(
    db_session_main: Session,
    supplier,
) -> None:
    """Un article peut avoir plusieurs prix valides, chacun avec son taux TVA."""
    vat_5 = VatRate(
        code=1,
        rate=5.5,
        label="Taux réduit",
        date_start=datetime.now(timezone.utc),
    )
    vat_20 = VatRate(
        code=3,
        rate=20.0,
        label="Taux normal",
        date_start=datetime.now(timezone.utc),
    )
    db_session_main.add_all([vat_5, vat_20])
    db_session_main.flush()

    obj = GeneralObjects(
        supplier_id=supplier.id,
        general_object_type="generic",
        ean13="9780000000001",
        name="Objet multi-prix",
        description="Objet répertoriant plusieurs prix valides.",
    )
    db_session_main.add(obj)
    db_session_main.flush()

    row_5 = ObjectPrices(
        general_object_id=obj.id,
        price=Decimal("10.00"),
        vat_rate_id=vat_5.id,
        from_date=date.today(),
        to_date=None,
    )
    row_20 = ObjectPrices(
        general_object_id=obj.id,
        price=Decimal("12.00"),
        vat_rate_id=vat_20.id,
        from_date=date.today(),
        to_date=None,
    )
    db_session_main.add_all([row_5, row_20])
    db_session_main.flush()

    valid_prices = obj.get_valid_prices()
    assert len(valid_prices) == 2
    assert {float(price.vat_rate.rate) for price in valid_prices} == {5.5, 20.0}
    assert {float(price.price) for price in valid_prices} == {10.0, 12.0}


def test_order_line_is_split_for_multiple_valid_prices(
    db_session_main: Session,
    supplier,
    complete_customer_part,
) -> None:
    """Une commande doit créer autant de lignes que de prix valides pour l'article."""
    vat_5 = VatRate(
        code=1,
        rate=5.5,
        label="Taux réduit",
        date_start=datetime.now(timezone.utc),
    )
    vat_20 = VatRate(
        code=3,
        rate=20.0,
        label="Taux normal",
        date_start=datetime.now(timezone.utc),
    )
    db_session_main.add_all([vat_5, vat_20])
    db_session_main.flush()

    obj = GeneralObjects(
        supplier_id=supplier.id,
        general_object_type="generic",
        ean13="9780000000002",
        name="Objet prix multiple",
        description="Objet avec plusieurs prix valides.",
    )
    db_session_main.add(obj)
    db_session_main.flush()

    db_session_main.add_all(
        [
            ObjectPrices(
                general_object_id=obj.id,
                price=Decimal("10.00"),
                vat_rate_id=vat_5.id,
                from_date=date.today(),
                to_date=None,
            ),
            ObjectPrices(
                general_object_id=obj.id,
                price=Decimal("12.00"),
                vat_rate_id=vat_20.id,
                from_date=date.today(),
                to_date=None,
            ),
        ]
    )
    db_session_main.flush()

    order = Order(
        reference="CMD-TEST-0001",
        customer_id=complete_customer_part.id,
        status="draft",
        create_source="test",
    )
    db_session_main.add(order)
    db_session_main.flush()

    repo = OrdersRepository(db_session_main)
    created_lines = repo.add_line(
        order,
        general_object_id=obj.id,
        quantity=2,
        unit_price=0.0,
        vat_rate=0.0,
    )

    assert isinstance(created_lines, list)
    assert len(created_lines) == 2
    assert {float(line.unit_price) for line in created_lines} == {10.0, 12.0}
    assert {float(line.vat_rate) for line in created_lines} == {5.5, 20.0}
    assert db_session_main.query(OrderLine).filter(OrderLine.order_id == order.id).count() == 2


def test_multi_price_order_can_be_invoiced_and_shipped_by_split_lines(
    db_session_main: Session,
    supplier,
    complete_customer_part,
) -> None:
    """Une commande multi-prix doit être facturée puis expédiée en gardant chaque ligne séparée."""
    vat_5 = VatRate(
        code=1,
        rate=5.5,
        label="Taux réduit",
        date_start=datetime.now(timezone.utc),
    )
    vat_20 = VatRate(
        code=3,
        rate=20.0,
        label="Taux normal",
        date_start=datetime.now(timezone.utc),
    )
    db_session_main.add_all([vat_5, vat_20])
    db_session_main.flush()

    obj = GeneralObjects(
        supplier_id=supplier.id,
        general_object_type="generic",
        ean13="9780000000003",
        name="Objet multi-prix business flow",
        description="Objet avec plusieurs prix valides et plusieurs TVA.",
    )
    db_session_main.add(obj)
    db_session_main.flush()

    db_session_main.add_all(
        [
            ObjectPrices(
                general_object_id=obj.id,
                price=Decimal("10.00"),
                vat_rate_id=vat_5.id,
                from_date=date.today(),
                to_date=None,
            ),
            ObjectPrices(
                general_object_id=obj.id,
                price=Decimal("12.00"),
                vat_rate_id=vat_20.id,
                from_date=date.today(),
                to_date=None,
            ),
        ]
    )
    db_session_main.flush()

    order = Order(
        reference="CMD-TEST-0002",
        customer_id=complete_customer_part.id,
        status="draft",
        create_source="test",
    )
    db_session_main.add(order)
    db_session_main.flush()

    repo = OrdersRepository(db_session_main)
    created_lines = repo.add_line(
        order,
        general_object_id=obj.id,
        quantity=1,
        unit_price=0.0,
        vat_rate=0.0,
    )
    assert isinstance(created_lines, list)
    assert len(created_lines) == 2

    with app.app_context():
        invoice = invoice_order(
            order.id,
            [
                {"order_line_id": created_lines[0].id, "quantity": 1},
                {"order_line_id": created_lines[1].id, "quantity": 1},
            ],
        )
        assert len(invoice.lines) == 2
        assert {float(line.unit_price) for line in invoice.lines} == {10.0, 12.0}

        shipment = ship_order(
            order.id,
            [
                {"order_line_id": created_lines[0].id, "quantity": 1},
                {"order_line_id": created_lines[1].id, "quantity": 1},
            ],
            carrier="UPS",
        )
        assert len(shipment["lines"]) == 2
        assert order.status == "shipped"


def test_add_movements(
    db_session_main: Session,
    general_object,  # pylint: disable=redefined-outer-name, unused-argument
    inventory_movements: list[
        InventoryMovements
    ],  # pylint: disable=redefined-outer-name, unused-argument
) -> None:  # pylint: disable=redefined-outer-name, unused-argument
    """Test d'ajout et de lecture des mouvements d'inventaire."""
    for movement in inventory_movements:
        db_session_main.add(movement)
    db_session_main.commit()
    retrieved = db_session_main.query(InventoryMovements).all()
    assert len(retrieved) == len(inventory_movements)
    for i, movement in enumerate(inventory_movements):
        assert retrieved[i].general_object_id == movement.general_object_id
        assert retrieved[i].movement_type == movement.movement_type
        assert retrieved[i].quantity == movement.quantity
        assert retrieved[i].price_at_movement == movement.price_at_movement
        assert retrieved[i].source == movement.source
        assert retrieved[i].destination == movement.destination
        assert retrieved[i].notes == movement.notes

    # Vérifier les propriétés du general_object fixture
    assert general_object is not None
    assert general_object.is_active is True
    assert general_object.name == "Test Generic Object"
    assert general_object.price == Decimal("29.99")
    assert general_object.supplier is not None
    assert general_object.supplier.name == "Fournisseur Test"
