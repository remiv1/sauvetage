"""Tests pour le module commandes"""

import pytest

@pytest.mark.parametrize("client_fixture", [
    "client_direction",
    "client_logistique",
    "client_support",
    "client_admin",
])
def test_order_index_access(client_fixture, request, fastapi_test_client): # pylint: disable=unused-argument
    """Test d'accès à la page d'accueil du module commandes."""
    client = request.getfixturevalue(client_fixture)
    response = client.get("/order/")
    assert response.status_code == 200, (
        f"Attendu 200 pour /order/ avec {client_fixture}, "
        f"obtenu {response.status_code}."
    )
    assert b"Commandes" in response.data, (
        f"Le contenu de la page d'accueil du module commandes est incorrect "
        f"pour {client_fixture}."
    )
