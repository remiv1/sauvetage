"""Tests des payloads et synchronisations produits WooCommerce."""

from decimal import Decimal
from unittest.mock import MagicMock

from db_models.objects import (
    Books,
    GeneralObjects,
    ObjMetadatas,
    ObjectPrices,
    ObjectTags,
    ObjectVariations,
    OrderLine,
    OtherObjects,
    Tags,
    VatRate,
)
from db_models.services.woo_commerce.orders import _match_line_to_wc
from db_models.services.woo_commerce.products import WCProductsService


def test_general_object_payload_uses_wc_tax_slug(book_product):
    """Le payload produit doit utiliser le slug WooCommerce de la TVA."""
    payload = book_product.to_dict_for_woo_commerce()

    assert payload["tax_class"] == "taux-reduit"
    assert payload["regular_price"] == "19.99"
    assert payload["sku"] is None


def test_object_tag_payload_uses_wc_tag_id() -> None:
    """L'association objet-tag doit renvoyer l'identifiant WooCommerce du tag."""
    tag = Tags(name="Promo", description="Promo", wpwc_id=42)
    object_tag = ObjectTags(general_object_id=1, tag_id=1, tag=tag)

    payload = object_tag.to_dict_for_woo_commerce()

    assert payload == {"id": 42}


def test_wc_product_payload_includes_synced_tags() -> None:
    """Le payload produit doit inclure les tags WooCommerce déjà synchronisés."""
    service = object.__new__(WCProductsService)
    service.session = MagicMock()
    service._build_media_src = MagicMock(return_value="https://example.com/image.jpg")  # pylint: disable=W0212

    product = GeneralObjects(
        supplier_id=1,
        general_object_type="book",
        ean13="9782222222222",
        name="Produit tagué",
        description="Description",
    )
    product.prices = [
        ObjectPrices(
            price=Decimal("19.90"),
            vat_rate=VatRate(code=1, rate=20.0, label="TVA 20%", wpwc_slug="standard"),
        ),
    ]
    product.object_tags = [
        ObjectTags(
            general_object_id=1,
            tag_id=1,
            tag=Tags(name="Promo", description="Promo", wpwc_id=42),
        ),
        ObjectTags(
            general_object_id=1,
            tag_id=2,
            tag=Tags(name="Nouveauté", description="Nouveauté", wpwc_id=77),
        ),
    ]
    product.media_files = []

    payload = service._build_product_payload(product)  # pylint: disable=W0212

    assert payload["tags"] == [{"id": 42}, {"id": 77}]


def test_update_product_syncs_missing_wc_tags_before_export() -> None:
    """
    Un produit avec tag non synchronisé doit déclencher l'export des tags avant la mise à
    jour produit.
    """
    service = object.__new__(WCProductsService)
    service.session = MagicMock()
    service.object_repo = MagicMock()
    service.api_read = MagicMock()
    service.api_write = MagicMock()
    service.sync_log_repo = MagicMock()

    def _fake_export_tags() -> None:
        product.object_tags[0].tag.wpwc_id = 42

    service.export_tags = MagicMock(side_effect=_fake_export_tags)

    product = GeneralObjects(
        supplier_id=1,
        general_object_type="book",
        ean13="9783333333333",
        name="Produit avec tag non sync",
        description="Description",
        is_active=True,
    )
    product.prices = [
        ObjectPrices(
            price=Decimal("20.00"),
            vat_rate=VatRate(code=1, rate=20.0, label="TVA 20%", wpwc_slug="standard"),
        ),
    ]
    product.object_tags = [
        ObjectTags(
            general_object_id=1,
            tag_id=1,
            tag=Tags(name="Promo", description="Promo", wpwc_id=None),
        ),
    ]
    product.media_files = []
    service.object_repo.get_by_ref.return_value = product

    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "create": [{"id": 123, "sku": str(product.id), "name": "Produit avec tag non sync"}]
    }
    service.api_write.post.return_value = response

    result = service.update_product(7)

    assert result == 123
    service.export_tags.assert_called_once()


