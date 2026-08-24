"""Tests pour les routes de stock."""   # pylint: disable=C0302

import io
import secrets
import string
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path

import pytest
from flask.testing import FlaskClient
from sqlalchemy.orm import Session
from PIL import Image

from db_models.objects import (
    VatRate,
    GeneralObjects,
    MediaFiles,
    ObjectVariations,
    OrderInLine,
    OrderInLinePrice,
    InventoryMovements,
    OrderIn,
)
from db_models.repositories.stocks.orders import OrderRepository

# +================================================================================================+
# |                          Gestion des tests de routes_htmx_search                               |
# +================================================================================================+


def test_stock_media_small_returns_webp_thumbnail(
    client_all: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Une miniature locale est renvoyée en WebP et ne dépasse pas 160 pixels."""
    image_path = tmp_path / "cover.png"
    Image.new("RGB", (640, 320), "red").save(image_path, format="PNG")
    monkeypatch.setattr(
        "app_front.blueprints.stock.routes_htmx_search._MEDIA_UPLOAD_DIR",
        str(tmp_path),
    )

    response = client_all.get("/stock/htmx/search/media/cover.png?small=true")

    assert response.status_code == 200
    assert response.mimetype == "image/webp"
    with Image.open(io.BytesIO(response.data)) as thumbnail:
        assert thumbnail.format == "WEBP"
        assert thumbnail.size == (160, 80)


def test_stock_media_small_false_returns_original_file(
    client_all: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """L'accès avec ``small=false`` retourne le fichier local sans transformation."""
    image_path = tmp_path / "cover.png"
    Image.new("RGB", (32, 16), "blue").save(image_path, format="PNG")
    original_content = image_path.read_bytes()
    monkeypatch.setattr(
        "app_front.blueprints.stock.routes_htmx_search._MEDIA_UPLOAD_DIR",
        str(tmp_path),
    )

    response = client_all.get("/stock/htmx/search/media/cover.png?small=false")

    assert response.status_code == 200
    assert response.data == original_content
    assert response.mimetype == "image/png"


def test_stock_media_small_returns_404_for_missing_file(
    client_all: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Une demande de miniature pour un fichier absent retourne 404."""
    monkeypatch.setattr(
        "app_front.blueprints.stock.routes_htmx_search._MEDIA_UPLOAD_DIR",
        str(tmp_path),
    )

    response = client_all.get("/stock/htmx/search/media/absent.png?small=true")

    assert response.status_code == 404


def test_stock_media_returns_503_without_upload_directory(
    client_all: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La route refuse les médias lorsque le répertoire de dépôt est absent."""
    monkeypatch.setattr(
        "app_front.blueprints.stock.routes_htmx_search._MEDIA_UPLOAD_DIR",
        "",
    )

    response = client_all.get("/stock/htmx/search/media/cover.png?small=true")

    assert response.status_code == 503


def test_stock_media_small_falls_back_to_original_non_image(
    client_all: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Un fichier non-image demandé en miniature conserve son contenu original."""
    file_path = tmp_path / "document.txt"
    original_content = b"contenu non image"
    file_path.write_bytes(original_content)
    monkeypatch.setattr(
        "app_front.blueprints.stock.routes_htmx_search._MEDIA_UPLOAD_DIR",
        str(tmp_path),
    )

    response = client_all.get("/stock/htmx/search/media/document.txt?small=true")

    assert response.status_code == 200
    assert response.data == original_content


@pytest.mark.parametrize("form_state", ["edit", "view"])
def test_object_complement_routes_legacy_local_media_path(
    client_all: FlaskClient,
    book_object: GeneralObjects,
    db_session_main: Session,
    form_state: str,
) -> None:
    """Un chemin absolu historique utilise les URLs média en édition et en vue."""
    legacy_path = "/home/root/app/documents/shared/pictures/cover.jpg"
    db_session_main.add(
        MediaFiles(
            general_object_id=book_object.id,
            file_type="img",
            file_link=legacy_path,
            is_local=False,
        )
    )
    db_session_main.commit()

    response = client_all.get(
        "/stock/htmx/search/object/complement",
        query_string={
            "general_object_type": "book",
            "form_state": form_state,
            "object_id": book_object.id,
        },
    )

    body = response.get_data(as_text=True)
    media_url = "/stock/htmx/search/media/cover.jpg"
    assert response.status_code == 200
    assert f"{media_url}?small=true" in body
    assert f"{media_url}?small=false" in body
    assert legacy_path not in body

def test_cleared_authenticated(client_all):
    """Tester que la route /stock/htmx/orders/cleared fonctionne avec une session authentifiée."""
    response = client_all.get("/stock/htmx/orders/cleared")

    # Devrait retourner 200 (succès) au lieu de 302 (redirect)
    assert response.status_code == 200


def test_create_reservation_with_context(client_all, supplier, db_session_main):    # pylint: disable=W0613
    """Une réservation doit conserver notes, localisation et responsable dans le contexte métier."""
    notes = "Vente déportée - Péraudière"
    location = "Montrottier"
    manager = "Jean Dupont"
    response = client_all.post(
        "/stock/htmx/reservations/section/create",
        data={
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "reservation_notes": notes,
            "reservation_location": location,
            "reservation_responsible_name": manager,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert notes in response.get_data(as_text=True)
    assert location in response.get_data(as_text=True)
    assert manager in response.get_data(as_text=True)


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


def test_supplier_object_filter_for_order_line(client_all, supplier, db_session_main):
    """La recherche d'articles pour une commande ne doit proposer que les objets du fournisseur."""

    other_supplier = supplier.__class__(
        name="Autre fournisseur",
        gln13="9876543210987",
        contact_email="autre@fournisseur.test",
    )
    db_session_main.add(other_supplier)
    db_session_main.flush()

    own_obj = GeneralObjects(
        supplier_id=supplier.id,
        general_object_type="generic",
        ean13="9780000000001",
        name="Objet fournisseur principal",
        description="Objet du fournisseur principal",
        price=10.0,
    )
    other_obj = GeneralObjects(
        supplier_id=other_supplier.id,
        general_object_type="generic",
        ean13="9780000000002",
        name="Objet fournisseur secondaire",
        description="Objet d'un autre fournisseur",
        price=12.0,
    )
    db_session_main.add_all([own_obj, other_obj])
    db_session_main.commit()

    response = client_all.get(
        f"/inventory/htmx/objects/get?object-wrapper=Objet&supplier_id={supplier.id}",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Objet fournisseur principal" in response.get_data(as_text=True)
    assert "Objet fournisseur secondaire" not in response.get_data(as_text=True)


def test_supplier_object_search_uses_exact_ean13(client_all, supplier, db_session_main):
    """Une saisie de treize chiffres doit chercher l'EAN13 exact chez le fournisseur."""
    own_obj = GeneralObjects(
        supplier_id=supplier.id,
        general_object_type="generic",
        ean13="1234567890128",
        name="Article avec EAN généré",
        description="Objet test",
        price=10.0,
    )
    db_session_main.add(own_obj)
    db_session_main.commit()

    response = client_all.get(
        f"/inventory/htmx/objects/get?object-wrapper=1234567890128&supplier_id={supplier.id}",
        follow_redirects=True,
    )

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Article avec EAN généré" in body
    assert "EAN : 1234567890128" in body


def test_supplier_object_search_keeps_supplier_filter_for_ean13(
    client_all,
    supplier,
    db_session_main,
):
    """Un EAN13 connu chez un autre fournisseur ne doit pas être sélectionnable."""
    other_supplier = supplier.__class__(
        name="Fournisseur EAN externe",
        gln13="9876543210987",
        contact_email="ean@fournisseur.test",
    )
    db_session_main.add(other_supplier)
    db_session_main.flush()
    db_session_main.add(
        GeneralObjects(
            supplier_id=other_supplier.id,
            general_object_type="generic",
            ean13="1234567890129",
            name="Article externe",
            description="Objet test",
            price=10.0,
        )
    )
    db_session_main.commit()

    response = client_all.get(
        f"/inventory/htmx/objects/get?object-wrapper=1234567890129&supplier_id={supplier.id}",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Article externe" not in response.get_data(as_text=True)


def test_order_object_dropdown_does_not_limit_quantity_like_reservation(
        client_all,
        supplier,
        db_session_main,
    ):
    """
    Le choix d'un article pour une commande fournisseur ne doit pas imposer un stock max réservé.
    """
    obj = GeneralObjects(
        supplier_id=supplier.id,
        general_object_type="generic",
        ean13="9780000000003",
        name="Objet commande fournisseur",
        description="Objet de commande fournisseur",
        price=10.0,
    )
    db_session_main.add(obj)
    db_session_main.commit()

    response = client_all.get(
        f"/inventory/htmx/objects/get?object-wrapper=Objet commande&supplier_id={supplier.id}",
        follow_redirects=True,
    )

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "quantityField.max =" not in body
    assert "reservationMode" in body


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


def test_create_object(client_all, supplier, tags, db_session_main):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Tester que la route /stock/htmx/search/object/create
    fonctionne avec une session authentifiée.
    """
    vat_rate = VatRate(
        code=1,
        rate=5.50,
        label="Taux réduit test",
        date_start=datetime.now(timezone.utc),
        date_end=None,
    )
    db_session_main.add(vat_rate)
    db_session_main.flush()
    vat_rate_id = vat_rate.id

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
            "purchase_price": "12.50",
            "prices-0-price": "19.99",
            "prices-0-vat_rate_id": str(vat_rate_id),
            "prices-0-from_date": "2026-01-01",
            "prices-0-to_date": "",
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
            "media_files-0-file_type": "lnk",
            "media_files-0-alt_text": "An image showing a test object",
            "media_files-0-file_link": "http://example.com/test_image.jpg",
        })

    assert response.status_code == 200
    assert response.text.startswith("<!-- template single_object_form.html -->")

    response = client_all.post("/stock/htmx/search/object/create", data={})
    assert response.status_code == 423
    assert response.text.startswith("<!-- template single_object_form.html -->")


def test_create_object_with_variations(client_all, supplier, db_session_main):
    """La création d'un produit enregistre les variations soumises avec le parent."""
    vat_rate = VatRate(
        code=2,
        rate=20.00,
        label="Taux normal variations",
        date_start=datetime.now(timezone.utc),
        date_end=None,
    )
    db_session_main.add(vat_rate)
    db_session_main.flush()
    ean13 = "9781234567891"

    response = client_all.post(
        "/stock/htmx/search/object/create",
        data={
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "general_object_type": "other",
            "ean_13": ean13,
            "name": "Produit à variations",
            "description": "Produit de test avec deux variations.",
            "prices-0-price": "19.99",
            "prices-0-vat_rate_id": str(vat_rate.id),
            "prices-0-from_date": "2026-01-01",
            "variations-0-name": "Format poche",
            "variations-0-description": "Petit format",
            "variations-0-price": "12.50",
            "variations-0-purchase_price": "6.00",
            "variations-0-is_active": "y",
            "variations-1-name": "Format relié",
            "variations-1-description": "Grand format",
            "variations-1-price": "22.50",
            "variations-1-purchase_price": "11.00",
            "variations-1-is_active": "y",
        },
    )

    assert response.status_code == 200
    product = db_session_main.query(GeneralObjects).filter_by(ean13=ean13).one()
    variations = (
        db_session_main.query(ObjectVariations)
        .filter_by(general_object_id=product.id)
        .order_by(ObjectVariations.name)
        .all()
    )
    assert [(variation.name, variation.price) for variation in variations] == [
        ("Format poche", 12.5),
        ("Format relié", 22.5),
    ]


def test_create_object_without_variation(client_all, supplier, db_session_main):
    """La création d'un produit reste possible sans variation."""
    vat_rate = VatRate(
        code=3,
        rate=10.00,
        label="Taux intermédiaire sans variation",
        date_start=datetime.now(timezone.utc),
        date_end=None,
    )
    db_session_main.add(vat_rate)
    db_session_main.flush()
    ean13 = "9781234567892"

    response = client_all.post(
        "/stock/htmx/search/object/create",
        data={
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "general_object_type": "other",
            "ean_13": ean13,
            "name": "Produit sans variation",
            "description": "Produit de test sans variation.",
            "prices-0-price": "9.99",
            "prices-0-vat_rate_id": str(vat_rate.id),
            "prices-0-from_date": "2026-01-01",
        },
    )

    assert response.status_code == 200
    product = db_session_main.query(GeneralObjects).filter_by(ean13=ean13).one()
    assert not product.object_variations


def test_edit_object_add_variation(client_all, book_object, supplier, db_session_main):
    """L'édition d'un produit peut ajouter une variation dans la soumission globale."""
    vat_rate = VatRate(
        code=4,
        rate=5.50,
        label="Taux réduit ajout variation",
        date_start=datetime.now(timezone.utc),
        date_end=None,
    )
    db_session_main.add(vat_rate)
    db_session_main.flush()

    response = client_all.post(
        f"/stock/htmx/search/object/edit/{book_object.id}",
        data={
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "general_object_type": "book",
            "ean_13": book_object.ean13,
            "name": book_object.name,
            "description": book_object.description,
            "prices-0-price": "19.99",
            "prices-0-vat_rate_id": str(vat_rate.id),
            "prices-0-from_date": "2026-01-01",
            "book-author": book_object.book.author,
            "book-diffuser": book_object.book.diffuser,
            "book-editor": book_object.book.editor,
            "book-genre": book_object.book.genre,
            "book-publication_year": book_object.book.publication_year,
            "book-pages": book_object.book.pages,
            "variations-0-name": "Édition collector",
            "variations-0-description": "Avec jaquette",
            "variations-0-price": "29.99",
            "variations-0-purchase_price": "15.00",
            "variations-0-is_active": "y",
        },
    )

    assert response.status_code == 200
    variation = (
        db_session_main.query(ObjectVariations)
        .filter_by(general_object_id=book_object.id, name="Édition collector")
        .one()
    )
    assert float(variation.price) == 29.99


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
    assert response.text.startswith("<!-- template cancelled.html -->")

    reponse = client_all.get(f"/stock/htmx/orders/cancel/{order_id}")
    assert reponse.status_code == 200
    assert reponse.text.startswith("<!-- template cancelled.html -->")


def test_create_reservation_line(client_all, order_in, book_object, db_session_main):   # pylint: disable=redefined-outer-name, unused-argument
    """Une ligne de réservation doit être créée même sans TVA affichée dans le formulaire."""
    order_id = order_in.id
    initial_line_count = len(order_in.orderin_lines)

    response = client_all.post(
        f"/stock/htmx/reservations/{order_id}/line/create",
        data={
            "order_id": order_id,
            "general_object_id": book_object.id,
            "quantity": "3",
        },
    )

    assert response.status_code == 200
    assert response.text.startswith("<!-- template view.html -->")
    assert "Test Book" in response.get_data(as_text=True)

    saved_line = db_session_main.query(OrderInLine).filter_by(
        order_in_id=order_id,
        general_object_id=book_object.id,
    ).first()
    assert saved_line is not None
    assert saved_line.qty_ordered == 3
    assert saved_line.get_unit_price_ht() == Decimal(str(book_object.purchase_price))
    assert len(order_in.orderin_lines) == initial_line_count + 1


def test_delete_reservation_line_reintegrates_stock(db_session_main, supplier, general_object):
    """La suppression d'une ligne de réservation doit compenser le mouvement "reserved"."""
    order = OrderIn(
        order_ref="RES-000001",
        supplier_id=supplier.id,
        reservation_context={"notes": "test"},
        order_state="draft",
    )
    db_session_main.add(order)
    db_session_main.flush()

    movement = InventoryMovements(
        general_object_id=general_object.id,
        movement_type="reserved",
        quantity=3,
        price_at_movement=12.5,
        source="stock",
        destination="reserve",
        notes="Réservation test",
    )
    db_session_main.add(movement)
    db_session_main.flush()

    line = OrderInLine(
        order_in_id=order.id,
        general_object_id=general_object.id,
        inventory_movement_id=movement.id,
        qty_ordered=3,
        qty_received=0,
        prices=[OrderInLinePrice(unit_price=12.5, vat_rate=0, position=0)],
        line_state="pending",
    )
    db_session_main.add(line)
    db_session_main.flush()

    repo = OrderRepository(db_session_main)
    repo.delete_order_in_line_db(line.id)

    assert db_session_main.get(OrderInLine, line.id) is None
    compensations = db_session_main.query(InventoryMovements).filter_by(
        general_object_id=general_object.id,
        movement_type="reserved",
    ).all()
    assert any(m.quantity == -3 for m in compensations)


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

    response = client_all.post(
        f"/stock/htmx/orders/{order_id}/line/{line_id}/edit",
        data={
            "order_id": order_id,
            "general_object_id": order_in.orderin_lines[0].general_object_id,
            "quantity": 5,
            "prices-0-unit_price": "9.99",
            "prices-0-vat_rate": "5.50",
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


def test_confirm_order_mail_choice(client_all, order_in):   # pylint: disable=redefined-outer-name, unused-argument
    """
    Pour un fournisseur avec email, l'UI doit proposer l'envoi en un clic ou le téléchargement.
    """
    order_id = order_in.id
    response = client_all.post(f"/stock/htmx/orders/{order_id}/confirm")

    assert response.status_code == 200
    assert "Envoyer par email" in response.get_data(as_text=True)
    assert "Télécharger le bon de commande" in response.get_data(as_text=True)


def test_send_order_mail_success_and_failure_states(client_all, order_in, monkeypatch):  # pylint: disable=redefined-outer-name, unused-argument
    """
    La route d'envoi mail doit remonter le statut et proposer le téléchargement en cas d'échec.
    """
    order_id = order_in.id

    monkeypatch.setattr(
        "app_front.blueprints.stock.routes_htmx_orders.send_order_by_mail",
        lambda order: True,
    )
    response = client_all.post(f"/stock/htmx/orders/{order_id}/send-mail")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Email envoyé" in body
    assert "Télécharger le bon de commande" in body

    monkeypatch.setattr(
        "app_front.blueprints.stock.routes_htmx_orders.send_order_by_mail",
        lambda order: False,
    )
    response = client_all.post(f"/stock/htmx/orders/{order_id}/send-mail")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Échec de l'envoi" in body
    assert "Le bon de commande reste disponible au téléchargement" in body


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
                                            "qty_cancelled": 0,
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
