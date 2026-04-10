"""Tests pour les modèles d'objets dans la base de données."""

from sqlalchemy.orm import Session, joinedload
from db_models.objects import GeneralObjects, Books, Suppliers


def test_object_create_read_and_update(
    db_session_main: Session,
    supplier: Suppliers,  # pylint: disable=redefined-outer-name, unused-argument
    book_object: Books,  # pylint: disable=redefined-outer-name, unused-argument
) -> None:
    """test de lecture de l'objet rentré précédemment et de modification"""
    retrieved = (
        db_session_main.query(GeneralObjects)
        .where(GeneralObjects.ean13 == "9781234567890")
        .options(
            joinedload(GeneralObjects.supplier),
            joinedload(GeneralObjects.book),
            joinedload(GeneralObjects.object_tags),
            joinedload(GeneralObjects.obj_metadatas),
            joinedload(GeneralObjects.media_files),
        )
        .first()
    )
    assert retrieved is not None
    retrieved.is_active = False
    db_session_main.add(retrieved)
    db_session_main.commit()
    retrieved = (
        db_session_main.query(GeneralObjects)
        .where(GeneralObjects.ean13 == "9781234567890")
        .first()
    )
    assert retrieved is not None
    assert retrieved.is_active is False  # type: ignore
    assert retrieved.name == "Test Book"  # type: ignore
    assert retrieved.supplier.name == "Fournisseur Test"  # type: ignore
    assert retrieved.book.author == "John Doe"  # type: ignore
    assert len(retrieved.object_tags) == 3  # type: ignore
    assert retrieved.obj_metadatas.semistructured_data == {"key": "value"}  # type: ignore
    assert len(retrieved.media_files) == 1  # type: ignore
    assert retrieved.media_files[0].file_name == "test_image.jpg"  # type: ignore
