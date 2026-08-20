"""Tests pour les routes de l'utilisateur."""

from datetime import datetime, timedelta, timezone

import pytest   # pylint: disable=unused-import
import requests
from sqlalchemy import select
from sqlalchemy.orm import Session
from db_models.objects import Users, UserSession
from db_models.repositories.user_session import UserSessionsRepository
from tests.fixtures.f_users import TEST_PASSWORD  # pylint: disable=unused-import, redefined-outer-name

# +================================================================================================+
# |                          Gestion des tests de routes                                           |
# +================================================================================================+

REDIRECTION = "<!doctype html>\n<html lang=en>\n<title>Redirecting...</"
HOME_PAGE = "<!DOCTYPE html>\n<html lang=\"fr\">\n<head>\n"
FORBIDEN = HOME_PAGE


def login_user(client, username: str, password: str = TEST_PASSWORD) -> str:
    """Connecte un utilisateur de test et retourne son jeton de session."""
    response = client.post(
        "/user/login", data={"username": username, "password": password}
    )
    assert response.status_code == 302
    with client.session_transaction() as current_session:
        return current_session["auth_token"]


def get_user_session(db_session: Session, session_token: str) -> UserSession:
    """Retourne la session persistée correspondant au jeton de test."""
    session = db_session.execute(
        select(UserSession).where(
            UserSession.token_hash == UserSessionsRepository._hash_token(session_token)
        )
    ).scalar_one()
    return session


def test_login(client, make_user, fastapi_test_client, patch_requests_to_fastapi):    # pylint: disable=unused-argument
    """Test de la page de login."""
    user = make_user()
    response_get = client.get("/user/login")
    assert response_get.status_code == 200
    assert response_get.text.startswith(HOME_PAGE)

    response_1 = client.post("/user/login",
                          data={"username": user.username, "password": TEST_PASSWORD},
                          follow_redirects=True)
    response_2 = client.post("/user/login",
                          data={"username": user.username, "password": "wrongpassword"},
                          follow_redirects=True)
    assert response_1.status_code == 200
    assert response_1.text.startswith(HOME_PAGE)
    assert response_2.status_code == 200
    assert user.nb_failed_logins == 1

    response_3 = client.post("/user/login",
                          data={"username": user.username, "password": TEST_PASSWORD},
                          follow_redirects=True)
    assert response_3.status_code == 200
    assert user.nb_failed_logins == 0

    for _ in range(4):
        response_locked = client.post("/user/login",
                                  data={"username": user.username, "password": "wrongpassword"},
                                  follow_redirects=True)
    assert response_locked.status_code == 200   # type: ignore
    assert user.nb_failed_logins == 3
    assert user.is_locked is True


def test_register(client,    # pylint: disable=unused-argument
             client_all,    # pylint: disable=unused-argument
             client_compta,    # pylint: disable=unused-argument
             fastapi_test_client,    # pylint: disable=unused-argument
             patch_requests_to_fastapi):    # pylint: disable=unused-argument
    """Test de la page de register."""
    response_get = client.get("/user/register")

    assert response_get.status_code == 302
    assert response_get.text.startswith(REDIRECTION)

    response_get_2 = client_all.get("/user/register")
    assert response_get_2.status_code == 200
    assert response_get_2.text.startswith(HOME_PAGE)

    response_get_3 = client_compta.get("/user/register")
    assert response_get_3.status_code == 403
    assert response_get_3.text.startswith(FORBIDEN)

    response_post_1 = client_compta.post("/user/register",
                                                     data={
                                                         "username": "newuser",
                                                         "email": "newuser@example.com",
                                                         "password": "newpassword",
                                                         "permissions": ["1", "2"],
                                                     },
                                                     follow_redirects=True)
    assert response_post_1.status_code == 403
    assert response_post_1.text.startswith(FORBIDEN)

    response_post_2 = client_all.post("/user/register",
                                             data={
                                                 "username": "newuser",
                                                 "email": "newuser@example.com",
                                                 "password": "newpassword",
                                                 "permissions": ["1", "2"],
                                             },
                                             follow_redirects=True)
    assert response_post_2.status_code == 200
    assert response_post_2.text.startswith(HOME_PAGE)


def test_logout(client,    # pylint: disable=unused-argument
            client_all,    # pylint: disable=unused-argument
            client_compta,):    # pylint: disable=unused-argument
    """Test de la page de logout."""
    response_get = client.get("/user/logout")
    response_get_2 = client_all.get("/user/logout", follow_redirects=True)
    response_get_3 = client_compta.get("/user/logout", follow_redirects=True)
    assert response_get.status_code // 100 == 3
    assert response_get_2.status_code // 100 == 2
    assert response_get_3.status_code // 100 == 2


