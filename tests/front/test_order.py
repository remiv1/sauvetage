"""Tests pour le module commandes"""

import pytest

from db_models.objects import GeneralObjects

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


def test_order_article_search_accepts_ean13_or_title(
    client_all,
    supplier,
    db_session_main,
):
    """La recherche d'article client doit accepter un EAN13 ou un extrait de titre."""
    article = GeneralObjects(
        supplier_id=supplier.id,
        general_object_type="generic",
        ean13="1234567890136",
        name="Chroniques de la recherche hybride",
        description="Objet test",
        price=18.0,
    )
    db_session_main.add(article)
    db_session_main.commit()

    ean_response = client_all.get("/order/htmx/create/articles?q=1234567890136")
    title_response = client_all.get("/order/htmx/create/articles?q=recherche hybride")

    assert ean_response.status_code == 200
    assert title_response.status_code == 200
    assert "Chroniques de la recherche hybride" in ean_response.get_data(as_text=True)
    assert "Chroniques de la recherche hybride" in title_response.get_data(as_text=True)
