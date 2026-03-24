"""Tests pour les routes de l'utilisateur."""

import pytest   # pylint: disable=unused-import
from tests.fixtures.f_users import FAKE_P_HASH  # pylint: disable=unused-import, redefined-outer-name

# +================================================================================================+
# |                          Gestion des tests de routes                                           |
# +================================================================================================+

def test_login(client, user):
    """Test de la page de login."""
    response_1 = client.get("/user/login",
                          data={"username": user.username, "password": FAKE_P_HASH})
    response_2 = client.get("/user/login",
                          data={"username": user.username, "password": "wrongpassword"})

    assert response_1.status_code == 200
    assert response_1.text.startswith("\n    <h1>Connexion</h1>\n")
    assert response_2.status_code == 200
    assert user.nb_failed_logins == 1
