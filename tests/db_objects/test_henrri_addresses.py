"""Tests de la construction des adresses envoyées à Henrri."""

import pytest

from db_models.objects import CustomerAddresses, Customers


def _address(**overrides) -> CustomerAddresses:
    """Construit une adresse de facturation active, surchargeable champ par champ."""
    defaults = {
        "customer_id": 1,
        "address_name": "Facturation",
        "address_line1": "12 rue du Test",
        "address_line2": "Bâtiment A",
        "city": "Paris",
        "state": "IDF",
        "postal_code": "75001",
        "country": "France",
        "is_billing": True,
        "is_shipping": False,
        "is_active": True,
    }
    defaults.update(overrides)
    return CustomerAddresses(**defaults)


def test_address_payload_contains_city_and_post_code() -> None:
    """Le payload d'adresse doit toujours transporter la ville et le code postal."""
    payload = _address().to_dict_henrri()

    assert payload["city"] == "Paris"
    assert payload["post_code"] == "75001"
    assert payload["country"] == "France"
    assert payload["address"] == "12 rue du Test\nBâtiment A"


def test_address_payload_handles_missing_second_line() -> None:
    """Une deuxième ligne d'adresse absente ne doit pas casser la sérialisation."""
    payload = _address(address_line2=None).to_dict_henrri()

    assert payload["address"] == "12 rue du Test"
    assert payload["city"] == "Paris"


def test_address_payload_omits_id_when_not_synced() -> None:
    """Une adresse jamais synchronisée ne doit pas envoyer d'identifiant Henrri."""
    payload = _address().to_dict_henrri()

    assert "id" not in payload


@pytest.mark.parametrize(
    "field,label",
    [("city", "ville"), ("postal_code", "code postal"), ("address_line1", "rue")],
)
def test_address_payload_rejects_incomplete_address(field: str, label: str) -> None:
    """Une adresse sans ville, code postal ou rue doit bloquer la synchronisation."""
    address = _address(**{field: ""})
    if field == "address_line1":
        address.address_line2 = ""

    with pytest.raises(ValueError, match=label):
        address.to_dict_henrri()


def test_customer_uses_active_billing_address() -> None:
    """Le client doit facturer sur son adresse à la fois de facturation et active."""
    customer = Customers(customer_type="part", is_active=True)
    customer.addresses = [
        _address(city="Lyon", postal_code="69000", is_billing=False),
        _address(city="Nantes", postal_code="44000", is_billing=True, is_active=False),
        _address(city="Lille", postal_code="59000", is_billing=True, is_active=True),
    ]

    address = customer.get_henrri_billing_address()

    assert address.city == "Lille"
    assert address.postal_code == "59000"


def test_customer_prefers_complete_active_billing_address() -> None:
    """Si la première adresse de facturation est incomplète, on prend la bonne adresse valide."""
    customer = Customers(customer_type="part", is_active=True)
    customer.addresses = [
        _address(city="", postal_code="", is_billing=True, is_active=True),
        _address(city="Lyon", postal_code="69000", is_billing=True, is_active=True),
    ]

    address = customer.get_henrri_billing_address()

    assert address.city == "Lyon"
    assert address.postal_code == "69000"


def test_customer_without_active_billing_address_raises() -> None:
    """Aucune adresse de facturation active ne doit permettre de facturer chez Henrri."""
    customer = Customers(customer_type="part", is_active=True)
    customer.addresses = [_address(is_billing=True, is_active=False)]

    with pytest.raises(ValueError, match="adresse de facturation active"):
        customer.get_henrri_billing_address()
