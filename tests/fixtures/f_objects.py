"""Module de fixtures pour les tests liés aux objets"""

from typing import Dict, Any
import pytest
from sqlalchemy.orm import Session
from db_models.objects.objects import (
    GeneralObjects, Books, Tags, ObjectTags, ObjMetadatas, MediaFiles
)
from tests.fixtures.sqlite_fixture import db_session, engine  # pylint: disable=unused-import # type: ignore

@pytest.fixture
def tags(db_session: Session) -> list[Tags]: # pylint: disable=redefined-outer-name
    """Fixture pour créer des tags de test."""
    tags = [    # pylint: disable=redefined-outer-name
        Tags(
            name="Tag1",
            description="Description du Tag1"
        ),
        Tags(
            name="Tag2",
            description="Description du Tag2"
        ),
        Tags(
            name="Tag3",
            description="Description du Tag3"
        )
    ]
    db_session.add_all(tags)
    db_session.flush()
    return tags

@pytest.fixture
def book_object(db_session: Session, tags: list[Tags]) -> Books: # pylint: disable=redefined-outer-name
    """Fixture pour créer un objet de type livre."""
    general_object = GeneralObjects(
        supplier_id=1,
        general_object_type="book",
        ean13="9781234567890",
        name="Test Book",
        description="This is a test book.",
        price=19.99
    )
    db_session.add(general_object)
    db_session.flush()
    book = Books(
        id=general_object.id,
        general_object_id=general_object.id,
        author="John Doe",
        publisher="Test Publisher",
        diffuser="Test Diffuser",
        editor="Test Editor",
        genre="Fiction",
        publication_year=2020,
        pages=300
    )
    db_session.add(book)
    db_session.flush()
    object_tags = [
        ObjectTags(
            general_object_id=general_object.id,
            tag_id=tags[0].id
        ),
        ObjectTags(
            general_object_id=general_object.id,
            tag_id=tags[1].id
        ),
        ObjectTags(
            general_object_id=general_object.id,
            tag_id=tags[2].id
        )
    ]
    meta = ObjMetadatas(
        general_object_id=general_object.id,
        semistructured_data={"key": "value"}
    )
    media_dict: Dict[str, Any] = {
        "general_object_id": general_object.id,
        "file_name": "test_image.jpg",
        "file_type": "image/jpeg",
        "alt_text": "An image showing a test object",
        "file_link": "http://example.com/test_image.jpg",
        "is_principal": True
    }
    media = MediaFiles.from_dict(media_dict)
    db_session.add(book)
    db_session.add_all(object_tags)
    db_session.add(meta)
    db_session.add(media)
    db_session.commit()
    return general_object
