"""Blueprint pour les fonctionnalités du tableau de bord (API JSON)

Endpoints:
- /dashboard/data/finances
- /dashboard/data/commandes
- /dashboard/data/stock
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from app_front.blueprints.dashboard.utils import define_period
from app_front.config import db_conf
from app_front.utils.decorators import (
    permission_required, DIRECTION, ADMIN, COMMERCIAL, COMPTA, LOGISTIQUE
)
from db_models.objects import (
    CustomerParts,
    CustomerPros,
    Customers,
    GeneralObjects,
    InventoryMovements,
    Invoice,
    Order,
    OrderLine,
)

bp_dashboard_data = Blueprint("dashboard_data", __name__, url_prefix="/dashboard/data")

STATUS_LABELS = {
    "draft": "En cours",
    "partial_invoiced": "En cours",
    "invoiced": "En cours",
    "partial_shipped": "En cours",
    "shipped": "Expédiée",
    "cancelled": "Annulée",
    "returned": "Retournée",
}

CATEGORY_LABELS = {
    "book": "Livres",
    "other": "Objets",
}


def _parse_start_date(value: str | None) -> datetime | None:
    """Parse une date ISO YYYY-MM-DD vers datetime UTC."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _period_bounds(start_value: str | None, period: str) -> tuple[datetime, datetime] | None:
    """Retourne les bornes de période ou None si aucun filtre temporel applicable."""
    period = (period or "").upper()
    if not period and not start_value:
        return None

    start = _parse_start_date(start_value)
    if start is None:
        now = datetime.now(timezone.utc)
        if period == "A":
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "S":
            month = 1 if now.month <= 6 else 7
            start = now.replace(month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "T":
            quarter_start_month = ((now.month - 1) // 3) * 3 + 1
            start = now.replace(
                month=quarter_start_month,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        elif period == "W":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    range_code = period or "M"
    try:
        start_dt, end_dt = define_period(start, range_code)
    except ValueError:
        start_dt, end_dt = define_period(start, "M")
    return start_dt, end_dt


def _customer_name(customer: Customers | None) -> str:
    """Retourne le nom lisible du client."""
    if customer is None:
        return "Client inconnu"
    if customer.customer_type == "part" and customer.part:
        return f"{customer.part.first_name} {customer.part.last_name}".strip()
    if customer.customer_type == "pro" and customer.pro:
        return customer.pro.company_name
    return f"Client #{customer.id}"


def _order_total_ttc(order: Order) -> float:
    """Calcule le montant TTC d'une commande à partir des lignes actives."""
    total = 0.0
    for line in (order.order_lines or []):
        if line.status == "cancelled":
            continue
        quantity = int(line.quantity or 0)
        unit_price = float(line.unit_price or 0)
        discount = float(line.discount or 0)
        vat_rate = float(line.vat_rate or 0)
        line_ht = quantity * unit_price
        line_ht_after_discount = line_ht * (1 - (discount / 100))
        total += line_ht_after_discount * (1 + (vat_rate / 100))
    return round(total, 2)


def _build_stock_snapshot(
        session,
        object_ids: set[int] | None = None
    ) -> dict[int, dict[str, float | str]]:
    """Construit un snapshot de stock courant par article."""
    im = InventoryMovements
    go = GeneralObjects

    latest_inv_ts = (
        select(im.general_object_id, func.max(im.movement_timestamp).label("max_ts"))
        .where(im.movement_type == "inventory")
        .group_by(im.general_object_id)
        .subquery()
    )

    latest_inv_qty = (
        select(
            im.general_object_id,
            im.quantity.label("inv_qty"),
            im.movement_timestamp.label("inv_ts"),
        )
        .join(
            latest_inv_ts,
            and_(
                im.general_object_id == latest_inv_ts.c.general_object_id,
                im.movement_timestamp == latest_inv_ts.c.max_ts,
            ),
        )
        .where(im.movement_type == "inventory")
        .subquery()
    )

    in_after = (
        select(im.general_object_id, func.coalesce(func.sum(im.quantity), 0).label("in_qty"))
        .join(latest_inv_qty, im.general_object_id == latest_inv_qty.c.general_object_id)
        .where(
            im.movement_type == "in",
            im.movement_timestamp > latest_inv_qty.c.inv_ts,
        )
        .group_by(im.general_object_id)
        .subquery()
    )

    out_after = (
        select(im.general_object_id, func.coalesce(func.sum(im.quantity), 0).label("out_qty"))
        .join(latest_inv_qty, im.general_object_id == latest_inv_qty.c.general_object_id)
        .where(
            im.movement_type == "out",
            im.movement_timestamp > latest_inv_qty.c.inv_ts,
        )
        .group_by(im.general_object_id)
        .subquery()
    )

    reserved_after = (
        select(
            im.general_object_id,
            func.coalesce(func.sum(im.quantity), 0).label("reserved_qty"),
        )
        .join(latest_inv_qty, im.general_object_id == latest_inv_qty.c.general_object_id)
        .where(
            im.movement_type == "reserved",
            im.movement_timestamp > latest_inv_qty.c.inv_ts,
        )
        .group_by(im.general_object_id)
        .subquery()
    )

    qty_expr = (
        func.coalesce(latest_inv_qty.c.inv_qty, 0)
        + func.coalesce(in_after.c.in_qty, 0)
        - func.abs(func.coalesce(out_after.c.out_qty, 0))
        - func.coalesce(reserved_after.c.reserved_qty, 0)
    ).label("stock_qty")

    stmt = (
        select(
            go.id,
            go.general_object_type,
            go.price.label("price"),
            go.name,
            qty_expr,
        )
        .outerjoin(latest_inv_qty, go.id == latest_inv_qty.c.general_object_id)
        .outerjoin(in_after, go.id == in_after.c.general_object_id)
        .outerjoin(out_after, go.id == out_after.c.general_object_id)
        .outerjoin(reserved_after, go.id == reserved_after.c.general_object_id)
    )

    if object_ids:
        stmt = stmt.where(go.id.in_(object_ids))

    rows = session.execute(stmt).all()
    stock_by_object: dict[int, dict[str, float | str]] = {}
    for row in rows:
        stock_by_object[int(row.id)] = {
            "qty": float(row.stock_qty or 0),
            "price": float(row.price or 0),
            "category": str(row.general_object_type or "Autres"),
            "name": str(row.name or f"Objet #{row.id}"),
        }
    return stock_by_object


def _availability_for_order(
        order: Order,
        stock_by_object: dict[int, dict[str, float | str]]
    ) -> str:
    """Retourne un statut de disponibilité global pour la commande."""
    active_lines = [line for line in (order.order_lines or []) if line.status != "cancelled"]
    if not active_lines:
        return "Indisponible"

    fully_available = 0
    partially_available = 0
    for line in active_lines:
        line_qty = int(line.quantity or 0)
        stock_qty = float(stock_by_object.get(line.general_object_id, {}).get("qty", 0))
        if stock_qty >= line_qty and line_qty > 0:
            fully_available += 1
        elif stock_qty > 0:
            partially_available += 1

    if fully_available == len(active_lines):
        return "Disponible"
    if fully_available > 0 or partially_available > 0:
        return "Partielle"
    return "Indisponible"


def _month_key(value: datetime) -> str:
    """Retourne une clé de mois pour agréger les séries."""
    return value.strftime("%Y-%m")


def _month_label(key: str) -> str:
    """Convertit une clé de mois en libellé FR court."""
    dt = datetime.strptime(f"{key}-01", "%Y-%m-%d")
    names = {
        1: "Jan",
        2: "Fev",
        3: "Mar",
        4: "Avr",
        5: "Mai",
        6: "Jun",
        7: "Jul",
        8: "Aou",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dec",
    }
    return f"{names[dt.month]} {dt.year}"


def _ordered_month_keys(start: datetime, end: datetime) -> list[str]:
    """Liste tous les mois entre deux bornes incluses."""
    cursor = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    limit = end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    keys: list[str] = []
    while cursor <= limit:
        keys.append(_month_key(cursor))
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)
    return keys


@bp_dashboard_data.get("/finances")
@permission_required([DIRECTION, ADMIN, COMMERCIAL, COMPTA, LOGISTIQUE], _and=False)
def finances():
    """Retourne les KPIs financiers pour une plage donnée.

    Query params:
    - start_date,
    - range (A, S, T, M, W) : Annual, Semestrial, Trimestrial, Monthly, Weekly
    - kpis (list[str]):
        - ca_sum: CA total
        - ca_paid: CA payé
        - ca_outstanding: CA à encaisser
        - average_margin: marge moyenne
        - pending_invoicing: en attente de facturation
        - pending_shipment: en attente d'envoi
    """
    range_code = request.args.get("range", "A").upper()
    bounds = _period_bounds(request.args.get("start_date"), range_code)
    if bounds is None:
        now = datetime.now(timezone.utc)
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=0)
    else:
        start, end = bounds

    session = db_conf.get_main_session()
    month_keys = _ordered_month_keys(start, end)
    ressources_by_month = {key: 0.0 for key in month_keys}
    charges_by_month = {key: 0.0 for key in month_keys}

    invoice_stmt = (
        select(Invoice.created_at, Invoice.total_amount, Invoice.vat_amount)
        .where(Invoice.created_at >= start, Invoice.created_at <= end)
    )
    for created_at, total_amount, vat_amount in session.execute(invoice_stmt).all():
        if created_at is None:
            continue
        key = _month_key(created_at)
        if key not in ressources_by_month:
            continue
        ht = float(total_amount or 0)
        vat = float(vat_amount or 0)
        ressources_by_month[key] += ht + vat

    movement_stmt = (
        select(
            InventoryMovements.movement_timestamp,
            InventoryMovements.quantity,
            InventoryMovements.price_at_movement
        )
        .where(
            InventoryMovements.movement_type == "in",
            InventoryMovements.movement_timestamp >= start,
            InventoryMovements.movement_timestamp <= end,
        )
    )
    for movement_ts, qty, unit_price in session.execute(movement_stmt).all():
        if movement_ts is None:
            continue
        key = _month_key(movement_ts)
        if key not in charges_by_month:
            continue
        charges_by_month[key] += float(qty or 0) * float(unit_price or 0)

    months = [_month_label(key) for key in month_keys]
    charges = [round(charges_by_month[key], 2) for key in month_keys]
    ressources = [round(ressources_by_month[key], 2) for key in month_keys]
    return jsonify({"months": months, "charges": charges, "ressources": ressources})


@bp_dashboard_data.get("/commandes")
@permission_required([DIRECTION, ADMIN, COMMERCIAL, COMPTA, LOGISTIQUE], _and=False)
def commandes():
    """Liste des commandes avec filtres de base pour le dashboard.

    Query params:
    - status (ex: pending, shipped, cancelled)
    - search (sur référence)
    - page, per_page pour pagination (optional, défaut page=1, per_page=25)
    - start_date (optional, pour filtrer par date de création),
    - range (A, S, T, M, W) : Annual, Semestrial, Trimestrial, Monthly, Weekly (optional)
    """
    status_filter = request.args.get("status")
    search = request.args.get("search")
    try:
        page = max(int(request.args.get("page", 1) or 1), 1)
        per_page = max(min(int(request.args.get("per_page", 25) or 25), 100), 1)
    except (TypeError, ValueError):
        return jsonify({"error": "Les paramètres de pagination doivent être numériques."}), 400
    bounds = _period_bounds(request.args.get("start_date"), request.args.get("range", ""))

    session = db_conf.get_main_session()
    stmt = (
        select(Order)
        .options(
            joinedload(Order.customer).joinedload(Customers.part),
            joinedload(Order.customer).joinedload(Customers.pro),
            selectinload(Order.order_lines).joinedload(OrderLine.general_object),
        )
        .order_by(Order.created_at.desc())
    )

    if search:
        search_clause = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Order.reference.ilike(search_clause),
                CustomerParts.first_name.ilike(search_clause),
                CustomerParts.last_name.ilike(search_clause),
                CustomerPros.company_name.ilike(search_clause),
            )
        ).join(Customers, Order.customer_id == Customers.id)
        stmt = stmt.outerjoin(CustomerParts, CustomerParts.customer_id == Customers.id)
        stmt = stmt.outerjoin(CustomerPros, CustomerPros.customer_id == Customers.id)

    if status_filter:
        raw_status = [status.strip() for status in status_filter.split(",") if status.strip()]
        if raw_status:
            stmt = stmt.where(Order.status.in_(raw_status))

    if bounds is not None:
        start, end = bounds
        stmt = stmt.where(Order.created_at >= start, Order.created_at <= end)

    stmt = stmt.limit(per_page).offset((page - 1) * per_page)
    orders = session.execute(stmt).scalars().unique().all()

    object_ids: set[int] = {
        int(line.general_object_id)
        for order in orders
        for line in (order.order_lines or [])
        if line.general_object_id is not None and line.status != "cancelled"
    }
    stock_by_object = _build_stock_snapshot(session, object_ids)

    payload = []
    for order in orders:
        payload.append(
            {
                "name": _customer_name(order.customer),
                "date": order.created_at.strftime("%d/%m/%Y") if order.created_at else "—",
                "amount": _order_total_ttc(order),
                "availability": _availability_for_order(order, stock_by_object),
                "status": STATUS_LABELS.get(order.status, order.status),
            }
        )

    return jsonify(payload)


