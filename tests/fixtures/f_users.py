"""Fixtures pour les tests liés aux utilisateurs."""

import pytest
from sqlalchemy.orm import Session
from db_models.objects import Users, UsersPasswords
from db_models.security.secur_sauv import PwdHasher
from tests.fixtures.db_fixture import (  # pylint: disable=unused-import # type : ignore
    db_session_main,  # pylint: disable=unused-import # type : ignore
    engine,  # pylint: disable=unused-import # type : ignore
)  # pylint: disable=unused-import # type : ignore

# Mot de passe clair de test
TEST_PASSWORD = "test_password_123"
FAKE_P_HASH = PwdHasher().hash(TEST_PASSWORD)

@pytest.fixture
def make_user(
    db_session_users_shared: Session,
    patch_requests_to_fastapi,  # pylint: disable=redefined-outer-name, unused-argument
):
    """Factory pour créer des utilisateurs de test paramétrables."""

    def _create_user(
        username="Utilisateur Test",
        email="test@test.fr",
        permissions="9",
        password_hash=FAKE_P_HASH,
    ):
        user_to_create = Users(
            username=username,
            email=email,
            permissions=permissions,
        )
        db_session_users_shared.add(user_to_create)
        db_session_users_shared.flush()

        password = UsersPasswords(
            user_id=user_to_create.id,
            password_hash=password_hash,
        )
        db_session_users_shared.add(password)
        db_session_users_shared.flush()

        return user_to_create

    return _create_user


@pytest.fixture
def make_client(app):
    """Factory pour créer un client Flask avec session personnalisée."""
    app.config["WTF_CSRF_ENABLED"] = False

    def _create_client(
        user_id="test-user-123",
        username="testuser",
        email="test@example.com",
        permissions="123456789",
        is_logged_in=True,
    ):
        client_instance = app.test_client()

        with client_instance.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["username"] = username
            sess["email"] = email
            sess["permissions"] = permissions
            sess["is_logged_in"] = is_logged_in

        return client_instance

    return _create_client


@pytest.fixture
def client(app):    # pylint: disable=redefined-outer-name, unused-argument
    """Fixture pour créer un test client Flask non authentifié."""
    app.config["WTF_CSRF_ENABLED"] = False  # Désactiver CSRF pour les tests
    return app.test_client()


@pytest.fixture
def client_all(make_client):   # pylint: disable=redefined-outer-name, unused-argument
    """Fixture pour créer un client authentifié avec une session utilisateur."""
    return make_client(permissions="123456789")


@pytest.fixture
def client_admin(make_client):   # pylint: disable=redefined-outer-name, unused-argument
    """Fixture pour créer un client authentifié avec des permissions d'admin."""
    return make_client(permissions="1")


@pytest.fixture
def client_compta(make_client):   # pylint: disable=redefined-outer-name, unused-argument
    """Fixture pour créer un client authentifié avec des permissions compta."""
    return make_client(permissions="2")


@pytest.fixture
def client_commercial(make_client):   # pylint: disable=redefined-outer-name, unused-argument
    """Fixture pour créer un client authentifié avec des permissions commercial."""
    return make_client(permissions="3")


@pytest.fixture
def client_logistique(make_client):   # pylint: disable=redefined-outer-name, unused-argument
    """Fixture pour créer un client authentifié avec des permissions logistique."""
    return make_client(permissions="4")


@pytest.fixture
def client_support(make_client):   # pylint: disable=redefined-outer-name, unused-argument
    """Fixture pour créer un client authentifié avec des permissions support."""
    return make_client(permissions="5")


@pytest.fixture
def client_informatique(make_client):   # pylint: disable=redefined-outer-name, unused-argument
    """Fixture pour créer un client authentifié avec des permissions informatique."""
    return make_client(permissions="6")


@pytest.fixture
def client_rh(make_client):   # pylint: disable=redefined-outer-name, unused-argument
    """Fixture pour créer un client authentifié avec des permissions RH."""
    return make_client(permissions="7")


@pytest.fixture
def client_direction(make_client):   # pylint: disable=redefined-outer-name, unused-argument
    """Fixture pour créer un client authentifié avec des permissions direction."""
    return make_client(permissions="8")


@pytest.fixture
def client_super_admin(make_client):   # pylint: disable=redefined-outer-name, unused-argument
    """Fixture pour créer un client authentifié avec des permissions super admin."""
    return make_client(permissions="9")
