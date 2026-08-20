"""Module de tests pour le tableau de bord."""

from datetime import datetime
from types import SimpleNamespace

from flask import session as flask_session
import pytest

from app_front.config import db_conf

ROUTES_TO_TEST = [
    "/dashboard/",
    "/dashboard/data/finances",
    "/dashboard/data/commandes",
    "/dashboard/data/stock",
]


@pytest.fixture
def dashboard_local_session_validation(monkeypatch):
    """Valide localement la session pour isoler les routes data testées."""
    def validate_session(_session_token):
        return {
            "valid": True,
            "username": flask_session.get("username", "test"),
            "email": flask_session.get("email", "test@example.com"),
            "permissions": flask_session.get("permissions", ""),
        }

    monkeypatch.setattr("app_front.main.validate_session", validate_session)


@pytest.mark.parametrize("routes, client_fixture, expected_status", [
    (ROUTES_TO_TEST, "client", 302),
    (ROUTES_TO_TEST, "client_informatique", 403),
    (ROUTES_TO_TEST, "client_compta", 200),
    (ROUTES_TO_TEST, "client_commercial", 200),
    (ROUTES_TO_TEST, "client_direction", 200),
    (ROUTES_TO_TEST, "client_admin", 200),
    (ROUTES_TO_TEST, "client_logistique", 200),
])
def test_dashboard_authorization(
        routes,
        client_fixture,
        expected_status,
        request,
        dashboard_local_session_validation, # pylint: disable=W0621
    ):
    """Test d'accès aux routes du dashboard selon les permissions de l'utilisateur."""
    del dashboard_local_session_validation
    client = request.getfixturevalue(client_fixture)
    for r in routes:
        response = client.get(r)
        assert response.status_code == expected_status, (
            f"Attendu {expected_status} pour {r} avec {client_fixture}, "
            f"obtenu {response.status_code}.")


class FakeResult:
    """Résultat SQL minimal utilisable par les routes du dashboard."""

    def __init__(self, rows):
        self.rows = rows

    def all(self):
        """Retourne les lignes simulées."""
        return self.rows


class FakeRow:
    """Ligne simulée avec les mêmes clés que le résultat SQLAlchemy."""

    def __init__(self, **values):
        self._values = values

    def __getattr__(self, name):
        try:
            return self._values[name]
        except KeyError as error:
            raise AttributeError(name) from error


class FakeSession:
    """Session SQL simulée avec des résultats retournés dans l'ordre."""

    def __init__(self, *results):
        self.results = iter(results)

    def execute(self, _statement):
        """Retourne le prochain résultat configuré."""
        return FakeResult(next(self.results))


def test_dashboard_finances_retourne_les_series_mensuelles(
        client_direction,
        monkeypatch,
        dashboard_local_session_validation, # pylint: disable=W0621
    ):
    """La route finances expose les mois et les montants agrégés."""
    del dashboard_local_session_validation
    session = FakeSession(
        [(datetime(2026, 1, 15), 100, 20)],
        [(datetime(2026, 1, 10), 2, 15)],
    )
    monkeypatch.setattr(db_conf, "get_main_session", lambda: session)

    response = client_direction.get(
        "/dashboard/data/finances",
        query_string={"start_date": "2026-01-01", "range": "M"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "months": ["Jan 2026"],
        "charges": [30.0],
        "ressources": [120.0],
    }


def test_dashboard_stock_by_category_retourne_les_totaux(
        client_direction,
        monkeypatch,
        dashboard_local_session_validation, # pylint: disable=W0621
    ):
    """La vue stock par catégorie agrège les quantités et les valeurs."""
    del dashboard_local_session_validation
    session = FakeSession([
        FakeRow(
            id=1,
            general_object_type="book",
            price=10,
            name="Livre test",
            stock_qty=3,
        ),
        FakeRow(
            id=2,
            general_object_type="other",
            price=4.5,
            name="Objet test",
            stock_qty=2,
        ),
    ])
    monkeypatch.setattr(db_conf, "get_main_session", lambda: session)

    response = client_direction.get(
        "/dashboard/data/stock",
        query_string={"view": "by_category"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "labels": ["Livres", "Objets"],
        "values": [3, 2],
        "value_total": 39.0,
        "items_total": 5,
    }


def test_dashboard_stock_slow_moving_limite_et_trie_les_articles(
        client_direction,
        monkeypatch,
        dashboard_local_session_validation, # pylint: disable=W0621
    ):
    """La vue slow_moving trie les stocks positifs et respecte la limite."""
    del dashboard_local_session_validation
    session = FakeSession(
        [
            FakeRow(
                id=1, general_object_type="book", price=10,
                name="Petit stock", stock_qty=2,
            ),
            FakeRow(
                id=2, general_object_type="book", price=5,
                name="Grand stock", stock_qty=7,
            ),
        ],
        [
            SimpleNamespace(general_object_id=1, last_ts=None),
            SimpleNamespace(general_object_id=2, last_ts=None),
        ],
    )
    monkeypatch.setattr(db_conf, "get_main_session", lambda: session)

    response = client_direction.get(
        "/dashboard/data/stock",
        query_string={"view": "slow_moving", "limit": "1"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "labels": ["Grand stock"],
        "values": [7],
        "value_total": 35.0,
        "items_total": 7,
    }


@pytest.mark.parametrize("pagination", [
    {"page": "abc"},
    {"per_page": "abc"},
])
def test_dashboard_commandes_rejette_une_pagination_invalide(
        client_direction,
        dashboard_local_session_validation, # pylint: disable=W0621
        pagination,
    ):
    """Une pagination non numérique retourne une erreur HTTP explicite."""
    del dashboard_local_session_validation
    response = client_direction.get(
        "/dashboard/data/commandes",
        query_string=pagination,
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Les paramètres de pagination doivent être numériques."
    }
