"""Tests des payloads WooCommerce générés par les modèles métier."""

import struct
import zlib
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app_front.blueprints.woocommerce.routes import serve_media

from db_models.objects import (
    Books,
    CustomerMails,
    CustomerParts,
    Customers,
    GeneralObjects,
    MediaFiles,
    ObjMetadatas,
    ObjectPrices,
    ObjectTags,
    ObjectVariations,
    Order,
    OrderLine,
    OtherObjects,
    Tags,
    VatRate,
)
from db_models.repositories.customers import CustomersRepository
from db_models.services.woo_commerce.customers import WCCustomersService
from db_models.services.woo_commerce.orders import WCOrdersService, _match_line_to_wc
from db_models.services.woo_commerce.products import WCProductsService


def test_wc_customer_sync_links_existing_customer_by_email() -> None:
    """Un client WooCommerce existant doit être rattaché à son identifiant distant."""
    service = object.__new__(WCCustomersService)
    service.api_read = MagicMock()
    service.api_write = MagicMock()
    service.customer_repo = MagicMock()
    customer = MagicMock(id=11)
    customer.get_wpwc_mail.return_value = "e.torresani@mail.com"
    service.api_read.get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=[{"id": 42}]),
    )
    service.customer_repo.update_info.return_value = customer

    result = service.create_wpwc_customer_if_not_exists(customer)

    assert result is customer
    service.api_write.post.assert_not_called()
    service.customer_repo.update_info.assert_called_once_with(11, {"wpwc_id": 42})


def test_wc_customer_sync_creates_and_links_missing_customer() -> None:
    """Un client absent de WooCommerce doit être créé puis rattaché à son identifiant."""
    service = object.__new__(WCCustomersService)
    service.api_read = MagicMock()
    service.api_write = MagicMock()
    service.customer_repo = MagicMock()
    customer = MagicMock(id=11)
    customer.get_wpwc_mail.return_value = "e.torresani@mail.com"
    customer.to_dict_for_wpwc.return_value = {"email": "e.torresani@mail.com"}
    service.api_read.get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=[]),
    )
    service.api_write.post.return_value = MagicMock(
        status_code=201,
        json=MagicMock(return_value={"id": 43}),
    )
    service.customer_repo.update_info.return_value = customer

    result = service.create_wpwc_customer_if_not_exists(customer)

    assert result is customer
    service.api_write.post.assert_called_once_with(
        "customers", data={"email": "e.torresani@mail.com"}
    )
    service.customer_repo.update_info.assert_called_once_with(11, {"wpwc_id": 43})


def test_customer_repository_updates_partner_identifiers() -> None:
    """Les identifiants partenaires doivent être enregistrés sur le client principal."""
    session = MagicMock()
    repository = CustomersRepository(session)
    customer = Customers(id=11, customer_type="part")
    customer.part = CustomerParts(customer_id=11, first_name="Etienne", last_name="Torresani")
    repository.get_by_id = MagicMock(return_value=customer)  # type: ignore[method-assign]

    updated = repository.update_info(11, {"wpwc_id": 42, "henrri_id": "3035"})

    assert updated.wpwc_id == 42
    assert updated.henrri_id == "3035"
    session.commit.assert_called_once()

def test_general_object_payload_uses_wc_tax_slug(
        book_product: GeneralObjects    # pylint: disable=W0621
    ) -> None:
    """Le payload produit doit utiliser le slug WooCommerce de la TVA, pas le label humain."""
    payload = book_product.to_dict_for_woo_commerce()

    assert payload["tax_class"] == "taux-reduit"
    assert payload["regular_price"] == "19.99"
    assert payload["sku"] is None


