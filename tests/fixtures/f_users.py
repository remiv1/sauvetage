"""Fixtures pour les tests liés aux utilisateurs."""

import pytest
from sqlalchemy.orm import Session
from db_models.objects import Users, UsersPasswords
from tests.fixtures.db_fixture import (  # pylint: disable=unused-import # type : ignore
    db_session_main,  # pylint: disable=unused-import # type : ignore
    engine,  # pylint: disable=unused-import # type : ignore
)  # pylint: disable=unused-import # type : ignore

FAKE_P_HASH = "pbkdf2:sha256:150000$test_salt$test_hash"

@pytest.fixture
def user(
    db_session_users: Session,  # pylint: disable=redefined-outer-name
    patch_requests_to_fastapi,  # pylint: disable=redefined-outer-name, unused-argument
) -> Users:  # pylint: disable=redefined-outer-name
    """Fixture pour créer un utilisateur de test."""
    user = Users(  # pylint: disable=redefined-outer-name
        username="Utilisateur Test",
        email="test@test.fr",
        permissions="9",
    )
    db_session_users.add(user)
    db_session_users.flush()
    password = UsersPasswords(
        user_id=user.id,
        password_hash=FAKE_P_HASH,
    )
    db_session_users.add(password)
    db_session_users.flush()
    return user
