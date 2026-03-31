"""Module de tests pour le tableau de bord."""

import pytest

ROUTES_TO_TEST = [
    "/dashboard/",
    "/dashboard/data/finances",
    "/dashboard/data/commandes",
    "/dashboard/data/stock",
]


@pytest.mark.parametrize("routes, client_fixture, expected_status", [
    (ROUTES_TO_TEST, "client", 302),
    (ROUTES_TO_TEST, "client_informatique", 403),
    (ROUTES_TO_TEST, "client_compta", 200),
    (ROUTES_TO_TEST, "client_commercial", 200),
    (ROUTES_TO_TEST, "client_direction", 200),
    (ROUTES_TO_TEST, "client_admin", 200),
    (ROUTES_TO_TEST, "client_logistique", 200),
])
def test_dashboard_authorization(routes, client_fixture, expected_status, request):
    """Test d'accès aux routes du dashboard selon les permissions de l'utilisateur."""
    client = request.getfixturevalue(client_fixture)
    for r in routes:
        response = client.get(r)
        assert response.status_code == expected_status, (
            f"Attendu {expected_status} pour {r} avec {client_fixture}, "
            f"obtenu {response.status_code}.")