def test_metadata_payload_uses_woo_attribute_shape() -> None:
    """
    Les métadonnées doivent être converties en attributs WooCommerce de type product
    attribute.
    """
    metadata = ObjMetadatas(semistructured_data={"couleur": "rouge", "poids": "500g"})

    payload = metadata.to_dict_for_woo_commerce()

    assert payload is not None
    assert payload["attributes"][0]["name"] == "couleur"
    assert payload["attributes"][0]["options"] == ["rouge"]
    assert payload["attributes"][0]["slug"] == "couleur"
    assert payload["attributes"][1]["name"] == "poids"
    assert payload["attributes"][1]["options"] == ["500g"]


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
    variation = ObjectVariations(
        name="Variation rouge",
        description="Version rouge",
        price=24.90,
        purchase_price=18.00,
    )

    payload = variation.to_dict_for_woo_commerce()

    assert payload["name"] == "Variation rouge"
    assert payload["regular_price"] == "24.90"
    assert payload["sale_price"] == "24.90"
    assert payload["manage_stock"] == "parent"
    assert payload["backorders"] == "notify"


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
            tag=Tags(
                name="Promo",
                description="Promo",
                wpwc_id=42,
            ),
        ),
        ObjectTags(
            general_object_id=1,
            tag_id=2,
            tag=Tags(
                name="Nouveauté",
                description="Nouveauté",
                wpwc_id=77,
            ),
        ),
    ]
    product.media_files = []

    payload = service._build_product_payload(product)  # pylint: disable=W0212

    assert payload["tags"] == [{"id": 42}, {"id": 77}]


def test_update_product_syncs_missing_wc_tags_before_export() -> None:
    """
    Un produit avec tag non synchronisé doit déclencher l'export des tags avant la mise à jour
    produit.
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
            tag=Tags(
                name="Promo",
                description="Promo",
                wpwc_id=None,
            ),
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


def test_order_line_payload_uses_wc_tax_class_and_variation_id(
    woo_book_product: GeneralObjects,
) -> None:
    """La ligne de commande doit conserver la tax_class et l'ID de variation WooCommerce."""
    product = woo_book_product
    variation = ObjectVariations(id=7, name="Variante A", description="", price=15.00, wpwc_id=21)
    line = OrderLine(
        id=10,
        order_id=1,
        general_object_id=99,
        quantity=2,
        status="draft",
        unit_price=15.0,
        discount=0,
        vat_rate=20.0,
        create_source="test",
        general_object=product,
        object_variation=variation,
    )

    payload = line.to_dict_for_woo_commerce()

    assert payload["product_id"] == 150
    assert payload["tax_class"] == "standard"
    assert payload["variation_id"] == 21
    assert payload["subtotal"] == "30.0"
    assert payload["total"] == "30.0"


def test_order_line_payload_raises_clear_error_when_product_not_synced_to_woo(
    woo_book_product: GeneralObjects,
) -> None:
    """Une ligne de commande sans produit WooCommerce doit produire un message exploitables."""
    product = woo_book_product
    product.wpwc_id = None
    line = OrderLine(
        id=10,
        order_id=1,
        general_object_id=99,
        quantity=2,
        status="draft",
        unit_price=15.0,
        discount=0,
        vat_rate=20.0,
        create_source="test",
        general_object=product,
    )

    with pytest.raises(ValueError, match="non synchronisé.*WooCommerce|wpwc_id"):
        line.to_dict_for_woo_commerce()


