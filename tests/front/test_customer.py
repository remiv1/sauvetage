"""Module de tests pour les routes clients du front-end."""

from collections import namedtuple
import pytest   # pylint: disable=unused-import

HOME_PAGE = "<!DOCTYPE html>\n<html lang=\"fr\">\n<head>\n"
REDIRECTION = "<!doctype html>\n<html lang=en>\n<title>Redirecting...</"
FORBIDEN = "<!doctype html>\n<html lang=en>\n<title>403 Forbidden"

# +------------------------------------------------------------------------------------------------+
# |                                    Tests pour les routes classiques                            |
# +------------------------------------------------------------------------------------------------+
CUSTOMER = {
    "customer_type": "part",
    "civil_title": "m",
    "first_name": "Jean",
    "last_name": "Dupont",
    "date_of_birth": "1990-01-01"
    }
ADDRESS = {
    "address_name": "Domicile",
    "address_line1": "234 Rue de Test",
    "address_line2": "Appartement 5",
    "city": "Testville Patch",
    "state": "Test State Patch",
    "postal_code": "54321",
    "country": "Test Country Patch",
    "is_billing": False,
    "is_shipping": True,
}
MAIL_CREATE = {
    "email_name": "Secondaire",
    "email": "test@example.com",
    "is_active": True,
}
MAIL_UPDATE = {
    "email_name": "Secondaire maj",
    "email": "test.updated@example.com",
    "is_active": True,
}
PHONE_CREATE = {
    "phone_name": "Mobile",
    "phone_number": "0123456789",
    "is_active": True,
}
PHONE_UPDATE = {
    "phone_name": "Mobile maj",
    "phone_number": "0123456799",
    "is_active": True,
}
PART = "complete_customer_part"
PRO = "complete_customer_pro"
Route = namedtuple("Route",
                   "path methods data customer_fixture contact_attr return_start is_form code")
ROUTES_TO_TEST = [
    Route("/", ["get"], None, None, None, True, False, 200),
    Route("/search", ["get"], None, None, None, True, False, 200),
    Route("/create", ["post"], CUSTOMER, PART, None, False, True, 300),
    Route("/create", ["get"], CUSTOMER, PART, None, True, True, 200),
    Route("/{id_c}", ["get"], None, PART, None, True, False, 200),
    Route("/data/search/fast", ["get"], {"q": "tes"}, PRO, None, False, False, 200),
    Route("/data/search/long", ["get"], {"name": "jan"}, PART, None, False, False, 200),
    Route("/data/{id_c}", ["get"], None, PART, None, False, False, 200),
    Route("/data/{id_c}/info", ["patch"], CUSTOMER, PART, None, False, False, 200),
    Route("/data/{id_c}/addresses", ["get"], None, PART, None, False, False, 200),
    Route("/data/{id_c}/address", ["post"], ADDRESS, PART, None, False, False, 200),
    Route("/data/{id_c}/address/{id_co}", ["patch"], ADDRESS, PART, "addresses", False, False, 200),
    Route("/data/{id_c}/emails", ["get"], None, PART, None, False, False, 200),
    Route("/data/{id_c}/email", ["post"], MAIL_CREATE, PART, None, False, False, 200),
    Route("/data/{id_c}/email/{id_co}", ["patch"], MAIL_UPDATE, PART, "emails", False, False, 200),
    Route("/data/{id_c}/phones", ["get"], None, PART, None, False, False, 200),
    Route("/data/{id_c}/phone", ["post"], PHONE_CREATE, PART, None, False, False, 200),
    Route("/data/{id_c}/phone/{id_co}", ["patch"], PHONE_UPDATE, PART, "phones", False, False, 200),
    Route("/data/{id_c}/activate", ["post"], None, PART, None, False, False, 200),
    Route("/data/{id_c}/deactivate", ["post"], None, PART, None, False, False, 200),
]

def dynamic_url_maker(route_and_parameters: Route, prefix: str,
                      customer_fixture=None) -> str:
    """Fonction utilitaire pour construire dynamiquement les URLs de test."""
    url = f"/{prefix}{route_and_parameters.path}"
    contact_type = route_and_parameters.contact_attr \
                        if route_and_parameters.contact_attr \
                        else None
    first_contact = getattr(customer_fixture, contact_type)[0] if contact_type else None
    customer_id = customer_fixture.id if customer_fixture else None
    contact_id = first_contact.id if first_contact else None
    url = url.replace("{id_c}", str(customer_id)) \
             .replace("{id_co}", str(contact_id))
    return url


def generate_request_cases(method: str, url: str, client, data, route: Route):
    """Génère les cas de test pour une méthode HTTP donnée."""
    request_method = getattr(client, method)

    if method in {"post", "patch", "put"}:
        if not data:
            return request_method(url)
        if route.is_form:
            return request_method(url, data=data)
        return request_method(url, json=data)

    if data:
        return request_method(url, query_string=data)
    return request_method(url)


@pytest.mark.parametrize("client_used, expected_code, routes, expected_start", [
    ("client_all", 200, ROUTES_TO_TEST, HOME_PAGE),
    ("client", 302, ROUTES_TO_TEST, REDIRECTION),
    ("client_informatique", 403, ROUTES_TO_TEST, FORBIDEN),
    ("client_compta", 200, ROUTES_TO_TEST, HOME_PAGE),
    ("client_commercial", 200, ROUTES_TO_TEST, HOME_PAGE),
    ("client_direction", 200, ROUTES_TO_TEST, HOME_PAGE),
])
def test_permissions(request, client_used, expected_code, routes, expected_start):
    """Test de l'accès aux différentes routes du module client selon les permissions."""
    # Récupération du client
    _client = request.getfixturevalue(client_used)

    # Itération sur les routes à tester
    for route in routes:
        c_fixture = request.getfixturevalue(
                        route.customer_fixture
                    )if route.customer_fixture else None
        url = dynamic_url_maker(route, "customer", c_fixture)
        data = route.data

        # Itération sur les méthodes HTTP à tester pour la route
        for m in route.methods:
            response = generate_request_cases(m, url, _client, data, route)
            assert response.status_code // 100 in [expected_code // 100, route.code // 100], (
                f"Échec pour {m.upper()} {url} avec {client_used} : "
                f"code {response.status_code} au lieu de {expected_code}. "
                f"data : {data or 'aucune donnée'}"
            )
            if route.return_start:
                assert response.text.startswith(expected_start), (
                    f"Le contenu de la réponse pour {m.upper()} {url} avec {client_used} "
                    f"ne commence pas par ce qui est attendu. "
                    f"Début de la réponse : {response.text[:100]}"
                )

# +------------------------------------------------------------------------------------------------+
# |                                    Tests pour les routes data                                  |
# +------------------------------------------------------------------------------------------------+

@pytest.mark.parametrize("searched_query, len_returned, customer_type, customer", [
    ("tes", 1, "pro", "complete_customer_pro"),
    ("jan", 1, "part", "complete_customer_part"),
    ("xyz", 0, None, None),
    ("", 0, None, None),
])
def test_search_fast_pro_part(request, client_all, searched_query,
                              len_returned, customer_type, customer):
    """Test de la route de recherche rapide de clients pour les clients professionnels."""
    customer = request.getfixturevalue(customer) if customer else None
    response = client_all.get("/customer/data/search/fast", query_string={"q": searched_query})
    data = response.get_json()

    assert response.status_code == 200
    assert isinstance(data, list)
    assert len(data) == len_returned
    if len_returned > 0:
        assert data[0]["customer_type"] == customer_type
