"""Configuration pytest pour les tests front."""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


# Charger les variables d'environnement au niveau du module
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

# Override test database URLs BEFORE Flask import (MUST use direct assignment, not setdefault)
# This ensures Flask uses localhost:5433 for tests instead of production db-main:5432
# Credentials are loaded from .env files above, making tests idempotent
main_pwd = os.environ.get("POSTGRES_PASSWORD_APP")
secure_pwd = os.environ.get("POSTGRES_PASSWORD_SECURE")
if main_pwd and secure_pwd:
    os.environ["DATABASE_URL"] = f"postgresql://app:{main_pwd}@localhost:5433/sauvetage_main"
    os.environ["SECURE_DATABASE_URL"] = f"postgresql://secure:{secure_pwd}" + \
                                            "@localhost:5433/sauvetage_secure"


# Lazy import of Flask app - deferred until after patching
_flask_app = None   # pylint: disable=invalid-name


def get_flask_app():
    """Lazy loader for Flask app to ensure patches are applied first."""
    global _flask_app   # pylint: disable=global-statement
    if _flask_app is None:
        from app_front.main import app  # pylint: disable=import-outside-toplevel, redefined-outer-name
        _flask_app = app
    return _flask_app


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


@pytest.fixture
def app():
    """Fixture pour créer l'application Flask pour les tests."""
    flask_app = get_flask_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):    # pylint: disable=redefined-outer-name, unused-argument
    """Fixture pour créer un test client Flask."""
    app.config["WTF_CSRF_ENABLED"] = False  # Désactiver CSRF pour les tests
    return app.test_client()


@pytest.fixture
def authenticated_client(client):   # pylint: disable=redefined-outer-name, unused-argument
    """Fixture pour créer un client authentifié avec une session utilisateur."""
    # Utiliser session_transaction pour définir la session de test
    with client.session_transaction() as sess:
        sess["user_id"] = "test-user-123"
        sess["username"] = "testuser"
        sess["email"] = "test@example.com"
        sess["permissions"] = "123456789"  # Tous les niveaux de permission
        sess["is_logged_in"] = True

    return client
