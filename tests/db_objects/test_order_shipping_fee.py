"""Tests de ventilation des frais de port des commandes."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app_front.blueprints.order import utils as order_utils
from app_front.blueprints.order.utils import _create_shipping_fee_lines
from db_models.objects import InvoiceFeeProduct, Order, OrderLine, VatRate


def _order_line(
    *,
    vat_rate_id: int,
    vat_rate: str,
    unit_price: str,
    discount: str = "0",
) -> OrderLine:
    return OrderLine(
        order_id=1,
        general_object_id=vat_rate_id,
        quantity=1,
        unit_price=Decimal(unit_price),
        discount=Decimal(discount),
        vat_rate=Decimal(vat_rate),
        vat_rate_id=vat_rate_id,
        status="draft",
        create_source="test",
    )


def test_shipping_fee_is_allocated_by_discounted_amount_before_tax() -> None:
    """Le port doit suivre les proportions des montants HT après remise."""
    order = Order(id=1)
    lines = [
        (_order_line(vat_rate_id=1, vat_rate="5.5", unit_price="100"), 1),
        (
            _order_line(
                vat_rate_id=2,
                vat_rate="20",
                unit_price="100",
                discount="50",
            ),
            1,
        ),
    ]

    shipping_lines = _create_shipping_fee_lines(order, lines, Decimal("15"))

    allocations = {
        float(order_line.vat_rate): Decimal(order_line.unit_price)
        for order_line in shipping_lines
    }
    assert allocations == {5.5: Decimal("10.00"), 20.0: Decimal("5.00")}


def test_shipping_fee_rounding_remainder_is_kept() -> None:
    """Le reliquat d'arrondi doit préserver exactement le montant de port."""
    order = Order(id=1)
    lines = [
        (_order_line(vat_rate_id=1, vat_rate="5.5", unit_price="1"), 1),
        (_order_line(vat_rate_id=2, vat_rate="10", unit_price="1"), 1),
        (_order_line(vat_rate_id=3, vat_rate="20", unit_price="1"), 1),
    ]

    shipping_lines = _create_shipping_fee_lines(order, lines, Decimal("10"))

    allocations = [Decimal(order_line.unit_price) for order_line in shipping_lines]
    assert allocations == [Decimal("3.33"), Decimal("3.33"), Decimal("3.34")]
    assert sum(allocations) == Decimal("10.00")


def test_shipping_fee_is_optional() -> None:
    """L'absence de frais de port ne doit créer aucune ligne."""
    order = Order(id=1)
    lines = [(_order_line(vat_rate_id=1, vat_rate="20", unit_price="10"), 1)]

    assert not _create_shipping_fee_lines(order, lines, None)


def test_shipping_fee_uses_negative_quantity_for_credit_note() -> None:
    """Le port d'un avoir doit être négatif malgré une saisie positive."""
    order = Order(id=1)
    lines = [(_order_line(vat_rate_id=1, vat_rate="20", unit_price="10"), -1)]

    shipping_lines = _create_shipping_fee_lines(order, lines, Decimal("4.50"))

    order_line = shipping_lines[0]
    assert order_line.quantity == -1
    assert Decimal(order_line.unit_price) == Decimal("4.50")


def test_invoice_order_flushes_shipping_order_lines_before_invoice_lines(
    monkeypatch,
) -> None:
    """Les lignes de facture de port doivent être créées après le flush de leurs lignes source."""
    product = MagicMock(ean13="9781234567890", name="Livre")
    source_line = _order_line(vat_rate_id=1, vat_rate="20", unit_price="10")
    source_line.id = 1
    source_line.general_object = product
    vat_rate = VatRate(id=1, code=3, rate=20, label="TVA 20 %")
    source_line.vat_rate_ref = vat_rate
    fee_product = InvoiceFeeProduct(
        id=10,
        fee_type="shipping",
        vat_rate=vat_rate,
        reference="PORT-1",
        description="Frais de port (TVA 20 %)",
    )
    order = MagicMock(
        customer_id=1,
        status="draft",
        order_lines=[source_line],
    )
    session = MagicMock()
    shipping_lines: list[OrderLine] = []

    def add_shipping_lines(lines: list[OrderLine]) -> None:
        shipping_lines.extend(lines)

    def flush_shipping_lines() -> None:
        for index, shipping_line in enumerate(shipping_lines, start=100):
            shipping_line.id = index

    session.add_all.side_effect = add_shipping_lines
    session.flush.side_effect = flush_shipping_lines
    order_repository = MagicMock(get_by_id=MagicMock(return_value=order))
    invoice_repository = MagicMock()
    created_invoice = MagicMock()
    invoice_repository.create_invoice.return_value = created_invoice
    monkeypatch.setattr(order_utils.db_conf, "get_main_session", lambda: session)
    monkeypatch.setattr(order_utils, "OrdersRepository", lambda _: order_repository)
    monkeypatch.setattr(order_utils, "InvoiceRepository", lambda _: invoice_repository)
    monkeypatch.setattr(
        order_utils,
        "get_or_create_invoice_fee_product",
        lambda *_args, **_kwargs: fee_product,
    )
    monkeypatch.setattr(
        order_utils,
        "_sync_invoice_with_henrri",
        lambda invoice, _: invoice,
    )

    order_utils.invoice_order(
        1,
        [{"order_line_id": 1, "quantity": 1}],
        shipping_fee=Decimal("2"),
    )

    invoice_lines = invoice_repository.create_invoice.call_args.kwargs["line_items"]
    assert session.add_all.call_args.args[0] == shipping_lines
    assert all(line.order_line_id is not None for line in invoice_lines)
    assert invoice_lines[-1].order_line_id == 100
    assert shipping_lines[0].invoice_fee_product is fee_product


def test_ship_order_rejects_shipping_fee_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Les frais de port ne doivent jamais devenir des lignes d'expédition."""
    shipping_fee = OrderLine(
        id=1,
        order_id=1,
        general_object_id=None,
        is_shipping_fee=True,
        quantity=1,
        unit_price=10,
        discount=0,
        vat_rate=20,
        vat_rate_id=1,
        status="invoiced",
        create_source="test",
    )
    session = MagicMock()
    order = MagicMock(order_lines=[shipping_fee])
    order_repository = MagicMock(get_by_id=MagicMock(return_value=order))
    monkeypatch.setattr(order_utils.db_conf, "get_main_session", lambda: session)
    monkeypatch.setattr(order_utils, "OrdersRepository", lambda _: order_repository)

    with pytest.raises(ValueError, match="frais de port"):
        order_utils.ship_order(
            1,
            [{"order_line_id": 1, "quantity": 1}],
            carrier="Colissimo",
        )


def test_shipping_fee_does_not_make_order_partially_shipped() -> None:
    """Un port facturé ne doit pas compter comme un article non expédié."""
    article = _order_line(vat_rate_id=1, vat_rate="20", unit_price="10")
    article.id = 1
    article.status = "shipped"
    shipping_fee = _order_line(vat_rate_id=1, vat_rate="20", unit_price="2")
    shipping_fee.id = 2
    shipping_fee.general_object_id = None
    shipping_fee.is_shipping_fee = True
    shipping_fee.status = "invoiced"
    order = Order(
        id=1,
        status="partial_shipped",
        order_lines=[article, shipping_fee],
    )
    repository = MagicMock()

    order_utils._recalculate_order_status(order, repository)  # pylint: disable=W0212

    repository.update_order_status.assert_called_once_with(
        order,
        "shipped",
        update_source="backoffice",
    )
