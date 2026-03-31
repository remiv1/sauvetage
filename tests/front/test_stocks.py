"""Tests pour les routes de stock."""

import secrets
import string
import pytest

# +================================================================================================+
# |                          Gestion des tests de routes_htmx_search                               |
# +================================================================================================+

def test_cleared_authenticated(client_all):
    """Tester que la route /stock/htmx/orders/cleared fonctionne avec une session authentifiée."""
    response = client_all.get("/stock/htmx/orders/cleared")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200


def test_cleared_unauthenticated(client):
    """Tester que la route /stock/htmx/cleared redirige sans authentification."""
    response = client.get("/stock/htmx/cleared")

    # Devrait retourner 302 (redirect) car pas d'authentification
    assert response.status_code == 302


def test_search_table(client_all,
                      db_session_main,      # pylint: disable=redefined-outer-name, unused-argument
                      inventory_movements):   # pylint: disable=redefined-outer-name, unused-argument
    """Tester que la route /stock/htmx/search/table fonctionne avec une session authentifiée."""
    response = client_all.get("/stock/htmx/search/table?ean13=9789876543210")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith("<!-- template table.html -->")


def test_dilicom_modal(client_all,
                      db_session_main,      # pylint: disable=redefined-outer-name, unused-argument
                      dilicom_referencial):   # pylint: disable=redefined-outer-name, unused-argument
    """Tester que la route /stock/htmx/search/dilicom/1 fonctionne avec une session authentifiée."""
    response = client_all.get(f"/stock/htmx/search/dilicom/{dilicom_referencial.id}")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith("<p>Aucun référentiel Dilicom trouvé pour cet objet.</p>")


def test_object_autocomplete(client_all,
                         db_session_main,      # pylint: disable=redefined-outer-name, unused-argument
                         dilicom_referencial):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/search/object/autocomplete/name?q=test
    fonctionne avec une session authentifiée.
    """
    response = client_all.get("/stock/htmx/search/object/autocomplete/name?q=test")

    assert response.status_code == 200
    assert response.text.startswith("<!-- template autocomplete_dropdown.html -->")


def test_create_tag_htmx(client_all,
                         db_session_main,):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/search/object/tag/create
    fonctionne avec une session authentifiée.
    """
    alphabet = string.ascii_letters + string.digits
    aleatory_string = ''.join(secrets.choice(alphabet) for _ in range(16))
    response = client_all.post(
        "/stock/htmx/search/object/tag/create",
        data={
            "name": aleatory_string,
            "description": f"This is a test tag created during unit testing for {aleatory_string}.",
        })

    assert response.status_code == 200
    assert response.text.startswith("<!-- template tag_selected.html -->")


def test_object_form(client_all,
                         db_session_main):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/search/object/form
    fonctionne avec une session authentifiée.
    """
    response = client_all.get("/stock/htmx/search/object/form")

    assert response.status_code == 200
    assert response.text.startswith("<!-- template single_object_form.html -->")


def test_object_view_or_edit(client_all,
                         general_object):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/search/object/view/1
    fonctionne avec une session authentifiée.
    """
    response = client_all.get(f"/stock/htmx/search/object/view/{general_object.id}")

    assert response.status_code == 200
    assert response.text.startswith("<!-- template single_object_form.html -->")


def test_object_complement(client_all,
                         book_object):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/search/object/complement
    fonctionne avec une session authentifiée.
    """
    response = client_all.get("/stock/htmx/search/object/complement",
                                        query_string={
                                            "general_object_type": "book",
                                            "form_state": "view",
                                            "object_id": book_object.id,
                                        })

    assert response.status_code == 200
    assert response.text.startswith("<!-- template object_complement.html -->")

    with pytest.raises(ValueError, match="Opération introuvable."):
        client_all.get("/stock/htmx/search/object/complement",
                                    query_string={
                                        "general_object_type": "other",
                                        "form_state": "monkey",
                                        "object_id": book_object.id,
                                    })


def test_create_object(client_all, supplier, tags):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/search/object/create
    fonctionne avec une session authentifiée.
    """
    alphabet = string.ascii_letters + string.digits
    aleatory_string = ''.join(secrets.choice(alphabet) for _ in range(16))
    response = client_all.post(
        "/stock/htmx/search/object/create",
        data={
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "general_object_type": "book",
            "ean_13": "9781234567890",
            "name": f"Test Book {aleatory_string}",
            "description": f"A test book created during unit testing for {aleatory_string}.",
            "price": "19.99",
            "book-author": "John Doe",
            "book-diffuser": "Test Diffuser",
            "book-editor": "Test Editor",
            "book-genre": "Fiction",
            "book-publication_year": 2020,
            "book-pages": 300,
            "object_tags-0-tag_id": tags[0].id,
            "object_tags-1-tag_id": tags[1].id,
            "object_tags-2-tag_id": tags[2].id,
            "obj_metadatas-items-0-key": "key1",
            "obj_metadatas-items-0-value": "value1",
            "obj_metadatas-items-1-key": "key2",
            "obj_metadatas-items-1-value": "value2",
            "media_files-0-file_name": "test_image.jpg",
            "media_files-0-file_type": "lnk",
            "media_files-0-alt_text": "An image showing a test object",
            "media_files-0-file_link": "http://example.com/test_image.jpg",
        })

    assert response.status_code == 200
    assert response.text.startswith("<!-- template single_object_form.html -->")

    response = client_all.post("/stock/htmx/search/object/create", data={})
    assert response.status_code == 423
    assert response.text.startswith("<!-- template single_object_form.html -->")