def test_book_payload_keeps_woo_attribute_keys() -> None:
    """Les attributs de livre doivent rester compatibles avec l’API WooCommerce."""
    book = Books(
        author="Jean Dupont",
        editor="Maison Édition",
        genre="Science-fiction",
        publication_year=2024,
        pages=128,
    )

    payload = book.to_dict_for_woo_commerce()

    first = payload["attributes"][0]
    assert first["name"] == "Auteur"
    assert first["options"] == ["Jean Dupont"]
    assert first["slug"] == "auteur"
    assert payload["attributes"][3]["slug"] == "annee-de-publication"


def test_other_object_payload_has_empty_attributes() -> None:
    """Les autres objets doivent produire une liste d'attributs vide pour WooCommerce."""
    other = OtherObjects()

    payload = other.to_dict_for_woo_commerce()

    assert payload == {"attributes": []}


def test_variation_payload_uses_wc_keys() -> None:
    """Les variations doivent envoyer les champs WooCommerce attendus pour un produit variable."""
    product = GeneralObjects(
        supplier_id=1,
        general_object_type="other",
        ean13="9781111111112",
        name="Produit variable",
        description="Description",
        object_variation_attribut="Couleur",
    )
    variation = ObjectVariations(
        id=2,
        general_object_id=10,
        name="Variation rouge",
        description="Version rouge",
        price=24.90,
        purchase_price=18.00,
        general_object=product,
    )

    payload = variation.to_dict_for_woo_commerce()

    assert "name" not in payload
    assert payload["description"] == "Version rouge"
    assert payload["sku"] == "10-2"
    assert payload["attributes"] == [
        {"name": "Couleur", "option": "Variation rouge"}
    ]
    assert payload["regular_price"] == "24.90"
    assert "sale_price" not in payload
    assert payload["manage_stock"] == "parent"
    assert payload["backorders"] == "notify"


def test_wc_parent_payload_declares_variation_attribute() -> None:
    """Le produit parent doit déclarer l'attribut et les options de ses variations actives."""
    service = object.__new__(WCProductsService)
    service.session = MagicMock()
    product = GeneralObjects(
        id=10,
        supplier_id=1,
        general_object_type="other",
        ean13="9781111111113",
        name="Produit par poids",
        description="Description",
        object_variation_attribut="Poids",
    )
    product.prices = [
        ObjectPrices(
            price=Decimal("10.00"),
            vat_rate=VatRate(code=1, rate=20.0, label="TVA 20%", wpwc_slug="standard"),
        ),
    ]
    product.object_variations = [
        ObjectVariations(name="500 g", description="Petit", price=10, is_active=True),
        ObjectVariations(name="1 kg", description="Grand", price=18, is_active=True),
        ObjectVariations(name="2 kg", description="Inactif", price=30, is_active=False),
    ]

    payload = service._build_product_payload(product)  # pylint: disable=W0212

    assert payload["type"] == "variable"
    assert {
        "name": "Poids",
        "options": ["500 g", "1 kg"],
        "visible": True,
        "variation": True,
    } in payload["attributes"]