def test_wc_product_payload_builds_catalog_payload_with_merged_attributes() -> None:
    """
    Le service produit doit assembler les attributs du livre et des métadonnées dans le
    payload WC.
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
            vat_rate=VatRate(
                code=1,
                rate=20.0,
                label="TVA 20%",
                wpwc_slug="standard"
            ),
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
        semistructured_data={
            "couleur": "rouge",
            "poids": "500g"
        },
    )
    product.media_files = []

    payload = service._build_product_payload(product)   # pylint: disable=W0212

    assert payload["categories"] == [{"id": 20}]
    assert any(attr["slug"] == "auteur" for attr in payload["attributes"])
    assert any(attr["slug"] == "couleur" for attr in payload["attributes"])
    assert payload["tax_class"] == "standard"


def test_wc_diff_objects_detects_create_update_and_delete_batches() -> None:
    """
    Le diff local/WooCommerce doit distinguer correctement création, mise à jour et
    suppression.
    """
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
            vat_rate=VatRate(
                code=1,
                rate=20.0,
                label="TVA 20%",
                wpwc_slug="standard",
            ),
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
            vat_rate=VatRate(
                code=1,
                rate=20.0,
                label="TVA 20%",
                wpwc_slug="standard"
            ),
        ),
    ]

    diff = service._WCProductsService__diff_objects(    # type: ignore  # pylint: disable=W0212
        [existing, new_product],
        [{"id": 42, "name": "Produit existant"}, {"id": 99, "name": "Produit distant"}],
    )

    assert len(diff) >= 1
    assert any(entry.get("update") for entry in diff)
    assert any(entry.get("create") for entry in diff)
    assert any(entry.get("delete") for entry in diff)


def test_order_payload_uses_wc_customer_and_line_contract(
        wc_customer_pro: Customers    # pylint: disable=W0621
    ) -> None:
    """
    La commande doit produire le payload WooCommerce attendu avec l'email, l'adresse et les lignes.
    """
    customer = wc_customer_pro
    product = GeneralObjects(
        id=12,
        supplier_id=1,
        general_object_type="book",
        ean13="9784444444444",
        name="Produit commande",
        description="Commandable",
        wpwc_id=120,
    )
    product.prices = [
        ObjectPrices(
            price=Decimal("16.00"),
            vat_rate=VatRate(
                code=1,
                rate=20.0,
                label="TVA 20%",
                wpwc_slug="standard",
            ),
        ),
    ]
    line = OrderLine(
        id=7,
        order_id=1,
        general_object_id=12,
        quantity=2,
        status="draft",
        unit_price=16.0,
        discount=0,
        vat_rate=20.0,
        create_source="test",
        general_object=product,
    )
    order = Order(
        id=1,
        reference="CMD-2401-00001",
        customer_id=999,
        invoice_address_id=1,
        delivery_address_id=1,
        status="draft",
        create_source="test",
        customer=customer,
        invoice_address=customer.addresses[0],
        delivery_address=customer.addresses[0],
        order_lines=[line],
    )

    payload = order.to_dict_for_woo_commerce()

    assert payload["customer_id"] == "42"
    assert payload["billing"]["email"] == "acme@example.com"
    assert payload["shipping"]["postcode"] == "75001"
    assert payload["line_items"][0]["product_id"] == 120
    assert payload["metadata"]["_billing_wooccm10"] == "Professionnel"


def test_cancelled_order_payload_updates_status_without_zeroing_lines(
        wc_customer_pro: Customers,
    ) -> None:
    """Une annulation doit changer le statut WC sans altérer la quantité des lignes."""
    product = GeneralObjects(
        id=12,
        supplier_id=1,
        general_object_type="book",
        ean13="9784444444444",
        name="Produit annulé",
        description="Commandable",
        wpwc_id=120,
    )
    line = OrderLine(
        id=7,
        order_id=1,
        general_object_id=12,
        quantity=2,
        status="cancelled",
        unit_price=16.0,
        discount=0,
        vat_rate=20.0,
        create_source="test",
        general_object=product,
        wpwc_id=70,
    )
    order = Order(
        id=1,
        reference="CMD-2401-00002",
        customer_id=999,
        status="cancelled",
        create_source="test",
        customer=wc_customer_pro,
        order_lines=[line],
    )

    payload = order.to_dict_for_woo_commerce()

    assert payload["status"] == "cancelled"
    assert payload["line_items"] == [{"name": "Produit annulé", "product_id": 120,
                                       "quantity": 2, "subtotal": "32.0", "total": "32.0",
                                       "id": 70}]


def test_returned_order_payload_uses_refunded_status(wc_customer_pro: Customers) -> None:
    """Une commande retournée doit être synchronisée comme remboursée dans WooCommerce."""
    order = Order(
        id=1,
        reference="RET-2401-00001",
        customer_id=999,
        status="returned",
        create_source="test",
        customer=wc_customer_pro,
        order_lines=[],
    )

    assert order.to_dict_for_woo_commerce()["status"] == "refunded"


def test_match_line_to_wc_uses_product_and_variation_ids() -> None:
    """
    L'appariement d'une ligne locale à la ligne WooCommerce doit se faire sur
    product_id + variation_id.
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


