"""Configuration pytest pour les tests front."""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

_fastapi_proxy = None   # pylint: disable=invalid-name

# ── 1. Charger les variables d'environnement AVANT tout import applicatif ──
env_file = Path(__file__).parent.parent.parent / "databases" / "logs" / ".env.db_logs"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file, override=True)

app_front_env = Path(__file__).parent.parent.parent / "app_front" / ".env.flask"
if app_front_env.exists():
    from dotenv import load_dotenv
    load_dotenv(app_front_env, override=True)

env_postgres = Path(__file__).parent.parent.parent / "databases" / "main" / ".env.db_main"
if env_postgres.exists():
    from dotenv import load_dotenv
    load_dotenv(env_postgres, override=True)

# ── 2. Override des URLs de connexion pour les tests (localhost:5433) ──
main_pwd = os.environ.get("POSTGRES_PASSWORD_APP")
secure_pwd = os.environ.get("POSTGRES_PASSWORD_SECURE")
db_users = os.environ.get("POSTGRES_DB_USERS", "sauvetage_users")
db_main = os.environ.get("POSTGRES_DB_MAIN", "sauvetage_main")
if main_pwd and secure_pwd:
    os.environ["DATABASE_URL"] = \
        f"postgresql://app:{main_pwd}@localhost:5433/{db_main}"
    os.environ["DATABASE_SECURE_URL"] = \
        f"postgresql://secure:{secure_pwd}@localhost:5433/{db_users}"

os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5433"

# ── 3. Désactiver les migrations AVANT tout import de app_back.main ──
import app_back.migration  # pylint: disable=wrong-import-position
app_back.migration.run_startup_tasks = lambda *a, **k: None

# ── 4. Importer config APRÈS le setup des env vars ──
from fastapi.testclient import TestClient  # pylint: disable=wrong-import-position, wrong-import-order
from app_back.db_connection import config  # pylint: disable=wrong-import-position
from app_front.config import db_conf  # pylint: disable=wrong-import-position

# ── 5. Forcer les URLs de test dans les variables module-level de config ──
#    Certaines routes (ex: exists_first) appellent get_secure_session() directement
#    sans dependency injection, donc les dependency_overrides ne suffisent pas.
if main_pwd and secure_pwd:
    config.DATABASE_URL = os.environ["DATABASE_URL"]
    config.SECURE_DATABASE_URL = os.environ["DATABASE_SECURE_URL"]


# Lazy import of Flask app - deferred until after patching
_flask_app = None   # pylint: disable=invalid-name
_fast_app = None    # pylint: disable=invalid-name


@pytest.fixture(autouse=True)
def disable_migrations():
    """Fixture (no-op) — les migrations sont déjà désactivées au niveau du module."""


class FakeLogger:
    """Fake logger pour les tests, remplace les méthodes de logging par des mocks."""
    def log(self, **kwargs):    # pylint: disable=unused-argument
        """Log une entrée (mock)."""
        return "fake"
    def log_user_action(self, **kwargs):    # pylint: disable=unused-argument
        """Log une action utilisateur (mock)."""
        return "fake"
    def log_client_event(self, **kwargs):    # pylint: disable=unused-argument
        """Log un événement client (mock)."""
        return "fake"
    def log_error(self, **kwargs):  # pylint: disable=unused-argument
        """Log une erreur (mock)."""
        return "fake"


@pytest.fixture(autouse=True)
def fake_mongo_logger(monkeypatch):
    """Fixture pour remplacer le logger MongoDB par un fake logger pendant les tests."""
    monkeypatch.setattr("logs.logger.get_logger", lambda: FakeLogger()) # pylint: disable=unnecessary-lambda


@pytest.fixture(scope="session", autouse=True)
def ensure_mongo_patches():
    """Patch MongoDB logger helpers before app import (no pre-import).

    Use unittest.mock.patch.start/stop so we don't require function-scoped
    fixtures like `monkeypatch` in a session-scoped fixture.
    """
    mock_instance = MagicMock()
    mock_instance.log = MagicMock()
    p1 = patch("logs.logger.MongoDBLogger", MagicMock(return_value=mock_instance))
    p2 = patch("logs.logger.get_logger", MagicMock(return_value=mock_instance))
    p1.start()
    p2.start()
    try:
        yield
    finally:
        p1.stop()
        p2.stop()