def test_wc_product_variations_are_reconciled() -> None:
    """Les variations locales doivent être créées, mises à jour ou supprimées dans WooCommerce."""
    service = object.__new__(WCProductsService)
    service.api_read = MagicMock()
    service.api_write = MagicMock()
    service.sync_log_repo = MagicMock()

    product = GeneralObjects(
        id=10,
        supplier_id=1,
        general_object_type="other",
        ean13="9784444444444",
        name="Produit variable",
        description="Description",
        wpwc_id=42,
        object_variation_attribut="Format",
    )
    variation_to_create = ObjectVariations(
        id=101,
        general_object_id=10,
        name="Nouvelle variation",
        description="À créer",
        price=12.90,
        is_active=True,
    )
    variation_found_by_sku = ObjectVariations(
        id=102,
        general_object_id=10,
        name="Variation existante",
        description="À mettre à jour",
        price=14.90,
        is_active=True,
    )
    variation_to_delete = ObjectVariations(
        id=103,
        general_object_id=10,
        name="Variation inactive",
        description="À supprimer",
        price=9.90,
        is_active=False,
        wpwc_id=503,
    )
    product.object_variations = [
        variation_to_create,
        variation_found_by_sku,
        variation_to_delete,
    ]

    read_response = MagicMock()
    read_response.raise_for_status.return_value = None
    read_response.json.return_value = [
        {"id": 502, "sku": "10-102"},
        {"id": 503, "sku": "10-103"},
    ]
    service.api_read.get.return_value = read_response

    create_response = MagicMock()
    create_response.raise_for_status.return_value = None
    create_response.json.return_value = {"id": 501, "sku": "10-101"}
    service.api_write.post.return_value = create_response

    update_response = MagicMock()
    update_response.raise_for_status.return_value = None
    update_response.json.return_value = {"id": 502, "sku": "10-102"}
    service.api_write.put.return_value = update_response

    delete_response = MagicMock()
    delete_response.raise_for_status.return_value = None
    delete_response.json.return_value = {"id": 503, "sku": "10-103"}
    service.api_write.delete.return_value = delete_response

    service._sync_product_variations(product)  # pylint: disable=W0212

    service.api_read.get.assert_called_once_with(
        "products/42/variations",
        params={"page": 1, "per_page": 100},
    )
    service.api_write.post.assert_called_once()
    assert service.api_write.post.call_args.args[0] == "products/42/variations"
    assert service.api_write.post.call_args.kwargs["data"]["sku"] == "10-101"
    assert service.api_write.post.call_args.kwargs["data"]["attributes"] == [
        {"name": "Format", "option": "Nouvelle variation"}
    ]
    service.api_write.put.assert_called_once()
    assert service.api_write.put.call_args.args[0] == "products/42/variations/502"
    assert service.api_write.put.call_args.kwargs["data"]["sku"] == "10-102"
    service.api_write.delete.assert_called_once_with(
        "products/42/variations/503",
        params={"force": True},
    )
    assert variation_to_create.wpwc_id == 501
    assert variation_found_by_sku.wpwc_id == 502
    assert variation_to_delete.wpwc_id is None


def test_wc_diff_objects_detects_create_update_and_delete_batches() -> None:
    """Le diff local/WooCommerce doit distinguer création, mise à jour et suppression."""
    service = object.__new__(WCProductsService)
    service.session = MagicMock()

    existing = GeneralObjects(
        id=10,
        supplier_id=1,
        general_object_type="book",
        ean13="9782222222222",
        name="Produit existant",
        description="desc",
        wpwc_id=42,
    )
    existing.prices = [
        ObjectPrices(
            price=Decimal("10.00"),
            vat_rate=VatRate(code=1, rate=20.0, label="TVA 20%", wpwc_slug="standard"),
        ),
    ]
    new_product = GeneralObjects(
        id=11,
        supplier_id=1,
        general_object_type="other",
        ean13="9783333333333",
        name="Produit nouveau",
        description="desc",
    )
    new_product.prices = [
        ObjectPrices(
            price=Decimal("15.00"),
            vat_rate=VatRate(code=1, rate=20.0, label="TVA 20%", wpwc_slug="standard"),
        ),
    ]

    diff = service._diff_objects(  # pylint: disable=W0212
        [existing, new_product],
        [{"id": 42, "name": "Produit existant"}, {"id": 99, "name": "Produit distant"}],
    )

    assert len(diff) >= 1
    assert any(entry.get("update") for entry in diff)
    assert any(entry.get("create") for entry in diff)
    assert any(entry.get("delete") for entry in diff)


