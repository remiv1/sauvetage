"""Tests pour les modèles d'objets dans la base de données."""

from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from db_models.objects import InventoryMovements, GeneralObjects, Books, Suppliers


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
