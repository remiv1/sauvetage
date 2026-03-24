"""Module de fixtures pour les tests liés aux stocks"""

from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from db_models.objects.stocks import OrderIn, OrderInLine, DilicomReferencial
from db_models.objects.inventory import InventoryMovements
from tests.fixtures.db_fixture import (  # pylint: disable=unused-import # type: ignore
    db_session_main,  # pylint: disable=unused-import # type: ignore
    engine,  # pylint: disable=unused-import # type: ignore
)  # pylint: disable=unused-import # type: ignore


@pytest.fixture
def order_in(
    db_session_main: Session,  # pylint: disable=redefined-outer-name, unused-argument
    general_object,  # pylint: disable=redefined-outer-name, unused-argument
    supplier,  # pylint: disable=redefined-outer-name, unused-argument
):
    """Fixture pour créer une commande d'entrée de stock."""
    order = OrderIn(
        order_ref="temp",
        external_ref="ext-000-001",
        supplier_id=supplier.id,
        value=Decimal("199.99"),
        order_state="draft",
    )
    db_session_main.add(order)
    db_session_main.flush()
    order.order_ref = f"CMD-{order.id:06d}"
    db_session_main.flush()
    inventory_movements = []
    inventory_movements.append(InventoryMovements(
        general_object_id=general_object.id,
        movement_type="pending",
        quantity=10,
        price_at_movement=Decimal("19.99"),
        source="supplier",
        destination="stock",
        notes=f"Order #{order.order_ref}",
    ))
    inventory_movements.append(InventoryMovements(
        general_object_id=general_object.id,
        movement_type="pending",
        quantity=10,
        price_at_movement=Decimal("15.99"),
        source="supplier",
        destination="stock",
        notes=f"Order #{order.order_ref}",
    ))
    db_session_main.add_all(inventory_movements)
    db_session_main.flush()
    line = []
    line.append(OrderInLine(
        order_in_id=order.id,
        general_object_id=general_object.id,
        inventory_movement_id=inventory_movements[0].id,
        qty_ordered=10,
        unit_price=Decimal("19.99"),
        vat_rate=Decimal("5.50"),
    ))
    line.append(OrderInLine(
        order_in_id=order.id,
        general_object_id=general_object.id,
        inventory_movement_id=inventory_movements[1].id,
        qty_ordered=10,
        unit_price=Decimal("15.99"),
        vat_rate=Decimal("5.50"),
    ))
    db_session_main.add_all(line)
    db_session_main.flush()

    return order

@pytest.fixture
def order_in_return(
    db_session_main: Session,  # pylint: disable=redefined-outer-name, unused-argument
    general_object,  # pylint: disable=redefined-outer-name, unused-argument
    supplier,  # pylint: disable=redefined-outer-name, unused-argument
):
    """Fixture pour créer une commande de retour fournisseur."""
    order = OrderIn(
        order_ref="temp-return",
        external_ref="ext-return-000-001",
        supplier_id=supplier.id,
        value=Decimal("99.99"),
        order_state="draft",
    )
    db_session_main.add(order)
    db_session_main.flush()
    order.order_ref = f"RET-{order.id:06d}"
    db_session_main.flush()
    inventory_movement = InventoryMovements(
        general_object_id=general_object.id,
        movement_type="pending",
        quantity=-5,
        price_at_movement=Decimal("19.99"),
        source="stock",
        destination="supplier",
        notes=f"Return Order #{order.order_ref}",
    )
    db_session_main.add(inventory_movement)
    db_session_main.flush()
    line = OrderInLine(
        order_in_id=order.id,
        general_object_id=general_object.id,
        inventory_movement_id=inventory_movement.id,
        qty_ordered=5,
        unit_price=Decimal("19.99"),
        vat_rate=Decimal("5.50"),
    )
    db_session_main.add(line)
    db_session_main.flush()

    return order

@pytest.fixture
def dilicom_referencial(db_session_main: Session,   # pylint: disable=redefined-outer-name, unused-argument
                        book_object, supplier):  # pylint: disable=redefined-outer-name, unused-argument
    """Fixture pour créer une entrée dans le référentiel Dilicom."""
    referencial = DilicomReferencial(
        ean13=book_object.ean13,
        gln13=supplier.gln13,
        create_ref=True,
        is_active=True,
        dilicom_synced=True
    )
    db_session_main.add(referencial)
    db_session_main.flush()
    return referencial