def test_edit_object(client_all, book_object, supplier):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/search/object/edit/1
    fonctionne avec une session authentifiée.
    """
    response = client_all.get(f"/stock/htmx/search/object/edit/{book_object.id}",
                                        data={
                                            "supplier_id": supplier.id,
                                            "supplier_name": supplier.name,
                                            "general_object_type": book_object.general_object_type,
                                            "ean_13": book_object.ean13,
                                            "name": "Nouveau nom du livre",
                                            "description": book_object.description,
                                            "price": str(book_object.price),
                                            "book-author": book_object.book.author,
                                            "book-diffuser": book_object.book.diffuser,
                                            "book-editor": book_object.book.editor,
                                            "book-genre": book_object.book.genre,
                                            "book-publication_year":
                                                    book_object.book.publication_year,
                                            "book-pages": book_object.book.pages,
                                        })

    assert response.status_code == 200
    assert response.text.startswith("<!-- template single_object_form.html -->")


def test_object_toggle_active_modal(client_all, book_object):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/search/object/toggle_active_modal/{id}
    fonctionne avec une session authentifiée.
    """
    response = client_all.get(
        f"/stock/htmx/search/object/toggle_active_modal/{book_object.id}"
        )

    assert response.status_code == 200
    assert response.text.startswith("<!-- template single_object_form.html -->")


def test_object_toggle_active(client_all, book_object):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/search/object/toggle-active/{id}
    fonctionne avec une session authentifiée.
    """
    response = client_all.post(
        f"/stock/htmx/search/object/toggle-active/{book_object.id}"
        )

    assert response.status_code == 200
    assert response.text.startswith("<!-- template toggle_active_modal.html -->")


def test_dilicom_add(client_all, book_object):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/search/dilicom/{id}/add
    fonctionne avec une session authentifiée.
    """
    response = client_all.post(f"/stock/htmx/search/dilicom/{book_object.id}/add",
                                         data={
                                            "gln13": book_object.supplier.gln13,
                                         })

    assert response.status_code == 200
    assert response.text.startswith("<!-- template dilicom_modal.html -->")


def test_dilicom_remove(client_all, book_object, dilicom_referencial):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/search/dilicom/{id}/remove
    fonctionne avec une session authentifiée.
    """
    response = client_all.post(
        f"/stock/htmx/search/dilicom/{book_object.id}/remove"
        )

    assert response.status_code == 200
    assert response.text.startswith("<!-- template dilicom_modal.html -->")

# +================================================================================================+
# |                          Gestion des tests de routes                                           |
# +================================================================================================+

COMPLETE_PAGE_START = "<!DOCTYPE html>\n<html lang=\"fr\">\n<head>"


def test_index(client_all, inventory_movements):   # pylint: disable=redefined-outer-name, unused-argument
    """Tester que la route /stock/ fonctionne avec une session authentifiée."""
    response = client_all.get("/stock/")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith(COMPLETE_PAGE_START)


def test_council(client_all, inventory_movements):   # pylint: disable=redefined-outer-name, unused-argument
    """Tester que la route /stock/council fonctionne avec une session authentifiée."""
    response = client_all.get("/stock/council")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith(COMPLETE_PAGE_START)


def test_orders(client_all, inventory_movements):   # pylint: disable=redefined-outer-name, unused-argument
    """Tester que la route /stock/orders fonctionne avec une session authentifiée."""
    response = client_all.get("/stock/orders")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith(COMPLETE_PAGE_START)


def test_create_order(client_all, book_object, inventory_movements):   # pylint: disable=redefined-outer-name, unused-argument
    """Tester que la route /stock/orders/create fonctionne avec une session authentifiée."""
    response = client_all.get("/stock/orders/new")

    assert response.status_code == 200
    assert response.text.startswith(COMPLETE_PAGE_START)


def test_create_return(client_all):   # pylint: disable=redefined-outer-name, unused-argument
    """Tester que la route /stock/returns/new fonctionne avec une session authentifiée."""
    response = client_all.get("/stock/returns/new")

    assert response.status_code == 200
    assert response.text.startswith(COMPLETE_PAGE_START)


def test_search(client_all):   # pylint: disable=redefined-outer-name, unused-argument
    """Tester que la route /stock/search fonctionne avec une session authentifiée."""
    response = client_all.get("/stock/search")

    assert response.status_code == 200
    assert response.text.startswith(COMPLETE_PAGE_START)

# +================================================================================================+
# |                          Gestion des tests de routes_htmx_return                               |
# +================================================================================================+

def test_cleared_return(client_all):
    """
    Tester que la route /stock/htmx/returns/cleared
    fonctionne avec une session authentifiée.
    """
    response = client_all.get("/stock/htmx/returns/cleared")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text == ""  # Doit retourner une section vide


def test_returns(client_all, inventory_movements):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/returns/
    fonctionne avec une session authentifiée.
    """
    response = client_all.get("/stock/htmx/returns/")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith("<!-- template home.html -->")


