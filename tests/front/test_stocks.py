"""Tests pour les routes de stock."""

import pytest   # pylint: disable=unused-import
import secrets
import string


def test_cleared_authenticated(authenticated_client):
    """Tester que la route /stock/htmx/orders/cleared fonctionne avec une session authentifiée."""
    response = authenticated_client.get("/stock/htmx/orders/cleared")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200


def test_cleared_unauthenticated(client):
    """Tester que la route /stock/htmx/cleared redirige sans authentification."""
    response = client.get("/stock/htmx/cleared")

    # Devrait retourner 302 (redirect) car pas d'authentification
    assert response.status_code == 302

def test_search_table(authenticated_client,
                      db_session_main,      # pylint: disable=redefined-outer-name, unused-argument
                      inventory_movements):   # pylint: disable=redefined-outer-name, unused-argument
    """Tester que la route /stock/htmx/search/table fonctionne avec une session authentifiée."""
    response = authenticated_client.get("/stock/htmx/search/table?ean13=9789876543210")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith("<!-- template table.html -->")

def test_dilicom_modal(authenticated_client,
                      db_session_main,      # pylint: disable=redefined-outer-name, unused-argument
                      dilicom_referencial):   # pylint: disable=redefined-outer-name, unused-argument
    """Tester que la route /stock/htmx/search/dilicom/1 fonctionne avec une session authentifiée."""
    response = authenticated_client.get(f"/stock/htmx/search/dilicom/{dilicom_referencial.id}")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith("<p>Aucun référentiel Dilicom trouvé pour cet objet.</p>")

def test_object_autocomplete(authenticated_client,
                         db_session_main,      # pylint: disable=redefined-outer-name, unused-argument
                         dilicom_referencial):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/search/object/autocomplete/name?q=test
    fonctionne avec une session authentifiée.
    """
    response = authenticated_client.get("/stock/htmx/search/object/autocomplete/name?q=test")

    assert response.status_code == 200
    assert response.text.startswith("<!-- template autocomplete_dropdown.html -->")

def test_create_tag_htmx(authenticated_client,
                         db_session_main,):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/search/object/tag/create
    fonctionne avec une session authentifiée.
    """
    alphabet = string.ascii_letters + string.digits
    aleatory_string = ''.join(secrets.choice(alphabet) for _ in range(16))
    response = authenticated_client.post(
        "/stock/htmx/search/object/tag/create",
        data={
            "name": aleatory_string,
            "description": f"This is a test tag created during unit testing for {aleatory_string}.",
        })

    assert response.status_code == 200
    assert response.text.startswith("<!-- template tag_selected.html -->")

def test_object_form(authenticated_client,
                         db_session_main):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/search/object/form
    fonctionne avec une session authentifiée.
    """
    response = authenticated_client.get("/stock/htmx/search/object/form")

    assert response.status_code == 200
    assert response.text.startswith("<!-- template single_object_form.html -->")

def test_object_view_or_edit(authenticated_client,
                         db_session_main,      # pylint: disable=redefined-outer-name, unused-argument
                         general_object):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/search/object/view/1
    fonctionne avec une session authentifiée.
    """
    response = authenticated_client.get(f"/stock/htmx/search/object/view/{general_object.id}")

    assert response.status_code == 200
    assert response.text.startswith("<!-- template single_object_form.html -->")