def test_logout_revokes_server_session(
    client_all,
    fastapi_test_client,
):
    """La déconnexion doit invalider le jeton côté serveur."""
    with client_all.session_transaction() as current_session:
        session_token = current_session["auth_token"]

    response = client_all.get("/user/logout", follow_redirects=True)
    validation = fastapi_test_client.post(
        "/api/v1/users/validate-session",
        json={"session_token": session_token},
    )

    assert response.status_code == 200
    assert validation.status_code == 200
    assert validation.json() == {"valid": False}


def test_revoked_session_redirects_on_next_protected_request(
    client_all,
    fastapi_test_client,
):
    """Une session révoquée est retirée du navigateur à la requête suivante."""
    with client_all.session_transaction() as current_session:
        session_token = current_session["auth_token"]
    fastapi_test_client.post("/api/v1/users/logout", json={"session_token": session_token})

    response = client_all.get("/user/register")

    assert response.status_code == 302
    with client_all.session_transaction() as current_session:
        assert "auth_token" not in current_session


@pytest.mark.parametrize("attribute", ["is_active", "is_locked"])
def test_disabled_or_locked_account_invalidates_existing_session(
    client,
    make_user,
    db_session_users_shared,
    attribute,
):
    """Un compte désactivé ou verrouillé perd immédiatement sa session existante."""
    user = make_user(username=f"session-{attribute}", email=f"{attribute}@example.com")
    login_user(client, user.username)
    setattr(user, attribute, False if attribute == "is_active" else True)
    db_session_users_shared.commit()

    response = client.get("/user/register")

    assert response.status_code == 302
    with client.session_transaction() as current_session:
        assert "auth_token" not in current_session


def test_permissions_are_refreshed_before_authorization(
    client_all,
    db_session_users_shared,
):
    """Les permissions modifiées côté serveur sont utilisées à la requête suivante."""
    with client_all.session_transaction() as current_session:
        username = current_session["username"]
    user = db_session_users_shared.execute(
        select(Users).where(Users.username == username)
    ).scalar_one()
    user.permissions = "2"
    db_session_users_shared.commit()

    response = client_all.get("/user/register")

    assert response.status_code == 403
    with client_all.session_transaction() as current_session:
        assert current_session["permissions"] == "2"


@pytest.mark.parametrize("field", ["expires_at", "last_seen_at"])
def test_expired_or_idle_session_is_rejected(
    client,
    make_user,
    db_session_users_shared,
    field,
):
    """Les expirations absolue et d'inactivité invalident une session."""
    user = make_user(username=f"expired-{field}", email=f"{field}@example.com")
    session_token = login_user(client, user.username)
    user_session = get_user_session(db_session_users_shared, session_token)
    setattr(user_session, field, datetime.now(timezone.utc) - timedelta(minutes=31))
    db_session_users_shared.commit()

    response = client.get("/user/register")

    assert response.status_code == 302


def test_authentication_backend_failure_returns_service_unavailable(
    client_all,
    monkeypatch,
):
    """Une panne du service d'authentification bloque les routes protégées."""
    def raise_connection_error(_session_token: str) -> dict:
        raise requests.ConnectionError("backend indisponible")

    monkeypatch.setattr("app_front.main.validate_session", raise_connection_error)

    response = client_all.get("/user/register")

    assert response.status_code == 503


def test_login_creates_distinct_opaque_server_sessions(
    app,
    client,
    make_user,
    db_session_users_shared,
):
    """Chaque connexion produit un jeton unique, jamais stocké en clair."""
    user = make_user(username="opaque-user", email="opaque@example.com")
    second_client = app.test_client()
    first_token = login_user(client, user.username)
    second_token = login_user(second_client, user.username)
    persisted_sessions = db_session_users_shared.execute(
        select(UserSession).where(UserSession.user_id == user.id)
    ).scalars().all()

    assert first_token != second_token
    assert len(persisted_sessions) == 2
    assert all(
        session.token_hash not in (first_token, second_token) for session in persisted_sessions
    )
    assert all(len(session.token_hash) == 64 for session in persisted_sessions)


