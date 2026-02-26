"""Module de configuration pour la connexion aux bases de données."""

from os import getenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

SECURE_DATABASE_URL = getenv("DATABASE_SECURE_URL",
    "postgresql://app:pwd@db-secure:5432/sauvetage_secure")
DATABASE_URL = getenv("DATABASE_URL",
    "postgresql://app:pwd@db-main:5432/sauvetage_main")

def _make_session(url: str):
    """Fabrique une session SQLAlchemy pour une URL donnée."""
    engine = create_engine(
        url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600
    )
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_secure_session() -> Session:
    """Crée une session pour la base de données sécurisée (utilisateurs)."""
    return _make_session(SECURE_DATABASE_URL)()

def get_main_session() -> Session:
    """Crée une session pour la base de données principale (app)."""
    return _make_session(DATABASE_URL)()
