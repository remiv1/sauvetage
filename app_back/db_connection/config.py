"""Module de configuration pour la connexion aux bases de données."""

from contextlib import contextmanager
from os import getenv
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError  # pylint: disable=unused-import

SECURE_DATABASE_URL = getenv(
    "DATABASE_SECURE_URL", "postgresql://app:pwd@db-secure:5432/sauvetage_secure"
)
DATABASE_URL = getenv(
    "DATABASE_URL", "postgresql://app:pwd@db-main:5432/sauvetage_main"
)

_engine_main = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
)
_SessionMain = sessionmaker(autocommit=False, autoflush=False, bind=_engine_main)

_engine_secure = create_engine(
    SECURE_DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=1800,
)
_SessionSecure = sessionmaker(autocommit=False, autoflush=False, bind=_engine_secure)


def get_secure_session() -> Generator[Session, None, None]:
    """Dépendance FastAPI pour la base de données sécurisée (utilisateurs)."""
    session = _SessionSecure()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_main_session() -> Generator[Session, None, None]:
    """Dépendance FastAPI pour la base de données principale (app)."""
    session = _SessionMain()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def secure_session_ctx() -> Generator[Session, None, None]:
    """Context manager pour la base de données sécurisée (code non-FastAPI)."""
    session = _SessionSecure()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def main_session_ctx() -> Generator[Session, None, None]:
    """Context manager pour la base de données principale (code non-FastAPI)."""
    session = _SessionMain()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
