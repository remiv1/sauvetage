"""Tests E2E des projections de stock issues des commandes et réservations."""

from datetime import date, datetime, timezone
from decimal import Decimal

from flask.testing import FlaskClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from db_models.objects import (
    GeneralObjects,
    InventoryMovements,
    ObjectPrices,
    OrderIn,
    OrderInLine,
    Suppliers,
    VatRate,
)
from db_models.repositories.stocks.inventory import InventoryRepository
from db_models.repositories.stocks.stock import StockRepository


EAN13 = "9780201379624"


def _latest_order(session: Session, prefix: str) -> OrderIn:
    return session.execute(
        select(OrderIn)
        .where(OrderIn.order_ref.startswith(prefix))
        .order_by(OrderIn.id.desc())
    ).scalars().first()


def _active_line(session: Session, order_id: int) -> OrderInLine:
    return session.execute(
        select(OrderInLine)
        .where(
            OrderInLine.order_in_id == order_id,
            OrderInLine.line_state == "pending",
        )
        .order_by(OrderInLine.id.desc())
    ).scalars().first()


def _assert_stock(
    client: FlaskClient,
    session: Session,
    obj: GeneralObjects,
    *,
    theoretical: int,
    available: int,
    scanned: int,
) -> None:
    stock_repo = StockRepository(session)
    inventory_repo = InventoryRepository(session)

    assert stock_repo.get_qty_by_id(obj.id, theorical=True) == theoretical
    assert inventory_repo.get_available_quantity(obj.id) == available

    payload = {
        "ean13": [obj.ean13] * scanned,
        "inventory_type": "partial" if scanned else "complete",
    }
    response = client.post("/inventory/data/prepare", json=payload)
    assert response.status_code == 200
    reconciliation = next(
        line for line in response.get_json() if line["ean13"] == obj.ean13
    )
    assert reconciliation["stock_theorique"] == theoretical
    assert reconciliation["stock_reel"] == scanned
    assert reconciliation["difference"] == scanned - theoretical


def _create_order(client: FlaskClient, supplier: Suppliers, *, reservation: bool) -> None:
    endpoint = (
        "/stock/htmx/reservations/section/create"
        if reservation
        else "/stock/htmx/orders/section/create"
    )
    response = client.post(
        endpoint,
        data={
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
        },
    )
    assert response.status_code == 200


def _add_order_line(
    client: FlaskClient,
    order: OrderIn,
    obj: GeneralObjects,
) -> None:
    response = client.post(
        f"/stock/htmx/orders/{order.id}/line/create",
        data={
            "order_id": order.id,
            "general_object_id": obj.id,
            "quantity": "2",
            "prices-0-unit_price": "8.40",
            "prices-0-vat_rate": "5.5",
            "prices-1-unit_price": "2.80",
            "prices-1-vat_rate": "20",
        },
    )
    assert response.status_code == 200


def test_stock_projection_tracks_orders_and_reservations(
    client_direction: FlaskClient,
    db_session_main: Session,
    supplier: Suppliers,
    fastapi_test_client,
) -> None:
    """Valide les stocks projeté, disponible et scanné sur le parcours complet."""
    del fastapi_test_client
    client = client_direction

    response = client.post(
        "/inventory/data/products",
        json={
            "ean13": EAN13,
            "name": "Livre E2E multi-prix",
            "description": "Article utilisé par le parcours E2E des stocks.",
            "product_type": "book",
            "supplier_id": supplier.id,
            "author": "Auteur E2E",
            "diffuser": "Diffuseur E2E",
            "editor": "Éditeur E2E",
            "genre": "Test",
            "publication_year": 2026,
            "pages": 100,
            "price": 12.0,
        },
    )
    assert response.status_code == 201

    obj = db_session_main.execute(
        select(GeneralObjects).where(GeneralObjects.ean13 == EAN13)
    ).scalar_one()
    reduced_vat = VatRate(
        code=101,
        rate=Decimal("5.50"),
        label="TVA livre E2E",
        date_start=datetime.now(timezone.utc),
    )
    standard_vat = VatRate(
        code=102,
        rate=Decimal("20.00"),
        label="TVA standard E2E",
        date_start=datetime.now(timezone.utc),
    )
    db_session_main.add_all([reduced_vat, standard_vat])
    db_session_main.flush()
    obj.prices[0].vat_rate = reduced_vat
    obj.prices.append(
        ObjectPrices(
            price=Decimal("4.00"),
            vat_rate=standard_vat,
            from_date=date.today(),
        )
    )
    db_session_main.add(
        InventoryMovements(
            general_object_id=obj.id,
            movement_type="inventory",
            quantity=0,
            price_at_movement=Decimal("0.00"),
            source="inventaire E2E",
            destination="stock",
            notes="Stock initial nul",
        )
    )
    db_session_main.commit()

    _assert_stock(client, db_session_main, obj, theoretical=0, available=0, scanned=0)

    _create_order(client, supplier, reservation=False)
    order = _latest_order(db_session_main, "CMD-")
    _add_order_line(client, order, obj)
    line = _active_line(db_session_main, order.id)
    assert len(line.prices) == 2
    assert line.get_unit_price_ht() == Decimal("11.20")
    assert line.inventory_movement.quantity == 2
    _assert_stock(client, db_session_main, obj, theoretical=2, available=0, scanned=0)

    response = client.post(
        f"/stock/htmx/orders/{order.id}/line/{line.id}/delete"
    )
    assert response.status_code == 200
    _assert_stock(client, db_session_main, obj, theoretical=0, available=0, scanned=0)

    _add_order_line(client, order, obj)
    line = _active_line(db_session_main, order.id)
    assert len(line.prices) == 2
    _assert_stock(client, db_session_main, obj, theoretical=2, available=0, scanned=0)

    response = client.post(f"/stock/htmx/orders/{order.id}/confirm")
    assert response.status_code == 200
    response = client.post(
        f"/stock/htmx/orders/{order.id}/line/{line.id}/receive",
        data={
            "line_id": line.id,
            "order_id": order.id,
            "qty_received": "2",
            "qty_cancelled": "0",
        },
    )
    assert response.status_code == 200
    _assert_stock(client, db_session_main, obj, theoretical=2, available=2, scanned=2)

    _create_order(client, supplier, reservation=True)
    reservation = _latest_order(db_session_main, "RES-")
    response = client.post(
        f"/stock/htmx/reservations/{reservation.id}/line/create",
        data={
            "order_id": reservation.id,
            "general_object_id": obj.id,
            "quantity": "1",
        },
    )
    assert response.status_code == 200
    reservation_line = _active_line(db_session_main, reservation.id)
    _assert_stock(client, db_session_main, obj, theoretical=1, available=1, scanned=2)

    response = client.post(
        f"/stock/htmx/reservations/{reservation.id}/line/{reservation_line.id}/delete"
    )
    assert response.status_code == 200
    _assert_stock(client, db_session_main, obj, theoretical=2, available=2, scanned=2)

    response = client.post(
        f"/stock/htmx/reservations/{reservation.id}/line/create",
        data={
            "order_id": reservation.id,
            "general_object_id": obj.id,
            "quantity": "1",
        },
    )
    assert response.status_code == 200
    _assert_stock(client, db_session_main, obj, theoretical=1, available=1, scanned=2)

    response = client.post(f"/stock/htmx/reservations/{reservation.id}/return")
    assert response.status_code == 200
    _assert_stock(client, db_session_main, obj, theoretical=2, available=2, scanned=2)