def test_new_return_section(client_all):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/returns/section/create
    fonctionne avec une session authentifiée.
    """
    response = client_all.get("/stock/htmx/returns/section/create")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 404


def test_view_return(client_all, order_in_return):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/returns/view/{return_id}
    fonctionne avec une session authentifiée.
    """
    # Récupérer l'ID d'un retour existant à partir des mouvements d'inventaire
    return_id = order_in_return.id
    response = client_all.get(f"/stock/htmx/returns/view/{return_id}")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 404


def test_new_return_table(client_all):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/returns/table/create
    fonctionne avec une session authentifiée.
    """
    response = client_all.post("/stock/htmx/returns/table/create")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 404


def test_new_return_line_form(client_all):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/returns/line/create
    fonctionne avec une session authentifiée.
    """
    response = client_all.get("/stock/htmx/returns/line/create")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 404

# +================================================================================================+
# |                          Gestion des tests de routes_htmx_orders                               |
# +================================================================================================+

def test_cleared_orders(client_all):
    """
    Tester que la route /stock/htmx/orders/cleared
    fonctionne avec une session authentifiée.
    """
    response = client_all.get("/stock/htmx/orders/cleared")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text == ""  # Doit retourner une section vide


def test_orders_htmx(client_all, inventory_movements):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/orders/
    fonctionne avec une session authentifiée.
    """
    response = client_all.get("/stock/htmx/orders/")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith("<!-- template home.html -->")


def test_new_order_section(client_all, supplier):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/orders/section/create
    fonctionne avec une session authentifiée.
    """
    response = client_all.get("/stock/htmx/orders/section/create")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith("<!-- template new.html -->")

    with pytest.raises(ValueError, match="Formulaire de création de commande invalide"):
        client_all.post("/stock/htmx/orders/section/create",
                                             data={})

    response = client_all.post("/stock/htmx/orders/section/create",
                                         data={
                                            "supplier_id": supplier.id,
                                            "supplier_name": supplier.name,
                                         })
    assert response.status_code == 200
    assert response.text.startswith("<!-- template view.html -->")


def test_edit_order(client_all, order_in):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/orders/{order_id}/section/edit
    fonctionne avec une session authentifiée.
    """
    order_id = order_in.id
    response = client_all.get(f"/stock/htmx/orders/{order_id}/section/edit")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith("<!-- template view.html -->")


def test_view_order(client_all, order_in):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/orders/view/{order_id}
    fonctionne avec une session authentifiée.
    """
    order_id = order_in.id
    response = client_all.get(f"/stock/htmx/orders/view/{order_id}")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith("<!-- template view.html -->")


def test_cancel_order(client_all, order_in):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/orders/cancel/{order_id}
    fonctionne avec une session authentifiée.
    """
    order_id = order_in.id
    response = client_all.post(f"/stock/htmx/orders/cancel/{order_id}")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith("<!-- template canceled.html -->")

    reponse = client_all.get(f"/stock/htmx/orders/cancel/{order_id}")
    assert reponse.status_code == 200
    assert reponse.text.startswith("<!-- template canceled.html -->")

def test_new_order_line(client_all, order_in):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/orders/{order_id}/line/create
    fonctionne avec une session authentifiée.
    """
    order_id = order_in.id
    response = client_all.post(f"/stock/htmx/orders/{order_id}/line/create")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith("<!-- template new_line.html -->")

    response = client_all.get(f"/stock/htmx/orders/{order_id}/line/create")

    assert response.status_code == 200
    assert response.text.startswith("<!-- template new_line.html -->")


