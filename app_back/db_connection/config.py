"""Module de configuration pour la connexion à la base de données sécurisée des utilisateurs."""

from os import getenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SECURE_DATABASE_URL = getenv(
    "DATABASE_SECURE_URL",
    "postgresql://app:pwd@db-secure:5432/sauvetage_secure"
)

def get_secure_session():
    """Crée une session SQLAlchemy pour la base de données sécurisée des utilisateurs."""

    engine = create_engine(
        SECURE_DATABASE_URL,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600
    )
    _session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
    return _session()
