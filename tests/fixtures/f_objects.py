"""Module de fixtures pour les tests liés aux objets"""

from typing import Dict, Any
import pytest
from sqlalchemy.orm import Session
from db_models.objects import (
    GeneralObjects, Books, Tags, ObjectTags, ObjMetadatas, MediaFiles,
    Suppliers
)
from tests.fixtures.db_fixture import (  # pylint: disable=unused-import # type: ignore
    db_session_main,  # pylint: disable=unused-import # type: ignore
    engine,  # pylint: disable=unused-import # type: ignore
)  # pylint: disable=unused-import # type: ignore


@pytest.fixture
def tags(
    db_session_main: Session,  # pylint: disable=redefined-outer-name, unused-argument
) -> list[Tags]:  # pylint: disable=redefined-outer-name
    """Fixture pour créer des tags de test."""
    tags = [  # pylint: disable=redefined-outer-name
        Tags(name="Tag1", description="Description du Tag1"),
        Tags(name="Tag2", description="Description du Tag2"),
        Tags(name="Tag3", description="Description du Tag3"),
    ]
    db_session_main.add_all(tags)
    db_session_main.flush()
    return tags


@pytest.fixture
def book_object(
    db_session_main: Session, supplier: Suppliers, tags: list[Tags]  # pylint: disable=redefined-outer-name, unused-argument
) -> Books:  # pylint: disable=redefined-outer-name
    """Fixture pour créer un objet de type livre."""
    general_object = GeneralObjects(
        supplier_id=supplier.id,
        general_object_type="book",
        ean13="9781234567890",
        name="Test Book",
        description="This is a test book.",
        price=19.99,
    )
    db_session_main.add(general_object)
    db_session_main.flush()
    book = Books(
        id=general_object.id,
        general_object_id=general_object.id,
        author="John Doe",
        diffuser="Test Diffuser",
        editor="Test Editor",
        genre="Fiction",
        publication_year=2020,
        pages=300,
    )
    db_session_main.add(book)
    db_session_main.flush()
    object_tags = [
        ObjectTags(general_object_id=general_object.id, tag_id=tags[0].id),
        ObjectTags(general_object_id=general_object.id, tag_id=tags[1].id),
        ObjectTags(general_object_id=general_object.id, tag_id=tags[2].id),
    ]
    meta = ObjMetadatas(
        general_object_id=general_object.id, semistructured_data={"key": "value"}
    )
    media_dict: Dict[str, Any] = {
        "general_object_id": general_object.id,
        "file_name": "test_image.jpg",
        "file_type": "image/jpeg",
        "alt_text": "An image showing a test object",
        "file_link": "http://example.com/test_image.jpg",
        "is_principal": True,
    }
    media = MediaFiles.from_dict(media_dict)
    db_session_main.add(book)
    db_session_main.add_all(object_tags)
    db_session_main.add(meta)
    db_session_main.add(media)
    db_session_main.commit()
    return general_object
