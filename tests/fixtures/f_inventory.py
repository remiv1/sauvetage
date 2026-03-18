"""Module de fixtures pour les tests liés aux inventaires"""

from typing import Dict, Any
import pytest
from sqlalchemy.orm import Session
from db_models.objects import InventoryMovements
from tests.fixtures.db_fixture import (  # pylint: disable=unused-import # type: ignore
    db_session_main,  # pylint: disable=unused-import # type: ignore
    engine,  # pylint: disable=unused-import # type: ignore
)  # pylint: disable=unused-import # type: ignore


@pytest.fixture
def inventory_movements(
    db_session_main: Session,  # pylint: disable=redefined-outer-name, unused-argument
) -> list[InventoryMovements]:  # pylint: disable=redefined-outer-name
    """Fixture pour créer des mouvements d'inventaire de test."""
    movements = [
        InventoryMovements(
            general_object_id=1,
            movement_type="inventory",
            quantity=10,
            price_at_movement=19.99,
            source="supplier",
            destination="stock",
            notes="Order #12345",
        ),
        InventoryMovements(
            general_object_id=1,
            movement_type="out",
            quantity=5,
            price_at_movement=25.42,
            source="stock",
            destination="customer",
            notes="order #54321",
        ),
        InventoryMovements(
            general_object_id=2,
            movement_type="in",
            quantity=3,
            price_at_movement=25.42,
            source="customer",
            destination="stock",
            notes="return order #54321",
        ),
    ]
    db_session_main.add_all(movements)
    db_session_main.flush()
    return movements
