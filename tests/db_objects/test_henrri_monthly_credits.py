"""Tests des crédits mensuels Henrri, sans appel à l'API externe."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import httpx
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from henrri_connect.models import Item

from app_front.blueprints.order import utils as order_utils
from app_front.blueprints.order import utils_henrri
from db_models.services.henrri.base import HenrriCreditTransport, HenrriService
from db_models.services.henrri import base as henrri_base
from db_models.services.henrri import monthly_credits
from db_models.services.henrri.monthly_credits import (
    CreditReservation,
    HenrriMonthlyCredits,
    MonthlyCreditQuotaExceeded,
    MonthlyCreditsUnavailable,
    get_credit_limit,
)


@pytest.mark.parametrize("configured, expected", [(None, 200), ("20", 20), ("500", 500)])
def test_monthly_limit_reads_credit_limit(
    monkeypatch: pytest.MonkeyPatch, configured: str | None, expected: int,
) -> None:
    """HENRRI_CREDIT_LIMIT pilote la réservation, sans plafond de 200 imposé par le code."""
    if configured is None:
        monkeypatch.delenv("HENRRI_CREDIT_LIMIT", raising=False)
    else:
        monkeypatch.setenv("HENRRI_CREDIT_LIMIT", configured)
    monkeypatch.setenv("HENRRI_MONTHLY_CREDIT_LIMIT", "3")
    monkeypatch.delenv("HENRRI_MONTHLY_CREDIT_INITIAL_PERIOD", raising=False)
    monkeypatch.delenv("HENRRI_MONTHLY_CREDIT_INITIAL_USED", raising=False)
    collection = MagicMock()
    budget = HenrriMonthlyCredits(collection, "compte")
    factory = MagicMock()
    monkeypatch.setattr(monthly_credits, "_cached_monthly_credits", factory)

    assert get_credit_limit() == expected
    budget.reserve()
    monthly_credits.get_monthly_credits("compte", "https://henrri.example")

    condition = collection.find_one_and_update.call_args.args[0]
    assert condition["$expr"]["$lt"][1] == expected
    assert factory.call_args.args[1] == expected


@pytest.mark.parametrize("configured", ["", "0", "-1", "20.5", "invalide"])
def test_monthly_limit_rejects_invalid_credit_limit(
    monkeypatch: pytest.MonkeyPatch, configured: str,
) -> None:
    """Une variable invalide bloque explicitement le contrôle des crédits."""
    monkeypatch.setenv("HENRRI_CREDIT_LIMIT", configured)

    with pytest.raises(ValueError, match="HENRRI_CREDIT_LIMIT"):
        get_credit_limit()


def test_reservation_uses_atomic_shared_budget() -> None:
    """La dernière réservation bloque un autre travailleur avant tout envoi."""
    collection = MagicMock()
    collection.find_one_and_update.side_effect = [{"consumed": 199}, None]
    clock = lambda: datetime(2026, 10, 31, 23, 59, tzinfo=timezone.utc) # pylint: disable=C3001
    first = HenrriMonthlyCredits(collection, "compte", clock=clock)
    second = HenrriMonthlyCredits(collection, "compte", clock=clock)

    reservation = first.reserve()
    with pytest.raises(MonthlyCreditQuotaExceeded, match="01/11/2026"):
        second.reserve()

    assert reservation.document_id == "compte:2026-10"
    condition = collection.find_one_and_update.call_args.args[0]
    assert condition["$expr"] == {
        "$lt": [{"$add": ["$consumed", {"$size": "$reservations"}]}, 200]
    }
    first.confirm(reservation)
    assert collection.update_one.call_args.args == (
        {"_id": reservation.document_id, "reservations": reservation.token},
        {"$pull": {"reservations": reservation.token}, "$inc": {"consumed": 1}},
    )


def test_cancellation_does_not_consume_credit() -> None:
    """Une erreur certaine retire seulement la réservation, sans incrément."""
    collection = MagicMock()
    monthly_budget = HenrriMonthlyCredits(collection, "compte")
    reservation = CreditReservation("compte:2026-10", "reservation")

    monthly_budget.cancel(reservation)

    assert collection.update_one.call_args.args == (
        {"_id": reservation.document_id, "reservations": reservation.token},
        {"$pull": {"reservations": reservation.token}},
    )


@pytest.mark.parametrize("month, used, next_year, next_month", [
    (10, 27, 2026, 11), (11, 0, 2026, 12), (12, 0, 2027, 1),
])
def test_calendar_month_seed_is_not_carried_forward(
    month: int, used: int, next_year: int, next_month: int,
) -> None:
    """L'initialisation historique ne s'applique qu'au mois configuré."""
    collection = MagicMock()
    collection.find_one.return_value = {"consumed": used, "reservations": []}
    monthly_budget = HenrriMonthlyCredits(
        collection, "compte", initial_period="2026-10", initial_used=27,
        clock=lambda: datetime(2026, month, 1, tzinfo=timezone.utc),
    )

    status = monthly_budget.get_status()

    assert collection.update_one.call_args.args[1] == {
        "$setOnInsert": {"consumed": used, "reservations": []}
    }
    assert status.available == 200 - used
    assert status.reset_at == datetime(next_year, next_month, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize("consumed, tokens", [(200, []), (199, ["incertaine"])])
def test_exhausted_or_reserved_budget_blocks_new_invoice(
    consumed: int, tokens: list[str],
) -> None:
    """Un crédit incertain reste indisponible jusqu'à sa vérification."""
    collection = MagicMock()
    collection.find_one.return_value = {"consumed": consumed, "reservations": tokens}
    monthly_budget = HenrriMonthlyCredits(collection, "compte")

    with pytest.raises(MonthlyCreditQuotaExceeded):
        monthly_budget.ensure_available()


def test_unavailable_mongo_blocks_reservation() -> None:
    """Aucune réservation locale ne remplace MongoDB indisponible."""
    collection = MagicMock()
    collection.update_one.side_effect = ServerSelectionTimeoutError("indisponible")
    monthly_budget = HenrriMonthlyCredits(collection, "compte")

    with pytest.raises(MonthlyCreditsUnavailable):
        monthly_budget.reserve()
    collection.find_one_and_update.assert_not_called()


def test_inflight_success_stays_in_original_month() -> None:
    """Une réponse reçue après minuit confirme le crédit du mois de l'envoi."""
    collection = MagicMock()
    monthly_budget = HenrriMonthlyCredits(
        collection, "compte", clock=lambda: datetime(2026, 11, 1, tzinfo=timezone.utc),
    )

    monthly_budget.confirm(CreditReservation("compte:2026-10", "en-cours"))

    assert collection.update_one.call_args.args[0]["_id"] == "compte:2026-10"


@pytest.mark.parametrize("limit, period, used", [
    (0, "", 0), (-1, "", 0), (200, "", 1),
    (200, "2026-1", 0), (200, "2026-13", 0), (200, "2026-10", 201),
])
def test_invalid_configuration_blocks_monthly_quota(
    limit: int, period: str, used: int,
) -> None:
    """Le quota doit être positif et la consommation initiale compatible."""
    collection = MagicMock()
    with pytest.raises(ValueError):
        HenrriMonthlyCredits(collection, "compte", limit, period, used)


@pytest.mark.parametrize("method, path", [
    ("GET", "/v1/items"), ("HEAD", "/v1/documents/1"),
    ("POST", "/v1/users/authenticate"), ("POST", "/v1/users/refresh-token"),
])
def test_read_and_auth_do_not_use_monthly_credit(method: str, path: str) -> None:
    """Les lectures et l'authentification restent possibles avec le budget épuisé."""
    factory = MagicMock()
    send = MagicMock(return_value=httpx.Response(200))
    transport = HenrriCreditTransport(httpx.MockTransport(send), factory)

    with httpx.Client(transport=transport) as client:
        assert client.request(method, f"https://henrri.example{path}").status_code == 200

    factory.assert_not_called()
    send.assert_called_once()


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize("status_code", [200, 201, 204, 400, 429, 500])
def test_business_write_settles_its_reservation(method: str, status_code: int) -> None:
    """Seules les écritures ayant une réponse 2xx consomment un crédit confirmé."""
    monthly_budget = MagicMock()
    send = MagicMock(return_value=httpx.Response(status_code))
    transport = HenrriCreditTransport(httpx.MockTransport(send), lambda: monthly_budget)

    with httpx.Client(transport=transport) as client:
        assert client.request(method, "https://henrri.example/v1/items").status_code == status_code

    monthly_budget.reserve.assert_called_once()
    if status_code < 300:
        monthly_budget.confirm.assert_called_once_with(monthly_budget.reserve.return_value)
        monthly_budget.cancel.assert_not_called()
    else:
        monthly_budget.cancel.assert_called_once_with(monthly_budget.reserve.return_value)
        monthly_budget.confirm.assert_not_called()


@pytest.mark.parametrize("error_class, released", [
    (httpx.ConnectError, True), (httpx.ConnectTimeout, True), (httpx.PoolTimeout, True),
    (httpx.ReadTimeout, False), (httpx.ReadError, False), (httpx.WriteError, False),
    (httpx.WriteTimeout, False),
])
def test_transport_failure_preserves_uncertain_credit(
    error_class: type[httpx.TransportError], released: bool,
) -> None:
    """Un résultat potentiellement écrit à distance conserve sa réservation."""
    monthly_budget = MagicMock()
    send = MagicMock(side_effect=error_class("échec réseau"))
    transport = HenrriCreditTransport(httpx.MockTransport(send), lambda: monthly_budget)

    with httpx.Client(transport=transport) as client:
        with pytest.raises(error_class):
            client.post("https://henrri.example/v1/items")

    monthly_budget.confirm.assert_not_called()
    if released:
        monthly_budget.cancel.assert_called_once_with(monthly_budget.reserve.return_value)
    else:
        monthly_budget.cancel.assert_not_called()


@pytest.mark.parametrize("error", [
    MonthlyCreditQuotaExceeded(200, datetime(2026, 11, 1, tzinfo=timezone.utc)),
    MonthlyCreditsUnavailable("MongoDB indisponible"),
])
def test_blocked_credit_prevents_http_write(error: RuntimeError) -> None:
    """Un budget épuisé ou indisponible empêche réellement l'envoi HTTP."""
    monthly_budget = MagicMock()
    monthly_budget.reserve.side_effect = error
    send = MagicMock(return_value=httpx.Response(200))
    transport = HenrriCreditTransport(httpx.MockTransport(send), lambda: monthly_budget)

    with httpx.Client(transport=transport) as client:
        with pytest.raises(type(error)):
            client.post("https://henrri.example/v1/items")

    send.assert_not_called()


def test_confirmation_failure_preserves_successful_remote_id() -> None:
    """Un échec MongoDB après succès HTTP ne masque pas l'identifiant distant."""
    monthly_budget = MagicMock()
    monthly_budget.confirm.side_effect = MonthlyCreditsUnavailable("MongoDB indisponible")
    transport = HenrriCreditTransport(
        httpx.MockTransport(lambda _request: httpx.Response(201, json={"id": 8001})),
        lambda: monthly_budget,
    )

    with httpx.Client(transport=transport) as client:
        response = client.post("https://henrri.example/v1/items")

    assert response.json()["id"] == 8001
    monthly_budget.cancel.assert_not_called()


def test_invoice_flow_stops_before_customer_and_product_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le quota épuisé bloque la facture avant toute écriture client ou produit."""
    customer_service = MagicMock()
    customer_service.ensure_monthly_credit.side_effect = MonthlyCreditQuotaExceeded(
        200, datetime(2026, 11, 1, tzinfo=timezone.utc),
    )
    product_service = MagicMock()
    monkeypatch.setattr(utils_henrri, "HenrriCustomersService", lambda: customer_service)
    monkeypatch.setattr(utils_henrri, "HenrriProductsService", product_service)
    invoice = MagicMock()

    with pytest.raises(utils_henrri.HenrriSyncError) as caught:
        utils_henrri.create_invoice(invoice)

    assert caught.value.step == "quota"
    assert caught.value.status_code == 429
    customer_service.upsert_customer.assert_not_called()
    product_service.assert_not_called()


def test_quota_check_closes_temporary_service(monkeypatch: pytest.MonkeyPatch) -> None:
    """La vérification préalable n'envoie aucune requête à Henrri."""
    service = MagicMock()
    monkeypatch.setattr(utils_henrri, "HenrriCustomersService", lambda: service)

    utils_henrri.ensure_invoice_credit_available()

    service.ensure_monthly_credit.assert_called_once()
    service.client.close.assert_called_once()
    service.upsert_customer.assert_not_called()


def test_invoice_order_does_not_create_local_invoice_when_quota_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un budget déjà épuisé ne crée ni facture locale ni ligne de port."""
    session = MagicMock()
    order = MagicMock(customer_id=1, status="draft", order_lines=[])
    repository = MagicMock()
    repository.get_by_id.return_value = order
    invoice_repository = MagicMock()
    quota = MagicMock(side_effect=utils_henrri.HenrriSyncError(
        "Quota mensuel Henrri atteint", status_code=429, step="quota",
    ))
    monkeypatch.setattr(order_utils.db_conf, "get_main_session", lambda: session)
    monkeypatch.setattr(order_utils, "OrdersRepository", lambda _session: repository)
    monkeypatch.setattr(order_utils, "InvoiceRepository", invoice_repository)
    monkeypatch.setattr(order_utils, "ensure_invoice_credit_available", quota)
    line_items = [{"order_line_id": 1, "quantity": 1}]

    with pytest.raises(ValueError, match="Quota mensuel Henrri"):
        order_utils.invoice_order(1, line_items)

    invoice_repository.assert_not_called()
    session.add_all.assert_not_called()
    session.flush.assert_not_called()
    session.commit.assert_not_called()


def test_invoice_order_preserves_partial_invoice_when_last_credit_is_consumed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un épuisement en cours conserve les IDs et rend l'échec visible à la route."""
    session = MagicMock()
    order = MagicMock(customer_id=1, status="draft", order_lines=[])
    repository = MagicMock(get_by_id=MagicMock(return_value=order))
    invoice = MagicMock(reference="INV-PARTIELLE", henrri_id="9001")
    invoice_repository = MagicMock(create_invoice=MagicMock(return_value=invoice))
    sync = MagicMock(side_effect=utils_henrri.HenrriSyncError(
        "Quota mensuel Henrri atteint", status_code=429, step="lines",
    ))
    monkeypatch.setattr(order_utils.db_conf, "get_main_session", lambda: session)
    monkeypatch.setattr(order_utils, "OrdersRepository", lambda _session: repository)
    monkeypatch.setattr(order_utils, "InvoiceRepository", lambda _session: invoice_repository)
    monkeypatch.setattr(order_utils, "ensure_invoice_credit_available", MagicMock())
    monkeypatch.setattr(order_utils, "_sync_invoice_with_henrri", sync)
    monkeypatch.setattr(order_utils, "_recalculate_order_status", MagicMock())
    line_items = [{"order_line_id": 1, "quantity": 1}]

    with pytest.raises(ValueError, match="Facture locale INV-PARTIELLE conservée"):
        order_utils.invoice_order(1, line_items)

    assert invoice.henrri_id == "9001"
    invoice_repository.create_invoice.assert_called_once()
    session.commit.assert_called_once()
    session.delete.assert_not_called()


def test_retry_commits_remote_ids_when_monthly_quota_blocks_remaining_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Une reprise interrompue garde l'identifiant du document pour la prochaine relance."""
    invoice = MagicMock(henrri_id="9001", sync_logs=[])
    session = MagicMock()
    repository = MagicMock(get_by_id=MagicMock(return_value=invoice))
    sync = MagicMock(side_effect=utils_henrri.HenrriSyncError(
        "Quota mensuel Henrri atteint", status_code=429, step="lines",
    ))
    monkeypatch.setattr(order_utils.db_conf, "get_main_session", lambda: session)
    monkeypatch.setattr(order_utils, "InvoiceRepository", lambda _session: repository)
    monkeypatch.setattr(
        order_utils,
        "find_henrri_invoice",
        MagicMock(return_value=MagicMock(finalized=False)),
    )
    monkeypatch.setattr(order_utils, "_sync_invoice_with_henrri", sync)

    with pytest.raises(ValueError, match="Quota mensuel Henrri"):
        order_utils.retry_henrri_invoice(1)

    assert invoice.henrri_id == "9001"
    session.commit.assert_called_once()


def test_sdk_applies_minute_and_monthly_limits_to_actual_http_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le vrai client SDK réserve les écritures et limite aussi l'authentification et les GET."""
    monthly_budget = MagicMock()
    monthly_factory = MagicMock(return_value=monthly_budget)
    minute_limiter = MagicMock()
    monkeypatch.setattr(henrri_base, "get_monthly_credits", monthly_factory)
    monkeypatch.setattr(henrri_base, "get_rate_limiter", lambda *_args: minute_limiter)
    monkeypatch.setenv("HENRRI_API_KEY", "compte-test")
    monkeypatch.setenv("HENRRI_API_SECRET", "secret-test")
    item = Item(
        id=123, vat_percent=0.0, creation_date="2026-10-05",
        is_tax_included=False, purchase_price=0.0, is_a_group=False,
    )

    def send(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("authenticate"):
            return httpx.Response(200, json={"accessToken": "jeton-test", "expiresIn": 60})
        return httpx.Response(200, json=item.model_dump(by_alias=True))

    monkeypatch.setattr(httpx, "HTTPTransport", lambda **_kwargs: httpx.MockTransport(send))
    service = HenrriService()
    try:
        service.client.authenticate()
        assert service.client.items.add(item).id == 123
        assert service.client.items.get(123).id == 123
    finally:
        service.client.close()

    assert minute_limiter.acquire.call_count == 3
    monthly_factory.assert_called_once()
    monthly_budget.reserve.assert_called_once()
    monthly_budget.confirm.assert_called_once_with(monthly_budget.reserve.return_value)
    monthly_budget.cancel.assert_not_called()


def test_calendar_uses_utc_not_local_first_of_month() -> None:
    """Le premier novembre local peut encore appartenir au budget UTC d'octobre."""
    collection = MagicMock()
    collection.find_one.return_value = {"consumed": 0, "reservations": []}
    monthly_budget = HenrriMonthlyCredits(
        collection, "compte", clock=lambda: datetime(
            2026, 11, 1, 1, tzinfo=timezone(timedelta(hours=2)),
        ),
    )

    status = monthly_budget.get_status()

    assert collection.find_one.call_args.args[0] == {"_id": "compte:2026-10"}
    assert status.reset_at == datetime(2026, 11, 1, tzinfo=timezone.utc)


@pytest.mark.skipif(
    not os.getenv("HENRRI_TEST_MONGO_URI"), reason="MongoDB de test non configuré",
)
def test_mongodb_concurrent_reservations_and_month_rollover() -> None:
    """Des clients MongoDB indépendants ne peuvent pas réserver plus de 200 crédits."""
    uri = os.environ["HENRRI_TEST_MONGO_URI"]
    collection_name = f"monthly_credits_{uuid4().hex}"
    now = [datetime(2026, 10, 31, 23, 59, tzinfo=timezone.utc)]
    with MongoClient(uri, serverSelectionTimeoutMS=10000) as client:
        collection = client["henrri_credit_tests"][collection_name]
        monthly_budget = HenrriMonthlyCredits(collection, "compte-test", clock=lambda: now[0])
        try:
            monthly_budget.ensure_available()

            def reserve_from_another_client(_index: int) -> CreditReservation | None:
                with MongoClient(uri, serverSelectionTimeoutMS=10000) as worker_client:
                    worker_budget = HenrriMonthlyCredits(
                        worker_client["henrri_credit_tests"][collection_name],
                        "compte-test", clock=lambda: now[0],
                    )
                    try:
                        return worker_budget.reserve()
                    except MonthlyCreditQuotaExceeded:
                        return None

            with ThreadPoolExecutor(max_workers=16) as executor:
                attempts = list(executor.map(reserve_from_another_client, range(220)))
            reservations = [reservation for reservation in attempts if reservation is not None]
            assert len(reservations) == 200
            assert monthly_budget.get_status().available == 0
            for reservation in reservations[:-1]:
                monthly_budget.confirm(reservation)
                monthly_budget.confirm(reservation)
            status = monthly_budget.get_status()
            assert status.consumed == 199
            assert len(status.reservations) == 1
            with pytest.raises(MonthlyCreditQuotaExceeded):
                monthly_budget.reserve()

            now[0] = datetime(2026, 11, 1, tzinfo=timezone.utc)
            assert monthly_budget.get_status().available == 200
            monthly_budget.confirm(reservations[-1])
            october = collection.find_one({"_id": "compte-test:2026-10"})
            assert october is not None
            assert october["consumed"] == 200
            assert october["reservations"] == []
            assert monthly_budget.get_status().consumed == 0
            new_reservation = monthly_budget.reserve()
            monthly_budget.cancel(new_reservation)
            monthly_budget.cancel(new_reservation)
            assert monthly_budget.get_status().available == 200
        finally:
            collection.drop()
