"""Module de fixture pour la base de données de test (PostgreSQL).

Cette fixture se connecte à la base de test créée par le script de tests
(`tests/run_db_test_up.sh`). Les variables de connexion sont lues depuis
`databases/main/.env.db_main`.

On expose désormais deux engines / deux sessions dédiées:
- `db_session_main` : pour la base principale (`POSTGRES_DB_MAIN`) — utilise
  l'utilisateur app par défaut.
- `db_session_users` : pour la base des utilisateurs (`POSTGRES_DB_USERS`) —
  utilise l'utilisateur de migration (migr) par défaut.

    (Exporte uniquement `db_session_main` et `db_session_users`.)
"""

from typing import Generator
import os
import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.engine import Engine
from db_models import WorkingBase, SecureBase  # type: ignore # pylint: disable=unused-import
from db_models.objects import (  # type: ignore # pylint: disable=unused-import
    Order,
    OrderLine,  # pylint: disable=unused-import# type: ignore
    GeneralObjects,
    Books,
    OtherObjects,
    MediaFiles,
    ObjMetadatas,
    Tags,
    ObjectTags,  # type: ignore # pylint: disable=unused-import
    Shipment,  # type: ignore # pylint: disable=unused-import
    InventoryMovements,  # type: ignore # pylint: disable=unused-import
    Invoice,  # type: ignore # pylint: disable=unused-import
    Suppliers,  # type: ignore # pylint: disable=unused-import
    Users,  # type: ignore # pylint: disable=unused-import
)  # type: ignore # pylint: disable=unused-import


def _load_env() -> None:
    """Charger le fichier canonical `.env.db_main` si présent."""
    join = os.path.join
    dirname = os.path.dirname
    abspath = os.path.abspath
    dotenv_file_path = join(
        abspath(join(dirname(__file__), "..", "..")),
        "databases",
        "main",
        ".env.db_main",
    )
    if os.path.exists(dotenv_file_path):
        load_dotenv(dotenv_file_path)


def _make_engine(dbname: str, username: str, password: str, port: str) -> Engine:
    """Créer un engine en connectant toujours sur localhost et le port fourni.

    La configuration précédente avec détection de nom de service est inutile
    pour les tests locaux — nous simplifions ici.
    """
    host = "localhost"
    url = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{dbname}"
    return create_engine(url, pool_pre_ping=True, future=True)


def _session_scope(engine_to_use: Engine) -> Generator[Session, None, None]:
    connection = engine_to_use.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    local_session = scoped_session(session_factory)
    session = local_session()
    try:
        yield session
    finally:
        try:
            session.close()
        finally:
            # rollback the outer transaction opened on the connection
            transaction.rollback()
            connection.close()


@pytest.fixture(scope="session")
def engine_main() -> Engine:
    """Engine pour `POSTGRES_DB_MAIN` (utilisateur app)."""
    _load_env()
    port = "5433"
    db = os.environ.get("POSTGRES_DB_MAIN", "sauvetage_main")
    user = os.environ.get("POSTGRES_USER_APP", "app")
    pw = os.environ.get("POSTGRES_PASSWORD_APP", "")
    return _make_engine(db, user, pw, port)


@pytest.fixture(scope="session")
def engine_users() -> Engine:
    """Engine pour `POSTGRES_DB_USERS` (utilisateur migr)."""
    _load_env()
    port = "5433"
    db = os.environ.get("POSTGRES_DB_USERS", "sauvetage_users")
    user = os.environ.get("POSTGRES_USER_MIGR", "migr")
    pw = os.environ.get("POSTGRES_PASSWORD_MIGR", "")
    return _make_engine(db, user, pw, port)


@pytest.fixture(scope="session")
def engine(
    engine_main: Engine, engine_users: Engine  # pylint: disable=redefined-outer-name
) -> Engine:  # pylint: disable=redefined-outer-name
    """Détecte et renvoie l'engine qui contient `auth_schema.users`.

    Essaie `engine_main` puis `engine_users`.
    """
    try:
        with engine_main.connect() as conn:
            if conn.execute(text("SELECT to_regclass('auth_schema.users')")).scalar():
                return engine_main
    except Exception:  # pylint: disable=broad-except
        pass
    try:
        with engine_users.connect() as conn:
            if conn.execute(text("SELECT to_regclass('auth_schema.users')")).scalar():
                return engine_users
    except Exception:  # pylint: disable=broad-except
        pass
    return engine_main


@pytest.fixture(scope="function")
def db_session_main(
    engine_main: Engine,
    engine_users: Engine,  # pylint: disable=redefined-outer-name, unused-argument
) -> Generator[
    Session, None, None
]:  # pylint: disable=redefined-outer-name, disable=unused-argument
    """Session pour la DB `main` (transaction rollbackée par test).

    Si la table `auth_schema.users` est absente dans `engine_main`, on bascule
    vers `engine_users` (cas où les migrations users ont été appliquées dans
    une base séparée).
    """
    # Utiliser toujours `engine_main` pour la session principale. Si vous
    # avez besoin d'accéder à la DB users, utilisez la fixture `db_session_users`.
    yield from _session_scope(engine_main)


@pytest.fixture(scope="function")
def db_session_users(
    engine_users: Engine,  # pylint: disable=redefined-outer-name, unused-argument
) -> Generator[Session, None, None]:  # pylint: disable=redefined-outer-name
    """Session pour la DB `users` (transaction rollbackée par test)."""
    yield from _session_scope(engine_users)