def test_wc_product_builds_catalog_payload_with_merged_attributes() -> None:
    """
    Le service produit doit assembler les attributs du livre et des métadonnées dans le payload WC.
    """
    service = object.__new__(WCProductsService)
    service.session = MagicMock()
    service._build_media_src = MagicMock(return_value="https://example.com/image.jpg")  # pylint: disable=W0212

    product = GeneralObjects(
        supplier_id=1,
        general_object_type="book",
        ean13="9781111111111",
        name="Catalogue test",
        description="Description standard",
    )
    product.prices = [
        ObjectPrices(
            price=Decimal("29.90"),
            vat_rate=VatRate(code=1, rate=20.0, label="TVA 20%", wpwc_slug="standard"),
        ),
    ]
    product.book = Books(
        author="Jean Dupont",
        editor="Editeur Test",
        genre="Roman",
        publication_year=2024,
        pages=240,
    )
    product.obj_metadatas = ObjMetadatas(
        general_object_id=1,
        semistructured_data={"couleur": "rouge"},
    )
    product.media_files = []

    payload = service._build_product_payload(product)  # pylint: disable=W0212

    assert payload["categories"] == [{"id": 20}]
    assert any(attr["slug"] == "auteur" for attr in payload["attributes"])
    assert any(attr["slug"] == "couleur" for attr in payload["attributes"])
    assert payload["tax_class"] == "standard"


def test_wc_product_update_fails_when_woo_returns_no_wc_id(caplog) -> None:
    """
    Une synchronisation de produit doit être considérée comme un échec si WooCommerce
    n'attribue aucun ID.
    """
    service = object.__new__(WCProductsService)
    service.session = MagicMock()
    service.object_repo = MagicMock()
    service.api_read = MagicMock()
    service.api_write = MagicMock()
    service.sync_log_repo = MagicMock()

    product = GeneralObjects(
        id=127,
        supplier_id=1,
        general_object_type="book",
        ean13="9780000000000",
        name="Produit sans id WC",
        description="desc",
        wpwc_id=None,
        is_active=True,
    )
    product.prices = [
        ObjectPrices(
            price=Decimal("29.90"),
            vat_rate=VatRate(code=1, rate=20.0, label="TVA 20%", wpwc_slug="standard"),
        ),
    ]
    service.object_repo.get_by_ref.return_value = product
    service.api_read.get.return_value = MagicMock(json=MagicMock(return_value=None))
    service._diff_objects = MagicMock(  # pylint: disable=W0212
        return_value=[{"create": [{"sku": "9999999999999"}]}]
    )
    response = MagicMock(status_code=200)
    response.text = '{"create": [{"id": 999, "sku": "AUTRE-PRODUIT"}]}'
    response.raise_for_status = MagicMock()
    response.json.return_value = {"create": [{"id": 999, "sku": "AUTRE-PRODUIT"}]}
    service.api_write.post.return_value = response

    with caplog.at_level("INFO"):
        result = service.update_product(product.id)

    assert result is None
    assert "http 200" in caplog.text.lower() or "status=200" in caplog.text.lower()
    assert "AUTRE-PRODUIT" in caplog.text or ("id" in caplog.text and "999" in caplog.text)


def test_match_line_to_wc_uses_product_and_variation_ids() -> None:
    """
    L'appariement d'une ligne locale à la ligne WooCommerce doit se faire sur product_id
    + variation_id.
    """
    product = GeneralObjects(
        id=5,
        supplier_id=1,
        general_object_type="book",
        ean13="9785555555555",
        name="Produit",
        description="desc",
        wpwc_id=33,
    )
    variation = ObjectVariations(
        id=21,
        name="Variante",
        description="",
        price=12.0,
        wpwc_id=77,
    )
    line = OrderLine(
        id=9,
        order_id=1,
        general_object_id=5,
        quantity=1,
        status="draft",
        unit_price=12.0,
        discount=0,
        vat_rate=20.0,
        create_source="test",
        general_object=product,
        object_variation=variation,
    )

    matched = _match_line_to_wc(line, {(33, 77): 888})

    assert matched == 888
    assert _match_line_to_wc(line, {(34, 77): 999}) is None
