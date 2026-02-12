"""Tests unitaires pour les objets de la base de données."""

from typing import Dict, Any
import pytest
from pytest_mock import MockerFixture
from db_models.objects.users import Users, UsersPasswords

@pytest.fixture
def mock_session(mocker: MockerFixture):
    """Fixture pour créer une session de base de données simulée."""
    return mocker.Mock()

def test_user_to_dict():
    """Test de la méthode to_dict de la classe Users."""
    user = Users(
        id=1,
        username="testuser",
        email="test@user.fr",
        is_active=True,
        nb_failed_logins=0,
        is_locked=False,
        permissions="13"
    )
    user_dict = user.to_dict()
    assert user_dict["id"] == 1
    assert user_dict["username"] == "testuser"
    assert user_dict["email"] == "test@user.fr"
    assert user_dict["is_active"] is True
    assert user_dict["nb_failed_logins"] == 0
    assert user_dict["is_locked"] is False
    assert user_dict["permissions"] == "13"
    assert "created_at" not in user_dict
    assert "updated_at" not in user_dict

def test_user_from_dict():
    """Test de la méthode from_dict de la classe Users."""
    user_data: Dict[str, Any] = {
        "username": "testuser",
        "email": "test@user.fr",
        "is_active": True,
        "permissions": "13"
    }
    user = Users.from_dict(user_data)
    assert user.username == "testuser"
    assert user.email == "test@user.fr"
    assert user.is_active is True
    assert user.permissions == "13"

def test_user_password_to_dict():
    """Test de la méthode to_dict de la classe UsersPasswords."""
    user_password = UsersPasswords(
        id=1,
        user_id=1,
        password_hash="hashed_password"
    )
    user_password_dict = user_password.to_dict()
    assert user_password_dict["id"] == 1
    assert user_password_dict["user_id"] == 1
    assert "password_hash" not in user_password_dict
    assert "created_at" not in user_password_dict
    assert "updated_at" not in user_password_dict
