"""Tests pour les modèles d'objets dans la base de données."""

from sqlalchemy.orm import Session, joinedload
from db_models.objects.objects import GeneralObjects, Books
from db_models.objects.suppliers import Suppliers

def test_object_create_read_and_update(db_session: Session, supplier: Suppliers,
                                       book_object: Books) -> None:    # pylint: disable=redefined-outer-name
    """test de lecture de l'objet rentré précédemment et de modification"""
    retrieved = db_session.query(GeneralObjects) \
                    .where(GeneralObjects.id==1) \
                    .options(
                        joinedload(GeneralObjects.supplier),
                        joinedload(GeneralObjects.book),
                        joinedload(GeneralObjects.object_tags),
                        joinedload(GeneralObjects.obj_metadatas),
                        joinedload(GeneralObjects.media_files)
                    ).first()
    if retrieved:
        retrieved.is_active = False
    db_session.add(retrieved)
    db_session.commit()
    retrieved = db_session.query(GeneralObjects).where(GeneralObjects.id==1).first()
    assert retrieved.is_active is False  # type: ignore
    assert retrieved.name == 'Test Book'  # type: ignore
    assert retrieved.supplier.name == "Fournisseur Test"    # type: ignore
    assert retrieved.book.author == "John Doe"  # type: ignore
    assert len(retrieved.object_tags) == 3  # type: ignore
    assert retrieved.obj_metadatas[0].semistructured_data == {"key": "value"}  # type: ignore
    assert len(retrieved.media_files) == 1  # type: ignore
    assert retrieved.media_files[0].file_name == "test_image.jpg"   # type: ignore
