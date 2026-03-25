"""Module de tests pour les routes clients du front-end."""

import pytest   # pylint: disable=unused-import

HOME_PAGE = "<!DOCTYPE html>\n<html lang=\"fr\">\n<head>\n"
REDIRECTION = "<!doctype html>\n<html lang=en>\n<title>Redirecting...</"
FORBIDEN = "<!doctype html>\n<html lang=en>\n<title>403 Forbidden"

# +------------------------------------------------------------------------------------------------+
# |                                    Tests pour les routes classiques                            |
# +------------------------------------------------------------------------------------------------+


def test_index(client_all,
               client,  # pylint: disable=redefined-outer-name, unused-argument
               client_informatique, # pylint: disable=redefined-outer-name, unused-argument
               client_compta,   # pylint: disable=redefined-outer-name, unused-argument
               client_commercial,   # pylint: disable=redefined-outer-name, unused-argument
               client_direction):   # pylint: disable=redefined-outer-name, unused-argument
    """Test de la route d'index du module client."""
    c_list_authorized = [client_compta, client_commercial, client_direction]
    c_list_unauthorized = [client, client_informatique]
    ok_code = set()
    nokcode = set()
    for c in c_list_authorized:
        response = c.get("/customer/")
        ok_code.add(response.status_code)
    for c in c_list_unauthorized:
        response = c.get("/customer/")
        nokcode.add(response.status_code)
    assert ok_code == {200}
    assert nokcode == {302, 403}

    response = client_all.get("/customer/")

    assert response.status_code == 200
    assert response.text.startswith(HOME_PAGE)


def test_search(client_all,
                client,  # pylint: disable=redefined-outer-name, unused-argument
                client_informatique, # pylint: disable=redefined-outer-name, unused-argument
                client_compta,   # pylint: disable=redefined-outer-name, unused-argument
                client_commercial,   # pylint: disable=redefined-outer-name, unused-argument
                client_direction):   # pylint: disable=redefined-outer-name, unused-argument
    """Test de la route de recherche de clients."""
    c_list_authorized = [client_compta, client_commercial, client_direction]
    c_list_unauthorized = [client, client_informatique]
    ok_code = set()
    nokcode = set()
    for c in c_list_authorized:
        response = c.get("/customer/search")
        ok_code.add(response.status_code)
    for c in c_list_unauthorized:
        response = c.get("/customer/search")
        nokcode.add(response.status_code)
    assert ok_code == {200}
    assert nokcode == {302, 403}

    response = client_all.get("/customer/search")

    assert response.status_code == 200
    assert response.text.startswith(HOME_PAGE)


def test_create(client_all,
                client,  # pylint: disable=redefined-outer-name, unused-argument
                client_informatique, # pylint: disable=redefined-outer-name, unused-argument
                client_compta,   # pylint: disable=redefined-outer-name, unused-argument
                client_commercial,   # pylint: disable=redefined-outer-name, unused-argument
                client_direction):   # pylint: disable=redefined-outer-name, unused-argument
    """Test de la route de création de clients."""
    c_list_authorized = [client_compta, client_commercial, client_direction]
    c_list_unauthorized = [client, client_informatique]
    ok_code = set()
    nokcode = set()
    for c in c_list_authorized:
        response = c.get("/customer/create")
        ok_code.add(response.status_code)
    for c in c_list_unauthorized:
        response = c.get("/customer/create")
        nokcode.add(response.status_code)
    assert ok_code == {200}
    assert nokcode == {302, 403}

    response = client_all.get("/customer/create")

    assert response.status_code == 200
    assert response.text.startswith(HOME_PAGE)

    response_post_part = client_all.post("/customer/create",
                                         data={
                                             "customer_type": "part",
                                             "civil_title": "m",
                                             "first_name": "Test",
                                             "last_name": "Client",
                                             "date_of_birth": "1990-01-01",
                                            })
    response_post_pro = client_all.post("/customer/create",
                                        data={
                                            "customer_type": "pro",
                                            "civil_title": "",
                                            "company_name": "Test Company",
                                            "siret_number": "12345678901234",
                                            "vat_number": "FR12345678901",
                                            })
    assert response_post_part.status_code == 302
    assert response_post_part.text.startswith(REDIRECTION)
    assert response_post_pro.status_code == 302
    assert response_post_pro.text.startswith(REDIRECTION)


def test_view(client_all,
              client,  # pylint: disable=redefined-outer-name, unused-argument
              client_informatique, # pylint: disable=redefined-outer-name, unused-argument
              client_compta,   # pylint: disable=redefined-outer-name, unused-argument
              client_commercial,   # pylint: disable=redefined-outer-name, unused-argument
              client_direction,
              complete_customer_pro):   # pylint: disable=redefined-outer-name, unused-argument
    """Test de la route d'affichage de la fiche client."""
    c_list_authorized = [client_compta, client_commercial, client_direction]
    c_list_unauthorized = [client, client_informatique]
    ok_code = set()
    nokcode = set()
    for c in c_list_authorized:
        response = c.get(f"/customer/{complete_customer_pro.id}")
        ok_code.add(response.status_code)
    for c in c_list_unauthorized:
        response = c.get(f"/customer/{complete_customer_pro.id}")
        nokcode.add(response.status_code)
    assert ok_code == {200}
    assert nokcode == {302, 403}

    response = client_all.get(f"/customer/{complete_customer_pro.id}")

    assert response.status_code == 200
    assert response.text.startswith(HOME_PAGE)

# +------------------------------------------------------------------------------------------------+
# |                                    Tests pour les routes data                                  |
# +------------------------------------------------------------------------------------------------+


def test_search_fast(complete_customer_pro,
                     complete_customer_part,
                     client_all,
                     client,
                     client_informatique,
                     client_compta,
                     client_commercial,
                     client_direction
                     ):  # pylint: disable=redefined-outer-name, unused-argument
    """Test de la route de recherche rapide de clients."""
    authorized_clients = [client_all, client_compta, client_commercial, client_direction]
    unauthorized_clients = [client, client_informatique]
    ok_code = set()
    nok_code = set()
    for c in authorized_clients:
        response = c.get("/customer/data/search/fast", query_string={"q": "tes"})
        ok_code.add(response.status_code)
    for c in unauthorized_clients:
        response = c.get("/customer/data/search/fast", query_string={"q": "tes"})
        nok_code.add(response.status_code)
    assert ok_code == {200}
    assert nok_code == {302, 403}

    response = client_all.get("/customer/data/search/fast", query_string={"q": "tes"})
    response_no_result = client_all.get("/customer/data/search/fast", query_string={"q": "xyz"})
    response_empty_query = client_all.get("/customer/data/search/fast", query_string={"q": ""})
    response_particulier = client_all.get("/customer/data/search/fast", query_string={"q": "jan"})

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1  # On s'attend à un seul client correspondant à la recherche rapide
    assert data[0]["customer_type"] == "pro"  # Le client trouvé doit être de type professionnel
    assert response_no_result.status_code == response_empty_query.status_code == 200
    data_no_result = response_no_result.get_json()
    data_empty_query = response_empty_query.get_json()
    assert isinstance(data_no_result, list)
    assert isinstance(data_empty_query, list)
    assert len(data_no_result) == 0  # On s'attend à aucun résultat
    assert len(data_empty_query) == 0  # On s'attend à aucun résultat
    assert response_particulier.status_code == 200
    data_particulier = response_particulier.get_json()
    assert isinstance(data_particulier, list)
    assert len(data_particulier) == 1  # On s'attend à un seul client particulier
    assert data_particulier[0]["customer_type"] == "part"