def test_wc_orders_service_uses_customer_woo_email_and_remote_customer_payload(
        wc_customer_part: Customers    # pylint: disable=W0621
    ) -> None:
    """Le service de commande doit utiliser l'email WooCommerce du client et le payload distant."""
    service = object.__new__(WCOrdersService)
    service.customer_repo = MagicMock()
    service.customer_service = MagicMock()
    service.api_write = MagicMock()
    service.order_repo = MagicMock()

    customer = wc_customer_part
    customer.id = 12
    customer.part.customer_id = 12
    customer.emails[0].customer_id = 12
    customer.addresses[0].customer_id = 12
    service.customer_repo.get_by_email.return_value = customer
    service.customer_service.get_by_mail.return_value = {
        "id": 42,
        "email": "alice@example.com",
    }

    order = Order(
        id=1,
        reference="CMD-2501-00001",
        customer_id=12,
        invoice_address_id=1,
        delivery_address_id=1,
        status="draft",
        create_source="web",
        customer=customer,
        invoice_address=customer.addresses[0],
        delivery_address=customer.addresses[0],
        order_lines=[],
    )
    created_order = Order(
        id=1,
        reference="CMD-2501-00001",
        customer_id=12,
        status="draft",
        create_source="web",
        customer=customer,
        wpwc_id=99,
    )
    service.order_repo.create_from_woo_commerce.return_value = created_order
    response = MagicMock(status_code=201)
    response.json.return_value = {"id": 99, "customer_id": 42, "line_items": []}
    service.api_write.post.return_value = response

    result = service.create_order(order)

    assert result.wpwc_id == 99
    service.customer_service.diff_customer.assert_called_once_with(
        local_customer=customer,
        wc_customer={"id": 42, "email": "alice@example.com"},
        from_local=True,
    )


def test_wc_orders_service_creates_missing_remote_customer_when_local_customer_exists() -> None:
    """
    Si le client local existe mais pas dans WooCommerce, le service doit créer le client distant.
    """
    service = object.__new__(WCOrdersService)
    service.customer_repo = MagicMock()
    service.customer_service = MagicMock()
    service.api_write = MagicMock()
    service.order_repo = MagicMock()

    customer = Customers(
        id=77,
        wpwc_id=None,
        customer_type="part",
    )
    customer.part = CustomerParts(
        customer_id=77,
        first_name="Bob",
        last_name="Martin",
    )
    customer.emails = [
        CustomerMails(
            customer_id=77,
            email_name="WooCommerce",
            email="bob@example.com",
            is_active=True,
        ),
    ]

    service.customer_repo.get_by_email.return_value = customer
    service.customer_service.get_by_mail.return_value = None
    response = MagicMock(status_code=201)
    response.json.return_value = {"id": 321, "customer_id": 77, "line_items": []}
    service.api_write.post.return_value = response

    order = Order(
        id=5,
        reference="CMD-2501-00002",
        customer_id=77,
        status="draft",
        create_source="web",
        customer=customer,
        order_lines=[],
    )

    service.create_order(order)

    service.customer_service.create_wpwc_customer_if_not_exists.assert_called_once_with(customer)