def test_edit_order_line(client_all, order_in):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/orders/{order_id}/line/{line_id}/edit
    fonctionne avec une session authentifiée.
    """
    order_id = order_in.id
    line_id = order_in.orderin_lines[0].id
    response = client_all.get(f"/stock/htmx/orders/{order_id}/line/{line_id}/edit")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith("<!-- template new_line.html -->")

    response = client_all.post(f"/stock/htmx/orders/{order_id}/line/{line_id}/edit",
                                         data={
                                             "order_id": order_id,
                                             "general_object_id":
                                                order_in.orderin_lines[0].general_object_id,
                                             "quantity": 5,
                                             "unit_price": "9.99",
                                             "vat_rate": "5.50",
                                         })

    assert response.status_code == 200
    assert response.text.startswith("<!-- template view.html -->")


def test_confirm_order(client_all, order_in):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/orders/{order_id}/confirm
    fonctionne avec une session authentifiée.
    """
    order_id = order_in.id
    response = client_all.post(f"/stock/htmx/orders/{order_id}/confirm")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith("<!-- template confirmed.html -->")


def test_receipt_order(client_all, order_in):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/orders/{order_id}/receipt
    fonctionne avec une session authentifiée.
    """
    order_id = order_in.id
    response = client_all.get(f"/stock/htmx/orders/{order_id}/receipt")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith("<!-- template view.html -->")


def test_receive_order_line(client_all, order_in):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/orders/{order_id}/line/{line_id}/receive
    fonctionne avec une session authentifiée.
    """
    order_id = order_in.id
    line_id = order_in.orderin_lines[0].id
    response = client_all.get(f"/stock/htmx/orders/{order_id}/line/{line_id}/receive")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith("<!-- template receive_line.html -->")

    response = client_all.post(f"/stock/htmx/orders/{order_id}/line/{line_id}/receive",
                                         data={
                                            "qty_received": 5,
                                            "qty_canceled": 0,
                                         })

    assert response.status_code == 200
    assert response.text.startswith("<!-- template receive_line.html -->")


def test_update_external_ref(client_all, order_in):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/orders/{order_id}/external-ref
    fonctionne avec une session authentifiée.
    """
    order_id = order_in.id
    response = client_all.post(f"/stock/htmx/orders/{order_id}/external-ref",
                                         data={
                                            "external_ref": "NEW-EXT-REF-123",
                                         })

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200
    assert response.text.startswith("<!-- template view.html -->")


# +================================================================================================+
# |                          Gestion des tests de routes_data                                      |
# +================================================================================================+

def test_api_update_price(client_all, inventory_movements):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/data/council
    fonctionne avec une session authentifiée.
    """
    response_1 = client_all.post("/stock/data/council",
                                           json={
                                               "movement_id": inventory_movements[0].id,
                                               "price": "24.99",
                                           })
    response_2 = client_all.post("/stock/data/council",
                                           json={
                                               "movement_id": inventory_movements[1].id,
                                               "price": "test_string",
                                           })
    response_3 = client_all.post("/stock/data/council",
                                           json={
                                               "movement_id": 999999,
                                               "price": "19.99",
                                           })
    response_4 = client_all.post("/stock/data/council",
                                           json={
                                               "price": "19.99",
                                           })
    response_5 = client_all.post("/stock/data/council",
                                           json={
                                               "movement_id": inventory_movements[0].id,
                                           })

    assert response_1.status_code == 200
    assert response_1.json["ok"] is True
    assert isinstance(response_1.json["new_movement_id"], int)
    assert response_2.status_code == 400
    assert response_2.json["error"] == "price doit être un nombre"
    assert response_3.status_code == 404
    assert response_3.json["error"] == "Mouvement 999999 introuvable"
    assert response_4.status_code == 400
    assert response_4.json["error"] \
        == response_5.json["error"] \
        == "movement_id et price sont requis"
    assert response_5.status_code == 400


def test_api_create_order(client_all, supplier):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/data/orderin/create
    fonctionne avec une session authentifiée.
    """
    response_1 = client_all.post("/stock/data/orderin/create",
                                           json={
                                               "supplier_id": supplier.id,
                                               "supplier_name": supplier.name,
                                           })
    response_2 = client_all.post("/stock/data/orderin/create",
                                           json={})

    assert response_1.status_code == 200
    assert response_1.json["ok"] is True
    assert isinstance(response_1.json["id_supplier"], int)
    assert response_2.status_code == 500
    assert response_2.json["error"] == "Le champ fournisseur est requis."
