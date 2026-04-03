"""Blueprint HTMX pour la gestion des commandes (liste, modales)."""

from flask import Blueprint, make_response, render_template, request
from app_front.blueprints.order.utils import (
    search_orders_paginated,
    get_order_by_id,
    cancel_order,
)

bp_order_htmx_list = Blueprint(
    "order_htmx_list",
    __name__,
    url_prefix="/order/htmx/list",
)

ORDER_TABLE = "htmx_templates/order/list/table.html"
ORDER_VIEW_MODAL = "htmx_templates/order/list/view_modal.html"
ORDER_CANCEL_MODAL = "htmx_templates/order/list/cancel_modal.html"
ORDER_NOT_FOUND = "<p>Commande introuvable.</p>"


@bp_order_htmx_list.get("/table")
def order_table():
    """Retourne le tableau filtré et paginé des commandes (HTMX)."""
    reference = request.args.get("reference", "").strip() or None
    customer_name = request.args.get("customer_name", "").strip() or None
    status_list = request.args.getlist("status")
    status: str | list[str] | None = None
    if len(status_list) > 1:
        status = status_list
    elif status_list and status_list[0]:
        status = status_list[0]
    date_from = request.args.get("date_from", "").strip() or None
    date_to = request.args.get("date_to", "").strip() or None

    page_str = request.args.get("page", "1").strip()
    page = max(1, int(page_str)) if page_str.isdigit() else 1

    result = search_orders_paginated(
        reference=reference,
        customer_name=customer_name,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
    )
    return render_template(ORDER_TABLE, **result)


@bp_order_htmx_list.get("/view/<int:order_id>")
def order_view(order_id: int):
    """Retourne la modale de consultation d'une commande (HTMX)."""
    order = get_order_by_id(order_id)
    if order is None:
        return ORDER_NOT_FOUND, 404
    return render_template(ORDER_VIEW_MODAL, order=order)


@bp_order_htmx_list.get("/cancel/<int:order_id>")
def order_cancel_modal(order_id: int):
    """Retourne la modale de confirmation d'annulation (HTMX)."""
    order = get_order_by_id(order_id)
    if order is None:
        return ORDER_NOT_FOUND, 404
    return render_template(ORDER_CANCEL_MODAL, order=order)


@bp_order_htmx_list.post("/cancel/<int:order_id>")
def order_cancel_submit(order_id: int):
    """Annule une commande (HTMX)."""
    try:
        cancel_order(order_id)
    except ValueError:
        return "<p>Erreur lors de l'annulation de la commande.</p>", 422

    response = make_response("", 200)
    response.headers["HX-Trigger"] = "refreshOrderTable"
    return response