def test_wc_orders_service_preserves_existing_line_ids() -> None:
    """Le synchroniseur conserve la liaison WooCommerce déjà connue d'une ligne."""
    service = object.__new__(WCOrdersService)
    product = GeneralObjects(
        id=8,
        supplier_id=1,
        general_object_type="book",
        ean13="9786666666666",
        name="Produit ligne",
        description="desc",
        wpwc_id=101,
    )
    variation = ObjectVariations(
        id=31,
        name="Variation B",
        description="",
        price=12.0,
        wpwc_id=201,
    )
    line = OrderLine(
        id=11,
        order_id=1,
        general_object_id=8,
        quantity=1,
        status="draft",
        unit_price=12.0,
        discount=0,
        vat_rate=20.0,
        create_source="test",
        general_object=product,
        object_variation=variation,
        wpwc_id=999,
    )
    order = Order(
        id=2,
        reference="CMD-2501-00003",
        customer_id=12,
        status="draft",
        create_source="test",
        order_lines=[line],
        customer=Customers(
            id=12,
            customer_type="part",
        ),
    )

    service._sync_line_ids( # pylint: disable=W0212
        order,
        [
            {
                "id": 77,
                "product_id": 101,
                "variation_id": 201,
            },
        ],
        clear_all_cancelled=False,
    )

    assert line.wpwc_id == 999


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
            vat_rate=VatRate(
                code=1,
                rate=20.0,
                label="TVA 20%",
                wpwc_slug="standard",
            ),
        ),
    ]
    service.object_repo.get_by_ref.return_value = product
    service.api_read.get.return_value = MagicMock(json=MagicMock(return_value=None))
    service._WCProductsService__diff_objects = MagicMock(  # type: ignore[attr-defined] # pylint: disable=W0212
        return_value=[
            {"create": [
                    {
                        "sku": "9999999999999",
                    },
                ],
            },
        ]
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


def test_wc_product_build_media_src_uses_internal_public_host_when_env_missing(monkeypatch) -> None:
    """
    Sans FRONT_BASE_URL explicit, le service doit utiliser le host interne public attendu par
    WooCommerce.
    """
    monkeypatch.setattr("db_models.services.woo_commerce.products._FRONT_BASE_URL", "")
    service = object.__new__(WCProductsService)
    service.session = MagicMock()
    media = MagicMock(spec=MediaFiles)
    media.id = 42
    media.is_local = True
    media.file_link = "29334045_main.jpg"

    url = service._build_media_src(media)  # pylint: disable=W0212

    assert "https://internal.editions-sauvetage.fr/woocommerce/media/" in url
    assert "/29334045_main.jpg" in url


def test_woo_media_route_resolves_media_by_id_and_serves_file(monkeypatch) -> None:
    """La route WooCommerce doit lire le média via son id, pas via un filtre invalide."""
    monkeypatch.setattr("app_front.blueprints.woocommerce.routes._MEDIA_UPLOAD_DIR", "/tmp/images")
    session = MagicMock()
    monkeypatch.setattr(
        "app_front.blueprints.woocommerce.routes.db_conf.get_main_session",
        lambda: session
    )

    token_record = MagicMock()
    token_record.is_valid.return_value = True
    token_record.media_file_id = 77

    media_file = MagicMock()
    media_file.file_link = "cover.jpg"

    with patch(
            "app_front.blueprints.woocommerce.routes.MediaAccessTokenRepository"
        ) as token_repo_cls, \
         patch(
            "app_front.blueprints.woocommerce.routes.MediaRepository"
        ) as media_repo_cls, \
         patch(
            "app_front.blueprints.woocommerce.routes.send_from_directory",
            return_value="OK",
        ):
        token_repo = token_repo_cls.return_value
        token_repo.get.return_value = token_record
        media_repo = media_repo_cls.return_value
        media_repo.get_by_id.return_value = media_file

        response = serve_media("valid-token", "cover.jpg")

    assert response == "OK"
    media_repo.get_by_id.assert_called_once_with(77)


def test_wc_product_build_media_src_uses_token_for_absolute_local_paths(monkeypatch) -> None:
    """
    Un chemin de fichier local absolu doit quand même être servi via le jeton publique
    afin d'éviter d'envoyer une URL invalide à WooCommerce.
    """
    monkeypatch.setattr("db_models.services.woo_commerce.products._FRONT_BASE_URL", "")
    service = object.__new__(WCProductsService)
    service.session = MagicMock()
    media = MagicMock(spec=MediaFiles)
    media.id = 43
    media.is_local = False
    media.file_link = "/app/data-seed/images/29334045_main.jpg"

    with patch("db_models.services.woo_commerce.products.MediaAccessTokenRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.get_last_by_media_id.return_value = None
        repo.create.return_value = MagicMock(token="token-abc123")

        url = service._build_media_src(media)  # pylint: disable=W0212
    base_url = "https://internal.editions-sauvetage.fr/woocommerce/media"
    assert f"{base_url}/token-abc123/29334045_main.jpg" in url
    assert "/app/data-seed/images/" not in url


def test_woo_media_route_uses_basename_for_local_file(monkeypatch) -> None:
    """Une URL de média historique avec chemin absolu doit être servie via son nom de fichier."""
    monkeypatch.setattr(
        "app_front.blueprints.woocommerce.routes._MEDIA_UPLOAD_DIR",
        "/tmp/images",
    )
    monkeypatch.setattr(
        "app_front.blueprints.woocommerce.routes.db_conf.get_main_session",
        MagicMock()
    )

    token_record = MagicMock()
    token_record.is_valid.return_value = True
    token_record.media_file_id = 77

    media_file = MagicMock()
    media_file.file_link = "/app/data-seed/images/29334045_main.jpg"

    with patch(
            "app_front.blueprints.woocommerce.routes.MediaAccessTokenRepository"
        ) as token_repo_cls, \
         patch(
            "app_front.blueprints.woocommerce.routes.MediaRepository"
        ) as media_repo_cls, \
         patch(
            "app_front.blueprints.woocommerce.routes.send_from_directory",
            return_value="OK"
        ) as send_mock:
        token_repo = token_repo_cls.return_value
        token_repo.get.return_value = token_record
        media_repo = media_repo_cls.return_value
        media_repo.get_by_id.return_value = media_file

        response = serve_media("valid-token", "29334045_main.jpg")

    assert response == "OK"
    send_mock.assert_called_once_with("/tmp/images", "29334045_main.jpg")


def _make_png_bytes() -> bytes:
    """Crée un PNG minimal, valide et indépendant de Pillow."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw_scanline = b"\x00\x00\x00\x00\x00"
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw_scanline))
        + chunk(b"IEND", b"")
    )


def test_woo_media_route_serves_existing_absolute_local_file(monkeypatch, tmp_path) -> None:
    """
    Quand le média historique est un chemin absolu existant, la route doit servir ce fichier
    lui-même.
    """
    image_path = tmp_path / "29334045_main.png"
    image_path.write_bytes(_make_png_bytes())
    monkeypatch.setattr(
        "app_front.blueprints.woocommerce.routes._MEDIA_UPLOAD_DIR",
        str(tmp_path)
    )
    monkeypatch.setattr(
        "app_front.blueprints.woocommerce.routes.db_conf.get_main_session",
        MagicMock()
    )

    token_record = MagicMock()
    token_record.is_valid.return_value = True
    token_record.media_file_id = 77

    media_file = MagicMock()
    media_file.file_link = str(image_path)
    media_file.file_type = "img"

    with patch(
            "app_front.blueprints.woocommerce.routes.MediaAccessTokenRepository",
        ) as token_repo_cls, \
         patch(
            "app_front.blueprints.woocommerce.routes.MediaRepository",
        ) as media_repo_cls, \
         patch(
            "app_front.blueprints.woocommerce.routes.send_file",
            return_value="OK",
        ) as send_file_mock:
        token_repo = token_repo_cls.return_value
        token_repo.get.return_value = token_record
        media_repo = media_repo_cls.return_value
        media_repo.get_by_id.return_value = media_file

        response = serve_media("valid-token", image_path.name)

    assert response == "OK"
    send_file_mock.assert_called_once_with(str(image_path), mimetype="image/png")


def test_woo_media_route_detects_real_mime_from_file_content(monkeypatch, tmp_path) -> None:
    """Le type MIME réel du fichier doit prévaloir sur l'étiquette métier `img`."""
    image_path = tmp_path / "example.png"
    image_path.write_bytes(_make_png_bytes())

    monkeypatch.setattr(
        "app_front.blueprints.woocommerce.routes._MEDIA_UPLOAD_DIR",
        str(tmp_path),
    )
    monkeypatch.setattr(
        "app_front.blueprints.woocommerce.routes.db_conf.get_main_session",
        MagicMock(),
    )

    token_record = MagicMock()
    token_record.is_valid.return_value = True
    token_record.media_file_id = 77

    media_file = MagicMock()
    media_file.file_link = str(image_path)
    media_file.file_type = "img"

    with patch(
        "app_front.blueprints.woocommerce.routes.MediaAccessTokenRepository",
    ) as token_repo_cls, \
         patch(
        "app_front.blueprints.woocommerce.routes.MediaRepository",
    ) as media_repo_cls, \
         patch(
        "app_front.blueprints.woocommerce.routes.send_file",
        return_value="OK",
    ) as send_file_mock:
        token_repo = token_repo_cls.return_value
        token_repo.get.return_value = token_record
        media_repo = media_repo_cls.return_value
        media_repo.get_by_id.return_value = media_file

        response = serve_media("valid-token", image_path.name)

    assert response == "OK"
    send_file_mock.assert_called_once_with(str(image_path), mimetype="image/png")


def test_wc_orders_service_creates_missing_products_before_push() -> None:
    """
    Le push d'une commande doit créer les produits WooCommerce manquants avant de serialiser la
    commande.
    """
    service = object.__new__(WCOrdersService)
    service.session = MagicMock()
    service.api_read = MagicMock()
    service.api_write = MagicMock()
    service.sync_log_repo = MagicMock()
    service.product_service = MagicMock()   # type: ignore

    product = GeneralObjects(
        id=9,
        supplier_id=1,
        general_object_type="book",
        ean13="9788888888888",
        name="Produit auto-sync",
        description="desc",
        wpwc_id=None,
    )
    line = OrderLine(
        id=12,
        order_id=2,
        general_object_id=9,
        quantity=2,
        status="draft",
        unit_price=10.0,
        discount=0,
        vat_rate=20.0,
        create_source="test",
        general_object=product,
        wpwc_id=50,
    )
    customer = Customers(
        id=12,
        wpwc_id="42",
        customer_type="part",
    )
    customer.emails = [
        CustomerMails(
            customer_id=12,
            email_name="WooCommerce",
            email="x@example.com",
            is_active=True,
        ),
    ]
    order = Order(
        id=2,
        reference="CMD-2501-00005",
        customer_id=12,
        status="draft",
        create_source="test",
        customer=customer,
        order_lines=[line],
        wpwc_id=221,
    )
    service.api_write.put.return_value = MagicMock(
        status_code=200,
        json=MagicMock(
            return_value={
                "id": 221,
                "line_items": [{"id": 50, "product_id": 111, "variation_id": 0}],
            },
        ),
    )
    service.product_service.update_product.side_effect = (  # type: ignore
        lambda pid: setattr(product, "wpwc_id", 111)
    )

    success, error = service.push_order(order)

    assert success is True
    assert error is None
    service.product_service.update_product.assert_called_once_with(product.id)  # type: ignore


def test_wc_orders_service_push_order_updates_remote_order_and_logs_success() -> None:
    """Le push de commande doit appeler le bon endpoint de mise à jour et journaliser le succès."""
    service = object.__new__(WCOrdersService)
    service.session = MagicMock()
    service.api_read = MagicMock()
    service.api_write = MagicMock()
    service.sync_log_repo = MagicMock()

    product = GeneralObjects(
        id=9,
        supplier_id=1,
        general_object_type="book",
        ean13="9787777777777",
        name="Produit push",
        description="desc",
        wpwc_id=111,
    )
    line = OrderLine(
        id=12,
        order_id=2,
        general_object_id=9,
        quantity=2,
        status="draft",
        unit_price=10.0,
        discount=0,
        vat_rate=20.0,
        create_source="test",
        general_object=product,
        wpwc_id=50,
    )
    customer = Customers(
        id=12,
        wpwc_id="42",
        customer_type="part",
    )
    customer.emails = [
        CustomerMails(
            customer_id=12,
            email_name="WooCommerce",
            email="x@example.com",
            is_active=True,
        ),
    ]
    order = Order(
        id=2,
        reference="CMD-2501-00004",
        customer_id=12,
        status="draft",
        create_source="test",
        customer=customer,
        order_lines=[line],
        wpwc_id=221,
    )
    service.api_read.get.return_value = MagicMock(
        status_code=200,
        json=MagicMock(
            return_value={
                "line_items": [
                    {
                        "id": 50,
                        "product_id": 111,
                        "variation_id": 0
                    }
                ]
            }
        ),
    )
    service.api_write.put.return_value = MagicMock(
        status_code=200,
        json=MagicMock(
            return_value={
                "id": 221,
                "line_items": [
                    {
                        "id": 50,
                        "product_id": 111,
                        "variation_id": 0,
                    },
                ],
            },
        ),
    )

    success, error = service.push_order(order)

    assert success is True
    assert error is None
    service.api_write.put.assert_called_once()
    service.sync_log_repo.log_order.assert_called_with(
        order_id=order.id,
        external_id="221",
        sync_direction="outbound",
        operation="update",
        sync_status="success",
    )


def test_customer_payload_and_repo_match_woo_customer_id(
        wc_customer_part: Customers    #pylint: disable=W0621
    ) -> None:
    """
    Le client doit produire le payload attendu par WooCommerce et être retrouvable par son ID WC.
    """
    customer = wc_customer_part
    customer.wpwc_id = "42"
    payload = customer.to_dict_for_wpwc()

    assert payload["email"] == "alice@example.com"
    assert payload["billing"]["postcode"] == "75000"
    assert payload["shipping"]["city"] == "Paris"
    assert payload["meta_data"][0]["key"] == "billing_wooccm10"

    repo = CustomersRepository.__new__(CustomersRepository)
    repo.session = MagicMock()
    repo.session.execute.return_value.scalars.return_value.first.return_value = customer

    found = repo.get_by_wpwc_id("42")

    assert found is customer