def test_change_password_requires_authenticated_owner_or_administrator(
    client,
    client_all,
    client_compta,
    make_user,
):
    """Seul le propriétaire ou un administrateur peut changer un mot de passe."""
    user = make_user()
    response_get = client.get(f"/user/change-password/{user.username}")
    response_get_2 = client_all.get(f"/user/change-password/{user.username}")
    assert response_get.status_code // 100 == 3
    assert response_get_2.status_code // 100 == 2

    response_forbidden = client_compta.post(
        f"/user/change-password/{user.username}",
        data={"new_password": "newpassword", "new_password_confirm": "newpassword"},
    )
    response_admin = client_all.post(
        f"/user/change-password/{user.username}",
        data={"new_password": "newpassword", "new_password_confirm": "newpassword"},
    )

    assert response_forbidden.status_code == 403
    assert response_admin.status_code == 302


@pytest.mark.parametrize("permissions", ["1", "9"])
def test_administrator_roles_can_reset_another_users_password(
    make_client,
    make_user,
    permissions,
):
    """Les rôles administrateur et super-administrateur réinitialisent un autre compte."""
    target = make_user(
        username=f"target-{permissions}", email=f"target-{permissions}@example.com"
    )
    administrator = make_client(
        username=f"administrator-{permissions}",
        email=f"administrator-{permissions}@example.com",
        permissions=permissions,
    )

    response = administrator.post(
        f"/user/change-password/{target.username}",
        data={"new_password": "administrator-reset", "new_password_confirm": "administrator-reset"},
    )

    assert response.status_code == 302


def test_password_change_revokes_server_sessions(
    client,
    app,
    make_user,
    fastapi_test_client,
    patch_requests_to_fastapi,  # pylint: disable=unused-argument
):
    """Un changement de mot de passe doit invalider les sessions existantes."""
    user = make_user(username="session-user", email="session-user@example.com")
    second_client = app.test_client()
    session_token = login_user(client, user.username)
    second_session_token = login_user(second_client, user.username)

    response = client.post(
        f"/user/change-password/{user.username}",
        data={
            "old_password": TEST_PASSWORD,
            "new_password": "new_password_456",
            "new_password_confirm": "new_password_456",
        },
        follow_redirects=True,
    )
    validation = fastapi_test_client.post(
        "/api/v1/users/validate-session",
        json={"session_token": session_token},
    )
    second_validation = fastapi_test_client.post(
        "/api/v1/users/validate-session",
        json={"session_token": second_session_token},
    )

    assert response.status_code == 200
    assert validation.status_code == 200
    assert validation.json() == {"valid": False}
    assert second_validation.status_code == 200
    assert second_validation.json() == {"valid": False}


def test_modify(client,    # pylint: disable=unused-argument
             make_user,    # pylint: disable=unused-argument
             client_all,    # pylint: disable=unused-argument
             client_compta,    # pylint: disable=unused-argument
             fastapi_test_client,    # pylint: disable=unused-argument
             patch_requests_to_fastapi):    # pylint: disable=unused-argument
    """Test de la page de modification d'utilisateur."""
    user = make_user(username="testuser", email="testuser@example.com")
    user_compta = make_user(username="comptauser", email="comptauser@example.com")
    response_get = client.get(f"/user/modify/{user.username}")
    response_get_2 = client_all.get(f"/user/modify/{user.username}")
    response_get_3 = client_compta.get(f"/user/modify/{user_compta.username}")
    assert response_get.status_code // 100 == 3
    assert response_get_2.status_code // 100 == 2
    assert response_get_3.status_code // 100 == 4

    response_post_1 = client.post(f"/user/modify/{user.username}",
                                data={
                                    "username": "testuser",
                                    "email": "testuser@example.com",
                                    "permissions": "admin"
                                }, follow_redirects=True)
    response_post_2 = client_all.post(f"/user/modify/{user.username}",
                                                data={
                                                    "username": "testuser",
                                                    "email": "testuser@example.com",
                                                    "permissions": "1"
                                                }, follow_redirects=True)
    response_post_3 = client_all.post(f"/user/modify/{user_compta.username}",
                                                data={
                                                    "username": "comptauser",
                                                    "email": "comptauser2@example.com",
                                                    "permissions": "12"
                                                }, follow_redirects=True)
    response_post_4 = client_compta.post(f"/user/modify/{user.username}",
                                                data={
                                                    "username": "testuser",
                                                    "email": "testuser2@example.com",
                                                    "permissions": "12"
                                                }, follow_redirects=True)
    response_post_5 = client_compta.post(f"/user/modify/{user_compta.username}",
                                                data={
                                                    "username": "comptauser",
                                                    "email": "comptauser2@example.com",
                                                    "permissions": "12"
                                                }, follow_redirects=True)
    assert response_post_1.status_code // 100 == 2
    assert response_post_2.status_code // 100 == 2
    assert response_post_3.status_code // 100 == 2
    assert response_post_4.status_code // 100 == 4
    assert response_post_5.status_code // 100 == 4
