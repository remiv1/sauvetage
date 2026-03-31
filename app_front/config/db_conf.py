"""Configuration de la base de données pour l'application Flask Sauvetage"""

from os import getenv
from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

DATABASE_URL = getenv(
    "DATABASE_URL", "postgresql://app:pwd@db-main:5432/sauvetage_main"
)
SECURE_DATABASE_URL = getenv(
    "SECURE_DATABASE_URL", "postgresql://app:pwd@db-secure:5432/sauvetage_secure"
)
MONGODB_URL = getenv("MONGODB_URL", "mongodb://app:pwd@db-logs:27017/sauvetage_logs")

_engine_main = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
)
_SessionMain = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=_engine_main))


def get_main_session():
    """Retourne une session SQLAlchemy pour la base de données principale."""

    # Gestion des sessions pour les tests.
    if hasattr(current_app, "db_session_main"):
        return current_app.db_session_main  # pylint: disable=no-member # type: ignore
    return _SessionMain()
