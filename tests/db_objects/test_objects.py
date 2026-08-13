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
    assert retrieved.media_files[0].file_link == "http://example.com/test_image.jpg"  # type: ignore


def test_get_by_ref_finds_existing_object_even_when_inactive(
    db_session_main: Session,
    supplier: Suppliers,
) -> None:
    """La recherche doit pouvoir retrouver un objet existant pour une mise à jour même s’il est inactif."""
    from db_models.repositories.objects.objects import ObjectsRepository

    general_object = GeneralObjects(
        supplier_id=supplier.id,
        general_object_type="book",
        ean13="9780000000001",
        name="Livre ancien",
        description="Objet déjà existant",
        is_active=False,
    )
    db_session_main.add(general_object)
    db_session_main.commit()

    repo = ObjectsRepository(db_session_main)
    found = repo.get_by_ref("9780000000001", only_actives=False)

    assert found is not None
    assert found.id == general_object.id
    assert found.ean13 == "9780000000001"
