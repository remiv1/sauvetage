"""Tests pour les modèles d'objets dans la base de données."""

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
    assert retrieved is not None
    assert retrieved.is_active is False  # type: ignore
    assert retrieved.name == "Test Book"  # type: ignore
    assert retrieved.supplier.name == "Fournisseur Test"  # type: ignore
    assert retrieved.book.author == "John Doe"  # type: ignore
    assert len(retrieved.object_tags) == 3  # type: ignore
    assert retrieved.obj_metadatas[0].semistructured_data == {"key": "value"}  # type: ignore
    assert len(retrieved.media_files) == 1  # type: ignore
    assert retrieved.media_files[0].file_name == "test_image.jpg"  # type: ignore
