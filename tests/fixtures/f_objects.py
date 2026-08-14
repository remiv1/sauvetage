"""Module de fixtures pour les tests liés aux objets"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

import pytest
from sqlalchemy.orm import Session

from db_models.objects import (
    Books,
    GeneralObjects,
    MediaFiles,
    ObjMetadatas,
    ObjectPrices,
    ObjectTags,
    Suppliers,
    Tags,
    VatRate,
)
from tests.fixtures.db_fixture import (  # pylint: disable=unused-import # type: ignore
    db_session_main,  # pylint: disable=unused-import # type: ignore
    engine,  # pylint: disable=unused-import # type: ignore
)  # pylint: disable=unused-import # type: ignore


@pytest.fixture
def standard_vat_rate() -> VatRate:
    """Taux de TVA standard pour les payloads WooCommerce."""
    return VatRate(
        code=1,
        rate=5.5,
        label="Taux réduit",
        wpwc_slug="taux-reduit",
        date_start=datetime.now(),
    )


@pytest.fixture
def henri_vat_20() -> VatRate:
    """Taux de TVA standard réutilisable pour les objets Henri."""
    return VatRate(code=1, rate=20.0, label="TVA 20%", wpwc_slug="standard")


@pytest.fixture
def book_product(standard_vat_rate: VatRate) -> GeneralObjects: #pylint: disable=W0621
    """Produit de type livre réutilisable dans les tests Woo."""
    product = GeneralObjects(
        supplier_id=1,
        general_object_type="book",
        ean13="9781234567890",
        name="Produit test",
        description="Description produit",
    )
    product.prices = [ObjectPrices(price=Decimal("19.99"), vat_rate=standard_vat_rate)]
    return product


@pytest.fixture
def henri_book_product(henri_vat_20: VatRate) -> GeneralObjects: #pylint: disable=W0621
    """Produit métier type livre réutilisable pour les tests Henri."""
    obj = GeneralObjects(
        supplier_id=1,
        general_object_type="book",
        ean13="9781234567890",
        name="Produit Henri",
        description="Description produit Henri",
    )
    obj.prices = [ObjectPrices(price=Decimal("19.99"), vat_rate=henri_vat_20)]
    return obj


@pytest.fixture
def woo_book_product() -> GeneralObjects:
    """Produit WooCommerce de référence pour les payloads de commande."""
    vat_rate = VatRate(code=1, rate=20.0, label="TVA 20%", wpwc_slug="standard")
    product = GeneralObjects(
        id=99,
        supplier_id=1,
        general_object_type="book",
        ean13="9781234567890",
        name="Commande test",
        description="Desc",
        wpwc_id=150,
    )
    product.prices = [ObjectPrices(price=Decimal("15.00"), vat_rate=vat_rate)]
    return product


@pytest.fixture
def tags(
    db_session_main: Session,  # pylint: disable=redefined-outer-name, unused-argument
) -> list[Tags]:  # pylint: disable=redefined-outer-name
    """Fixture pour créer des tags de test."""
    created_tags = [  # pylint: disable=redefined-outer-name
        Tags(name="Tag1", description="Description du Tag1"),
        Tags(name="Tag2", description="Description du Tag2"),
        Tags(name="Tag3", description="Description du Tag3"),
    ]
    db_session_main.add_all(created_tags)
    db_session_main.flush()
    return created_tags


@pytest.fixture
def book_object(
    db_session_main: Session,  # pylint: disable=redefined-outer-name, unused-argument
    supplier: Suppliers,
    tags: list[Tags],  # pylint: disable=redefined-outer-name, unused-argument
) -> Books:  # pylint: disable=redefined-outer-name
    """Fixture pour créer un objet de type livre."""
    general_object = GeneralObjects(  # pylint: disable=redefined-outer-name
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
        general_object_id=general_object.id,
        semistructured_data={"key": "value"},
    )
    media_dict: Dict[str, Any] = {
        "general_object_id": general_object.id,
        "file_type": "image/jpeg",
        "alt_text": "An image showing a test object",
        "file_link": "http://example.com/test_image.jpg",
        "is_principal": True,
    }
    media = MediaFiles.from_dict(media_dict)
    db_session_main.add_all(object_tags)
    db_session_main.add(meta)
    db_session_main.add(media)
    db_session_main.commit()
    return general_object


@pytest.fixture
def general_object(
    db_session_main: Session,  # pylint: disable=redefined-outer-name, unused-argument
    supplier: Suppliers,
) -> GeneralObjects:  # pylint: disable=redefined-outer-name
    """Fixture pour créer un objet générique de test."""
    obj = GeneralObjects(
        supplier_id=supplier.id,
        general_object_type="generic",
        ean13="9789876543210",
        name="Test Generic Object",
        description="This is a generic test object.",
        price=29.99,
    )
    db_session_main.add(obj)
    db_session_main.commit()
    return obj
