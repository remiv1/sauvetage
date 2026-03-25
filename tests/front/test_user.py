"""Tests pour les routes de l'utilisateur."""

import pytest   # pylint: disable=unused-import
from tests.fixtures.f_users import TEST_PASSWORD  # pylint: disable=unused-import, redefined-outer-name

# +================================================================================================+
# |                          Gestion des tests de routes                                           |
# +================================================================================================+

REDIRECTION = "<!doctype html>\n<html lang=en>\n<title>Redirecting...</"
HOME_PAGE = "<!DOCTYPE html>\n<html lang=\"fr\">\n<head>\n"
FORBIDEN = "<!doctype html>\n<html lang=en>\n<title>403 Forbidden"


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
    assert user.nb_failed_logins == 4
    assert user.is_locked is True


def test_register(client,    # pylint: disable=unused-argument
             authenticated_client,    # pylint: disable=unused-argument
             authenticated_client_compta,    # pylint: disable=unused-argument
             fastapi_test_client,    # pylint: disable=unused-argument
             patch_requests_to_fastapi):    # pylint: disable=unused-argument
    """Test de la page de register."""
    response_get = client.get("/user/register")

    assert response_get.status_code == 302
    assert response_get.text.startswith(REDIRECTION)

    response_get_2 = authenticated_client.get("/user/register")
    assert response_get_2.status_code == 200
    assert response_get_2.text.startswith(HOME_PAGE)

    response_get_3 = authenticated_client_compta.get("/user/register")
    assert response_get_3.status_code == 403
    assert response_get_3.text.startswith(FORBIDEN)

    response_post_1 = authenticated_client_compta.post("/user/register",
                                                     data={
                                                         "username": "newuser",
                                                         "email": "newuser@example.com",
                                                         "password": "newpassword",
                                                         "permissions": ["1", "2"],
                                                     },
                                                     follow_redirects=True)
    assert response_post_1.status_code == 403
    assert response_post_1.text.startswith(FORBIDEN)

    response_post_2 = authenticated_client.post("/user/register",
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
            authenticated_client,    # pylint: disable=unused-argument
            authenticated_client_compta,):    # pylint: disable=unused-argument
    """Test de la page de logout."""
    response_get = client.get("/user/logout")
    response_get_2 = authenticated_client.get("/user/logout", follow_redirects=True)
    response_get_3 = authenticated_client_compta.get("/user/logout", follow_redirects=True)
    assert response_get.status_code // 100 == 3
    assert response_get_2.status_code // 100 == 2
    assert response_get_3.status_code // 100 == 2


def test_chg_pwd(client,    # pylint: disable=unused-argument
             authenticated_client,    # pylint: disable=unused-argument
             authenticated_client_compta,    # pylint: disable=unused-argument
             fastapi_test_client,    # pylint: disable=unused-argument
             patch_requests_to_fastapi,    # pylint: disable=unused-argument
             make_user):    # pylint: disable=unused-argument
    """Test de la page de changement de mot de passe."""
    user = make_user()
    user_compta = make_user(username="comptauser", email="comptauser@example.com")
    response_get = client.get(f"/user/change-password/{user.username}")
    response_get_2 = authenticated_client.get(f"/user/change-password/{user.username}")
    response_get_3 = authenticated_client_compta.get(
                                        f"/user/change-password/{user_compta.username}")
    assert response_get.status_code // 100 == 3
    assert response_get_2.status_code // 100 == 2
    assert response_get_3.status_code // 100 == 2

    response_post_1 = client.post(f"/user/change-password/{user.username}",
                                data={
                                    "old_password": TEST_PASSWORD,
                                    "new_password": "newpassword",
                                    "new_password_confirm": "newpassword",
                                },
                                follow_redirects=True)
    response_post_2 = authenticated_client.post(f"/user/change-password/{user.username}",
                                                data={
                                                    "old_password": TEST_PASSWORD,
                                                    "new_password": "newpassword",
                                                    "new_password_confirm": "newpassword",
                                                },
                                                follow_redirects=True)
    response_post_3 = authenticated_client_compta.post(
                                                f"/user/change-password/{user_compta.username}",
                                                data={
                                                    "old_password": TEST_PASSWORD,
                                                    "new_password": "newpassword",
                                                    "new_password_confirm": "newpassword",
                                                },
                                                follow_redirects=True)
    response_post_4 = authenticated_client.post("/user/change-password/testuser",
                                                data={
                                                    "old_password": "wrongpassword",
                                                    "new_password": "newpassword",
                                                    "new_password_confirm": "newpassword",
                                                },
                                                follow_redirects=True)
    # Le changement de mot de passe doit réussir même sans être connecté
    assert response_post_1.status_code // 100 == 2
    assert response_post_2.status_code // 100 == 2
    assert response_post_3.status_code // 100 == 2
    assert response_post_4.status_code // 100 == 2


def test_modify(client,    # pylint: disable=unused-argument
             make_user,    # pylint: disable=unused-argument
             authenticated_client,    # pylint: disable=unused-argument
             authenticated_client_compta,    # pylint: disable=unused-argument
             fastapi_test_client,    # pylint: disable=unused-argument
             patch_requests_to_fastapi):    # pylint: disable=unused-argument
    """Test de la page de modification d'utilisateur."""
    user = make_user(username="testuser", email="testuser@example.com")
    user_compta = make_user(username="comptauser", email="comptauser@example.com")
    response_get = client.get(f"/user/modify/{user.username}")
    response_get_2 = authenticated_client.get(f"/user/modify/{user.username}")
    response_get_3 = authenticated_client_compta.get(f"/user/modify/{user_compta.username}")
    assert response_get.status_code // 100 == 3
    assert response_get_2.status_code // 100 == 2
    assert response_get_3.status_code // 100 == 4

    response_post_1 = client.post(f"/user/modify/{user.username}",
                                data={
                                    "username": "testuser",
                                    "email": "testuser@example.com",
                                    "permissions": "admin"
                                }, follow_redirects=True)
    response_post_2 = authenticated_client.post(f"/user/modify/{user.username}",
                                                data={
                                                    "username": "testuser",
                                                    "email": "testuser@example.com",
                                                    "permissions": "1"
                                                }, follow_redirects=True)
    response_post_3 = authenticated_client.post(f"/user/modify/{user_compta.username}",
                                                data={
                                                    "username": "comptauser",
                                                    "email": "comptauser2@example.com",
                                                    "permissions": "12"
                                                }, follow_redirects=True)
    response_post_4 = authenticated_client_compta.post(f"/user/modify/{user.username}",
                                                data={
                                                    "username": "testuser",
                                                    "email": "testuser2@example.com",
                                                    "permissions": "12"
                                                }, follow_redirects=True)
    response_post_5 = authenticated_client_compta.post(f"/user/modify/{user_compta.username}",
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
