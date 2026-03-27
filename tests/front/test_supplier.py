"""Tests pour les routes de fournisseurs."""

import pytest   # pylint: disable=unused-import

# +================================================================================================+
# |                          Gestion des tests de routes                                           |
# +================================================================================================+

def test_index(client_all):
    """Test de la page d'accueil du module fournisseurs."""
    response = client_all.get("/supplier/")
    assert response.status_code == 200
    assert response.text.startswith("\n    <h1>Fournisseurs</h1>\n")

# +================================================================================================+
# |                          Gestion des tests de routes_htmx                                      |
# +================================================================================================+

def test_get_suppliers(client_all, supplier):     # pylint: disable=redefined-outer-name, unused-argument
    """Test de la route HTMX de recherche de fournisseurs."""
    with pytest.raises(ValueError, match="Type de données non supporté : name"):
        client_all.get("/supplier/htmx/get/suppliers/name?q=test")
    response_2 = client_all.get("/supplier/htmx/get/suppliers/id_name_gln",
                                          query_string={"supplier_name": "Inexistant"})
    response_3 = client_all.get("/supplier/htmx/get/suppliers/id_name_gln",
                                          query_string={"supplier_name": "test"})
    response_4 = client_all.get("/supplier/htmx/get/suppliers/filter",
                                          query_string={"q": "test"})
    for response in [response_2, response_3, response_4]:
        assert response.status_code == 200
    assert response_2.text.startswith(
                    "\n\n    <!-- template suppliers_dropdown.html - vide -->"
                    )
    assert response_3.text.startswith("\n\n    <!-- template suppliers_dropdown.html -->")
    assert response_4.text.startswith("<!-- template filter_suppliers_dropdown.html -->")


def test_add_new_supplier(client_all):
    """Test de la route HTMX d'affichage du formulaire d'ajout rapide."""
    response = client_all.get("/supplier/htmx/add-new/Test Supplier")
    assert response.status_code == 200
    assert response.text.startswith("<!-- template add_supplier_form.html -->")


def test_create_supplier_htmx(client_all, db_session_main):   # pylint: disable=redefined-outer-name, unused-argument
    """Test de la route HTMX de création rapide d'un fournisseur."""
    # Test de validation : nom manquant
    response_1 = client_all.post("/supplier/htmx/create",
                                           data={
                                               "supplier_name": "test création rapide",
                                               "gln13": "1234567890123",
                                               "contact_email": "test@example.com",
                                               "contact_phone": "0123456789"
                                           })
    response_2 = client_all.post("/supplier/htmx/create",
                                           data={})

    assert response_1.status_code == 200
    assert response_1.text == ""
    assert response_1.headers.get("HX-Trigger") is not None
    assert response_2.status_code == 422
    assert response_2.text.startswith("<!-- template add_supplier_form.html -->")
    assert "Créer le fournisseur" in response_2.text


def test_select_supplier(client_all, supplier):   # pylint: disable=redefined-outer-name, unused-argument
    """Test de la route HTMX de sélection d'un fournisseur."""
    response = client_all.get(f"/supplier/htmx/select/{supplier.id}")
    assert response.status_code == 200
    assert response.text.startswith("<!-- template select_supplier.html -->")


def test_select_dilicom_supplier(client_all, supplier):   # pylint: disable=redefined-outer-name, unused-argument
    """Test de la route HTMX de sélection d'un fournisseur (contexte Dilicom)."""
    response = client_all.get(
        f"/supplier/htmx/select/{supplier.id}",
        query_string={"supplier_name": "test", "gln13": "1234567890123", "context": "dilicom"}
    )
    assert response.status_code == 200
    assert response.text.startswith("<!-- template select_supplier.html -->")


def test_close_modal(client_all):
    """Test de la route HTMX de fermeture de modale."""
    response = client_all.get("/supplier/htmx/close-modal")
    assert response.status_code == 200
    assert response.text == ""
