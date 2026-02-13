"""Module de fixture pour la base de données en SQLite"""

import os
import pytest
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from db_models import WorkingBase, SecureBase
from db_models.objects.orders import Order, OrderLine   # type: ignore # pylint: disable=unused-import
from db_models.objects.objects import (     # type: ignore # pylint: disable=unused-import
    GeneralObjects, Books, OtherObjects, MediaFiles, ObjMetadatas, Tags, ObjectTags     # pylint: disable=unused-import    # type: ignore 
)   # type: ignore # pylint: disable=unused-import
from db_models.objects.shipments import Shipment    # pylint: disable=unused-import    # type: ignore
from db_models.objects.inventory import InventoryMovements  # type: ignore # pylint: disable=unused-import
from db_models.objects.invoices import Invoice  # type: ignore # pylint: disable=unused-import
from db_models.objects.suppliers import Suppliers   # type: ignore # pylint: disable=unused-import
from db_models.objects.users import Users   # type: ignore # pylint: disable=unused-import


@pytest.fixture(scope="session")
def engine() -> Engine:
    """Crée un moteur SQLite en mémoire"""
    return create_engine("sqlite:///tests/fake_datas/test_db.sqlite")

@pytest.fixture(scope="function")
def db_session(engine: Engine) -> Session:  # pylint: disable=redefined-outer-name # type: ignore
    """Crée toutes les tables dans la base de test"""
    WorkingBase.metadata.create_all(engine)
    SecureBase.metadata.create_all(engine)
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    local_session = scoped_session(session_factory)  # pylint: disable=redefined-outer-name, invalid-name # type: ignore
    session = local_session()

    yield session  # Fournit la session au test # type: ignore

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope='session', autouse=True)
def cleanup_db():
    """Méthode de cleanup"""
    yield
    os.remove("tests/fake_datas/test_db.sqlite")
