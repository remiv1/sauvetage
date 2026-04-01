"""Configuration de la base de données pour l'application Flask Sauvetage"""

from typing import Optional
from os import getenv
from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

DATABASE_URL = getenv(
    "DATABASE_URL", "postgresql://app:pwd@db-main:5432/sauvetage_main"
)
SECURE_DATABASE_URL = getenv(
    "SECURE_DATABASE_URL", "postgresql://app:pwd@db-secure:5432/sauvetage_secure"
)
MONGODB_URL = getenv("MONGODB_URL", "mongodb://app:pwd@db-logs:27017/sauvetage_logs")
MONGO_DB_NAME = getenv("MONGO_DB_LOGS", "sauvetage_logs")

_engine_main = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
)
_SessionMain = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=_engine_main))

_mongo_client: Optional[MongoClient] = None  # type: ignore


def get_main_session():
    """Retourne une session SQLAlchemy pour la base de données principale."""

    # Gestion des sessions pour les tests.
    if hasattr(current_app, "db_session_main"):
        return current_app.db_session_main  # pylint: disable=no-member # type: ignore
    return _SessionMain()


def get_mongo_db():
    """Retourne l'instance de la base de données MongoDB pour les logs."""
    global _mongo_client  # pylint: disable=global-statement
    try:
        if _mongo_client is None:
            _mongo_client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=3000)
        return _mongo_client[MONGO_DB_NAME]
    except ConnectionFailure:
        return None
