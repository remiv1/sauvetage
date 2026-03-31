"""Module de tests pour l'inventaire."""

from collections import namedtuple
import pytest

Route = namedtuple("route", "path method data fixtures success_status")
POST_HTMX = {
    "general_object_id": "{id_obj}",
    "object-wrapper": "Test Book",
}
POST_PARSE = {
    "raw": "9781234567890,9781234567890,9781111111111",
    "inventory_type": "partial",
    "category": "book",
}
POST_UNKNOWN = {
    "ean13": ["9781234567890", "9781111111111"],
}
POST_PRODUCT = {
    "ean13": "9780000000001",
    "name": "Produit inventaire test",
    "product_type": "book",
    "supplier_id": "{supplier_id}",
    "author": "Auteur test",
    "diffuser": "Diffuseur test",
    "editor": "Editeur test",
    "genre": "Fiction",
    "publication_year": 2024,
    "pages": 120,
    "category": "book",
    "price": 12.5,
}
POST_PREPARE = {
    "ean13": ["9781234567890", "9781234567890"],
    "inventory_type": "partial",
}
POST_VALIDATE = {
    "lines": [
        {
            "ean13": "9781234567890",
            "stock_theorique": 1,
            "stock_reel": 2,
            "motifs": ["counting_error"],
            "commentaire": "écart de test",
        }
    ],
    "inventory_type": "partial",
}
POST_COMMIT = {
    "planned": [
        {
            "general_object_id": "{general_object_id}",
            "ean13": "9781234567890",
            "quantity": 1,
            "movement_type": "in",
            "motifs": ["counting_error"],
            "commentaire": "commit de test",
        }
    ],
    "inventory_type": "partial",
}

ALL_ROUTES_TO_TEST = [
    Route("/inventory/", "get", None, [], 200),
    Route("/inventory/htmx/objects/get", "get", {"object-wrapper": "test"}, ["book_object"], 200),
    Route("/inventory/htmx/objects/select", "post", POST_HTMX, ["book_object"], 200),
    Route("/inventory/data/objects/info/search", "get", {"author": "john"}, ["book_object"], 200),
    Route("/inventory/data/parse", "post", POST_PARSE, [], 200),
    Route("/inventory/data/unknown", "post", POST_UNKNOWN, [], 200),
    Route("/inventory/data/products", "post", POST_PRODUCT, ["supplier"], 201),
    Route("/inventory/data/prepare", "post", POST_PREPARE, [], 200),
    Route("/inventory/data/validate", "post", POST_VALIDATE, ["book_object"], 200),
    Route("/inventory/data/commit", "post", POST_COMMIT, ["book_object"], 200),
    Route("/inventory/data/status", "get", None, [], 200),
]

SUCCESS_ROUTES_TO_TEST = [
    route for route in ALL_ROUTES_TO_TEST if route.path != "/inventory/data/unknown"
]


def _resolve_payload(data, fixture_values):
    """Injecte quelques placeholders de test avec les fixtures disponibles."""
    if isinstance(data, dict):
        return {k: _resolve_payload(v, fixture_values) for k, v in data.items()}
    if isinstance(data, list):
        return [_resolve_payload(item, fixture_values) for item in data]
    if data == "{id_obj}":
        return fixture_values.get("book_object").id
    if data == "{supplier_id}":
        return fixture_values.get("supplier").id
    if data == "{general_object_id}":
        return fixture_values.get("book_object").id
    return data


def _call_route(client, route, payload):
    """Exécute une route de test avec le bon mode de transmission des données."""
    method = getattr(client, route.method)
    if payload:
        if route.method == "get":
            return method(route.path, query_string=payload)
        return method(route.path, json=payload)
    return method(route.path)


def _assert_status(response, route, expected_status, client_fixture):
    """Valide le statut HTTP attendu pour une route donnée."""
    assert response.status_code == expected_status, (
        f"Attendu {expected_status} pour {route.path} avec {client_fixture}, "
        f"obtenu {response.status_code}."
    )


@pytest.mark.parametrize("route, client_fixture, expected_status", [
    (ALL_ROUTES_TO_TEST, "client", 302),
    (ALL_ROUTES_TO_TEST, "client_informatique", 403),
])
def test_inventory_authorization_denied(route, client_fixture, expected_status,
                                        request, fastapi_test_client): # pylint: disable=unused-argument
    """Test des refus d'accès aux routes de l'inventaire."""
    client = request.getfixturevalue(client_fixture)
    for r in route:
        fixture_values = {name: request.getfixturevalue(name) for name in r.fixtures}
        payload = _resolve_payload(r.data, fixture_values) if r.data else None
        response = _call_route(client, r, payload)
        _assert_status(response, r, expected_status, client_fixture)


@pytest.mark.parametrize("client_fixture", [
    "client_direction",
    "client_logistique",
    "client_support",
    "client_admin",
])
def test_inventory_authorization_success(client_fixture, request,
                                         fastapi_test_client): # pylint: disable=unused-argument
    """Test des routes inventaire qui doivent réussir métier côté profils autorisés."""
    client = request.getfixturevalue(client_fixture)
    for route in SUCCESS_ROUTES_TO_TEST:
        fixture_values = {name: request.getfixturevalue(name) for name in route.fixtures}
        payload = _resolve_payload(route.data, fixture_values) if route.data else None
        response = _call_route(client, route, payload)
        _assert_status(response, route, route.success_status, client_fixture)
