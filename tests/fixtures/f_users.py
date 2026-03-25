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