@pytest.fixture(autouse=True)
def patch_requests_to_fastapi():
    """Patch requests AVANT import Flask/FastAPI."""
    API_BASE = "http://app-back:8000"  # pylint: disable=invalid-name

    from requests.sessions import Session   # pylint: disable=import-outside-toplevel
    original_request = Session.request

    # Client créé à la demande si aucune instance proxy n'existe encore
    created_client = None

    def fake_request(self, method, url, **kwargs):
        nonlocal created_client
        global _fastapi_proxy   # pylint: disable=global-statement

        if url.startswith(API_BASE):
            # Créer un TestClient à la demande pour éviter la résolution DNS
            if _fastapi_proxy is None:  # pylint: disable=possibly-used-before-assignment
                try:
                    fastapp = get_fast_app()
                    client = TestClient(fastapp)
                    _fastapi_proxy = client
                    created_client = client
                except Exception:   # pylint: disable=broad-except
                    # Si on ne peut pas créer le proxy, retomber sur la requête normale
                    return original_request(self, method, url, **kwargs)

            path = url.replace(API_BASE, "")
            kwargs.pop("timeout", None)
            return _fastapi_proxy.request(method, path, **kwargs)

        return original_request(self, method, url, **kwargs)

    patcher = patch.object(Session, "request", new=fake_request)

    patcher.start()
    try:
        yield
    finally:
        patcher.stop()
        if created_client is not None:
            try:
                created_client.close()
            except Exception:   # pylint: disable=broad-except
                pass
            _fastapi_proxy = None


def get_flask_app():
    """Lazy loader for Flask app to ensure patches are applied first."""
    global _flask_app   # pylint: disable=global-statement
    if _flask_app is None:
        from app_front.main import app  # pylint: disable=import-outside-toplevel, redefined-outer-name
        _flask_app = app
    return _flask_app


def get_fast_app():
    """Getter for FastAPI app."""
    global _fast_app    # pylint: disable=global-statement
    if _fast_app is None:
        # Patcher les migrations AVANT l'import de app_back.main,
        # car run_startup_tasks() est appelé au niveau du module.
        app_back.migration.run_startup_tasks = lambda *a, **k: None
        from app_back.main import app as fastapi_app  # pylint: disable=import-outside-toplevel, redefined-outer-name
        _fast_app = fastapi_app
    return _fast_app


@pytest.fixture
def app():
    """Fixture pour créer l'application Flask pour les tests."""
    flask_app = get_flask_app()
    flask_app.config["TESTING"] = True
    return flask_app

_test_secure_session = None   # pylint: disable=invalid-name
_test_main_session = None     # pylint: disable=invalid-name


class SessionProxy:
    """Proxy pour récupérer la session test actuelle."""

    def __init__(self, session_type: str):
        self.session_type = session_type

    def __call__(self):
        """Retourner la session test du type spécifié."""
        if self.session_type == "secure":
            return _test_secure_session
        elif self.session_type == "main":
            return _test_main_session
        return None

    def __getattr__(self, name):
        """Déléguer les appels d'attribut à la session réelle."""
        session = self()
        if session is None:
            raise RuntimeError(f"Session {self.session_type} is None - fixture not initialized")
        return getattr(session, name)


@pytest.fixture(scope="function", autouse=True)
def init_test_sessions(db_session_main, db_session_users_shared, monkeypatch):
    """Fixture autouse qui initialise les sessions de test pour tous les tests."""
    global _test_secure_session, _test_main_session  # pylint: disable=global-statement

    # Always initialize the sessions
    _test_secure_session = db_session_users_shared
    _test_main_session = db_session_main

    # Patcher les fonctions get_secure_session et get_main_session
    # pour retourner les sessions de test lors d'appels directs
    monkeypatch.setattr(config, "get_secure_session", SessionProxy("secure"))
    monkeypatch.setattr(config, "get_main_session", SessionProxy("main"))
    monkeypatch.setattr(db_conf, "get_main_session", SessionProxy("main"))

    yield

    # Cleanup
    _test_secure_session = None
    _test_main_session = None


@pytest.fixture(scope="function")
def fastapi_test_client(db_session_main, db_session_users_shared):
    """Fixture pour créer un client de test FastAPI avec les sessions de test."""
    global _fastapi_proxy  # pylint: disable=global-statement

    def override_main():
        yield db_session_main

    def override_secure():
        yield db_session_users_shared

    fastapi_app = get_fast_app()
    fastapi_app.dependency_overrides[config.get_main_session] = override_main
    fastapi_app.dependency_overrides[config.get_secure_session] = override_secure

    with TestClient(fastapi_app) as client_fastapi:
        _fastapi_proxy = client_fastapi
        yield client_fastapi

    fastapi_app.dependency_overrides.clear()
