"""Fixtures pour les tests liés aux fournisseurs."""

import pytest
from sqlalchemy.orm import Session
from db_models.objects import Suppliers
from tests.fixtures.db_fixture import (  # pylint: disable=unused-import # type : ignore
    db_session_main,  # pylint: disable=unused-import # type : ignore
    engine,  # pylint: disable=unused-import # type : ignore
)  # pylint: disable=unused-import # type : ignore


@pytest.fixture
def supplier(
    db_session_main: Session,  # pylint: disable=redefined-outer-name
) -> Suppliers:  # pylint: disable=redefined-outer-name
    """Fixture pour créer un fournisseur de test."""
    supplier = Suppliers(  # pylint: disable=redefined-outer-name
        name="Fournisseur Test",
        gln13="1234567890123",
        contact_email="fournisseur@fournisseur.email",
        contact_phone="01 02 03 04 05",
    )
    db_session_main.add(supplier)
    db_session_main.flush()
    return supplier
