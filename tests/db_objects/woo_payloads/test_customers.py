"""Tests sur les payloads et repo WooCommerce clients."""

from unittest.mock import MagicMock

from db_models.repositories.customers import CustomersRepository


def test_customer_payload_and_repo_match_woo_customer_id(wc_customer_part) -> None:
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
