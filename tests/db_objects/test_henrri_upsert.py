"""Tests des opérations d'upsert (POST/PUT) vers Henrri."""

from unittest.mock import MagicMock

from henrri_connect.models import Address, Contact, Customer, Item

from db_models.objects import CustomerAddresses, CustomerParts, Customers
from db_models.services.henrri.customers import HenrriCustomersService
from db_models.services.henrri.products import HenrriProductsService
from db_models.services.henrri.sync import (
    sync_customer_to_henrri,
    sync_product_to_henrri,
)


def _local_customer(henrri_id: str | None = None) -> Customers:
    """Construit un client local complet et facturable."""
    customer = Customers(
        wpwc_id="91", henrri_id=henrri_id, customer_type="part", is_active=True
    )
    customer.id = 7
    customer.part = CustomerParts(customer_id=7, first_name="Julie", last_name="Benoit")
    customer.addresses = [
        CustomerAddresses(
            customer_id=7,
            address_name="Facturation",
            address_line1="15 rue de la Paix",
            address_line2="",
            city="Lille",
            state="Hauts-de-France",
            postal_code="59000",
            country="France",
            is_billing=True,
            is_shipping=False,
            is_active=True,
        )
    ]
    customer.emails = []
    customer.phones = []
    return customer


def _service_with_client() -> tuple[HenrriCustomersService, MagicMock]:
    """Retourne un service clients Henrri dont le client HTTP est simulé."""
    service = HenrriCustomersService.__new__(HenrriCustomersService)
    client = MagicMock()
    service.client = client
    return service, client


def _products_service_with_client() -> tuple[HenrriProductsService, MagicMock]:
    """Retourne un service produits Henrri dont le client HTTP est simulé."""
    service = HenrriProductsService.__new__(HenrriProductsService)
    client = MagicMock()
    service.client = client
    return service, client


def test_upsert_customer_creates_when_identifier_is_unknown() -> None:
    """Sans identifiant Henrri connu, le client doit être créé (POST)."""
    service, client = _service_with_client()
    client.customers.add.return_value = Customer(id=5001, name="Julie Benoit")

    result = service.upsert_customer(Customer(name="Julie Benoit"), None)

    assert result.id == 5001
    client.customers.add.assert_called_once()
    client.customers.modify.assert_not_called()


def test_upsert_customer_updates_when_identifier_is_known() -> None:
    """Avec un identifiant Henrri connu, le client doit être mis à jour (PUT)."""
    service, client = _service_with_client()
    client.customers.modify.return_value = Customer(id=81, name="Julie Benoit")

    result = service.upsert_customer(Customer(name="Julie Benoit"), "81")

    assert result.id == 81
    client.customers.modify.assert_called_once()
    assert client.customers.modify.call_args.args[0] == 81
    client.customers.add.assert_not_called()


def test_upsert_product_creates_then_updates() -> None:
    """Le produit doit être créé sans identifiant, puis mis à jour lorsqu'il en a un."""
    service, client = _products_service_with_client()
    item = Item(
        vat_percent=20.0,
        creation_date="2026-08-14",
        is_tax_included=False,
        purchase_price=0.0,
        is_a_group=False,
    )
    client.items.add.return_value = Item(
        id=8001,
        vat_percent=20.0,
        creation_date="2026-08-14",
        is_tax_included=False,
        purchase_price=0.0,
        is_a_group=False,
    )
    client.items.modify.return_value = Item(
        id=8001,
        vat_percent=20.0,
        creation_date="2026-08-14",
        is_tax_included=False,
        purchase_price=0.0,
        is_a_group=False,
    )

    service.upsert_product(item, None)
    service.upsert_product(item, 8001)

    client.items.add.assert_called_once()
    client.items.modify.assert_called_once()
    assert client.items.modify.call_args.args[0] == 8001


def test_sync_customer_persists_all_returned_identifiers() -> None:
    """
    Les identifiants Henrri du client, de son adresse et de son contact doivent être conservés.
    """
    customer = _local_customer()
    service = MagicMock()
    service.upsert_customer.return_value = Customer(
        id=5001,
        name="Julie Benoit",
        address=Address(
            id=701,
            city="Lille",
            post_code="59000",
            is_post_code_shared=False,
        ),
    )
    service.upsert_contact.return_value = Contact(
        id=801,
        first_name="Julie",
        last_name="Benoit",
    )

    sync_customer_to_henrri(customer, service)

    assert customer.henrri_id == "5001"
    assert customer.addresses[0].henrri_id == 701
    assert customer.part.contact_henrri_id == 801


def test_sync_customer_sends_full_address() -> None:
    """L'adresse transmise à Henrri doit contenir la rue, la ville et le code postal."""
    customer = _local_customer()
    service = MagicMock()
    service.upsert_customer.return_value = Customer(id=5001, name="Julie Benoit")
    service.upsert_contact.return_value = Contact(id=801)

    sync_customer_to_henrri(customer, service)

    sent_customer = service.upsert_customer.call_args.args[0]
    assert sent_customer.address is not None
    assert sent_customer.address.address == "15 rue de la Paix"
    assert sent_customer.address.city == "Lille"
    assert sent_customer.address.post_code == "59000"
    assert sent_customer.contacts is None
    service.upsert_contact.assert_called_once()


def test_sync_customer_updates_contact_separately() -> None:
    """Un contact existant doit être mis à jour par sa route dédiée Henrri."""
    customer = _local_customer(henrri_id="81")
    customer.part.contact_henrri_id = 801
    service = MagicMock()
    service.upsert_customer.return_value = Customer(id=81, name="Julie Benoit")
    service.upsert_contact.return_value = Contact(id=801)

    sync_customer_to_henrri(customer, service)

    assert service.upsert_contact.call_args.args[0] == 81
    assert service.upsert_contact.call_args.args[2] == 801


def test_sync_customer_passes_known_identifier_for_update() -> None:
    """Un client déjà synchronisé doit transmettre son identifiant pour déclencher un PUT."""
    customer = _local_customer(henrri_id="81")
    service = MagicMock()
    service.upsert_customer.return_value = Customer(id=81, name="Julie Benoit")

    sync_customer_to_henrri(customer, service)

    assert service.upsert_customer.call_args.args[1] == "81"


def test_sync_product_persists_returned_identifier() -> None:
    """L'identifiant produit retourné par Henrri doit être reporté en base."""
    product = MagicMock(henrri_id=None)
    product.to_dict_henrri.return_value = {
        "reference": "9780012345678",
        "description": "Livre sync",
        "is_tax_included": False,
        "selling_price_without_tax": 42.0,
        "vat_percent": 20.0,
        "creation_date": "2026-08-14",
        "id": None,
    }
    service = MagicMock()
    service.upsert_product.return_value = Item(
        id=8001,
        vat_percent=20.0,
        creation_date="2026-08-14",
        is_tax_included=False,
        purchase_price=0.0,
        is_a_group=False,
    )

    sync_product_to_henrri(product, service)

    assert product.henrri_id == 8001
