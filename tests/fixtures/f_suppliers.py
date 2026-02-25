"""Fixtures pour les tests liés aux fournisseurs."""

import pytest
from sqlalchemy.orm import Session
from db_models.objects.suppliers import Suppliers
from tests.fixtures.sqlite_fixture import db_session, engine  # pylint: disable=unused-import # type : ignore

@pytest.fixture
def supplier(db_session: Session) -> Suppliers: # pylint: disable=redefined-outer-name
    """Fixture pour créer un fournisseur de test."""
    supplier = Suppliers(   # pylint: disable=redefined-outer-name
        name="Fournisseur Test",
        contact_email="fournisseur@fournisseur.email",
        contact_phone="01 02 03 04 05"
    )
    db_session.add(supplier)
    db_session.flush()
    return supplier