"""Module de fixtures pour les tests liés aux inventaires"""

from decimal import Decimal
import time
import pytest
from sqlalchemy.orm import Session
from db_models.objects import InventoryMovements, GeneralObjects
from tests.fixtures.db_fixture import (  # pylint: disable=unused-import # type: ignore
    db_session_main,  # pylint: disable=unused-import # type: ignore
    engine,  # pylint: disable=unused-import # type: ignore
)  # pylint: disable=unused-import # type: ignore


@pytest.fixture
def inventory_movements(
    db_session_main: Session,  # pylint: disable=redefined-outer-name, unused-argument
    supplier,  # pylint: disable=redefined-outer-name, unused-argument
) -> list[InventoryMovements]:  # pylint: disable=redefined-outer-name, unused-argument
    """Fixture pour créer des mouvements d'inventaire de test."""
    # Générer des EAN13 uniques basés sur le timestamp
    timestamp = str(int(time.time() * 1000000))[-11:-1]

    # Créer les objets génériques d'abord
    general_object_1 = GeneralObjects(
        supplier_id=supplier.id,
        general_object_type="generic",
        ean13=f"978{timestamp}00",
        name="Test Generic Object 1",
        description="First test object for inventory movements.",
        price=Decimal("19.99"),
    )
    general_object_2 = GeneralObjects(
        supplier_id=supplier.id,
        general_object_type="book",
        ean13=f"978{timestamp}01",
        name="Test Generic Object 2",
        description="Second test object for inventory movements.",
        price=Decimal("25.42"),
    )
    db_session_main.add_all([general_object_1, general_object_2])
    db_session_main.flush()
    movements = [
        InventoryMovements(
            general_object_id=general_object_1.id,
            movement_type="inventory",
            quantity=10,
            price_at_movement=Decimal("19.99"),
            source="supplier",
            destination="stock",
            notes="Order #12345",
        ),
        InventoryMovements(
            general_object_id=general_object_1.id,
            movement_type="out",
            quantity=5,
            price_at_movement=Decimal("25.42"),
            source="stock",
            destination="customer",
            notes="order #54321",
        ),
        InventoryMovements(
            general_object_id=general_object_2.id,
            movement_type="in",
            quantity=3,
            price_at_movement=Decimal("25.42"),
            source="customer",
            destination="stock",
            notes="return order #54321",
        ),
    ]
    db_session_main.add_all(movements)
    db_session_main.flush()
    return movements
