"""Module de fixture pour la base de données en SQLite"""

import os
import pytest
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from db_models import WorkingBase, SecureBase

@pytest.fixture(scope="session")
def engine() -> Engine:
    """Crée un moteur SQLite en mémoire"""
    return create_engine("sqlite:///tests/fake_datas/test_db.sqlite")

@pytest.fixture(scope="function")
def db_session(engine: Engine) -> Session:
    """Crée toutes les tables dans la base de test"""
    WorkingBase.metadata.create_all(engine)
    SecureBase.metadata.create_all(engine)
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    Session = scoped_session(session_factory)
    session = Session()

    yield session  # Fournit la session au test

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope='session', autouse=True)
def cleanup_db():
    """Méthode de cleanup"""
    yield
    os.remove("tests/fake_datas/test_db.sqlite")
