"""Module de configuration pour la connexion aux bases de données."""

from contextlib import contextmanager
from os import getenv
from urllib.parse import quote
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError  # pylint: disable=unused-import


def _build_database_url(user: str, password: str, host: str, port: str, db_name: str) -> str:
    """Construit une URL PostgreSQL correcte depuis les variables d'environnement."""
    return (
        f"postgresql://{user}:{quote(password, safe='')}@{host}:{port}/{db_name}"
    )


SECURE_DATABASE_URL = (
    getenv("DATABASE_SECURE_URL")
    or getenv("SECURE_DATABASE_URL")
    or _build_database_url(
        getenv("POSTGRES_USER_SECURE", "secure"),
        getenv("POSTGRES_PASSWORD_SECURE", "pwd"),
        getenv("POSTGRES_HOST", "db-main"),
        getenv("POSTGRES_PORT", "5432"),
        getenv("POSTGRES_DB_USERS", "sauvetage_users"),
    )
)
DATABASE_URL = getenv("DATABASE_URL") or _build_database_url(
    getenv("POSTGRES_USER_APP", "app"),
    getenv("POSTGRES_PASSWORD_APP", "pwd"),
    getenv("POSTGRES_HOST", "db-main"),
    getenv("POSTGRES_PORT", "5432"),
    getenv("POSTGRES_DB_MAIN", "sauvetage_main"),
)

_engine_main = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
)
_SessionMain = sessionmaker(autocommit=False, autoflush=False, bind=_engine_main)   # pylint: disable=C0103

_engine_secure = create_engine(
    SECURE_DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=1800,
)
_SessionSecure = sessionmaker(autocommit=False, autoflush=False, bind=_engine_secure)   # pylint: disable=C0103


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