@bp_dashboard_data.get("/stock")
@permission_required([DIRECTION, ADMIN, COMMERCIAL, COMPTA, LOGISTIQUE], _and=False)
def stock():
    """Endpoints pour vues stock: slow_moving ou by_category

    Query params:
    - view=slow_moving|by_category,
    - limit,
    - category_id,
    - range
    """
    view = request.args.get("view", "by_category")
    limit = max(min(int(request.args.get("limit", 6) or 6), 50), 1)
    bounds = _period_bounds(request.args.get("start_date"), request.args.get("range", ""))

    session = db_conf.get_main_session()
    stock_snapshot = _build_stock_snapshot(session)

    if view == "slow_moving":
        last_mvt_sq = (
            select(
                InventoryMovements.general_object_id,
                func.max(InventoryMovements.movement_timestamp).label("last_ts"),
            )
            .group_by(InventoryMovements.general_object_id)
            .subquery()
        )
        mvt_map = {
            int(row.general_object_id): row.last_ts
            for row in session.execute(
                select(
                    last_mvt_sq.c.general_object_id,
                    last_mvt_sq.c.last_ts
                )
            ).all()
        }
        if bounds is not None:
            _, end = bounds
        else:
            end = datetime.now(timezone.utc)

        candidates = []
        for object_id, values in stock_snapshot.items():
            qty = float(values.get("qty", 0))
            if qty <= 0:
                continue
            last_ts = mvt_map.get(object_id)
            if last_ts is None or last_ts <= end:
                candidates.append((
                        str(values.get("name", f"Objet #{object_id}")),
                        qty,
                        float(values.get("price", 0))
                ))

        candidates.sort(key=lambda item: item[1], reverse=True)
        selected = candidates[:limit]
        labels = [row[0] for row in selected]
        values = [int(row[1]) for row in selected]
        value_total = round(sum(row[1] * row[2] for row in selected), 2)
        items_total = int(sum(values))
        return jsonify(
            {
                "labels": labels,
                "values": values,
                "value_total": value_total,
                "items_total": items_total,
            }
        )

    grouped: dict[str, dict[str, float]] = {}
    for values in stock_snapshot.values():
        category_code = str(values.get("category", "Autres"))
        category = CATEGORY_LABELS.get(category_code, category_code.capitalize())
        qty = float(values.get("qty", 0))
        price = float(values.get("price", 0))

        if category not in grouped:
            grouped[category] = {"qty": 0.0, "value": 0.0}
        grouped[category]["qty"] += qty
        grouped[category]["value"] += qty * price

    ranked = sorted(grouped.items(), key=lambda item: item[1]["qty"], reverse=True)[:limit]
    labels = [item[0] for item in ranked]
    values = [int(round(item[1]["qty"])) for item in ranked]
    value_total = round(sum(item[1]["value"] for item in ranked), 2)
    items_total = int(sum(values))

    return jsonify(
        {
            "labels": labels,
            "values": values,
            "value_total": value_total,
            "items_total": items_total,
        }
    )
