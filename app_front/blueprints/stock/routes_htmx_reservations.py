"""Blueprint API HTMX pour le module réservations de stock.

Réutilise les templates des commandes fournisseurs avec le flag reservation=True.
"""

from flask import Blueprint, render_template, request
from app_front.blueprints.stock.forms import (
    OrderInCreateForm,
    OrderInLineForm,
)
from app_front.blueprints.stock.utils import (
    get_supplier_orders,
    get_order_by_id,
    create_order_in_db,
    edit_order_in_line_db,
    cancel_supplier_order,
    confirm_supplier_order,
    return_reservation,
)

bp_stock_htmx_reservations = Blueprint(
    "stock_htmx_reservations",
    __name__,
    url_prefix="/stock/htmx/reservations",
    template_folder="htmx_templates/stock",
)

# Réutilisation des templates commandes avec flag reservation=True
SECTION_HOME = "htmx_templates/stock/orders/sections/home.html"
SECTION_VIEW = "htmx_templates/stock/orders/sections/view.html"
SECTION_NEW = "htmx_templates/stock/orders/sections/new.html"
SECTION_CANCELED = "htmx_templates/stock/orders/sections/canceled.html"
SECTION_CONFIRMED = "htmx_templates/stock/orders/sections/confirmed.html"
NEW_LINE = "htmx_templates/stock/orders/fragments/new_line.html"

CTX = {"reservation": True}


@bp_stock_htmx_reservations.get("/cleared")
def cleared():
    """Retourne une section vide pour réinitialiser l'affichage (HTMX)."""
    return ""


@bp_stock_htmx_reservations.get("/")
def reservations_list():
    """Retourne la liste des réservations (HTMX)."""
    orders = get_supplier_orders(reservation=True)
    return render_template(SECTION_HOME, orders=orders, **CTX)


@bp_stock_htmx_reservations.route("/section/create", methods=["GET", "POST"])
def new_reservation_section():
    """Formulaire de création d'une nouvelle réservation (HTMX)."""
    form = OrderInCreateForm()
    if form.validate_on_submit():
        reservation_id = create_order_in_db(form, reservation=True)
        order = get_order_by_id(reservation_id)
        return render_template(SECTION_VIEW, view_state="new", order=order, **CTX)
    if request.method == "POST":
        msg = "Formulaire invalide : " + str(form.errors)
        raise ValueError(msg)
    return render_template(SECTION_NEW, form=form, **CTX)


@bp_stock_htmx_reservations.get("/<int:order_id>/section/edit")
def edit_reservation(order_id: int):
    """Retourne la vue d'édition d'une réservation (HTMX)."""
    order = get_order_by_id(order_id)
    return render_template(SECTION_VIEW, order=order, view_state="edit", **CTX)


@bp_stock_htmx_reservations.get("/view/<int:order_id>")
def view_reservation(order_id: int):
    """Retourne la vue détaillée d'une réservation (HTMX)."""
    order = get_order_by_id(order_id)
    return render_template(SECTION_VIEW, order=order, view_state="view", **CTX)


@bp_stock_htmx_reservations.route("/<int:order_id>/line/create", methods=["GET", "POST"])
def new_reservation_line(order_id: int):
    """Formulaire d'ajout d'une ligne de réservation (HTMX)."""
    form = OrderInLineForm()
    form.order_id.data = str(order_id)
    if form.validate_on_submit():
        edit_order_in_line_db(form, action="create", order_id=order_id, reservation=True)
        order = get_order_by_id(order_id)
        return render_template(SECTION_VIEW, order=order, view_state="new", **CTX)
    return render_template(NEW_LINE, form=form, view_state="create", **CTX)


@bp_stock_htmx_reservations.route(
    "/<int:order_id>/line/<int:line_id>/delete", methods=["GET", "POST"]
)
def delete_reservation_line(order_id: int, line_id: int):
    """Supprime une ligne de réservation (HTMX)."""
    if request.method == "POST":
        form = OrderInLineForm()
        edit_order_in_line_db(form, action="delete", line_id=line_id, order_id=order_id)
        return render_template(
            SECTION_CANCELED, deleted=True, line_id=line_id, mod="line", **CTX
        )
    return render_template(SECTION_CANCELED, line_id=line_id, mod="line", **CTX)


@bp_stock_htmx_reservations.route("/cancel/<int:order_id>", methods=["GET", "POST"])
def cancel_reservation(order_id: int):
    """Supprime une réservation brouillon (HTMX)."""
    if request.method == "POST":
        cancel_supplier_order(order_id, reservation=True)
        return render_template(
            SECTION_CANCELED, order_id=order_id, deleted=True,
            mod="reservation", **CTX
        )
    return render_template(
        SECTION_CANCELED, order_id=order_id, deleted=False,
        mod="reservation", **CTX
    )


@bp_stock_htmx_reservations.route("/<int:order_id>/return", methods=["GET", "POST"])
def return_reservation_route(order_id: int):
    """Retourne (clôture) une réservation (HTMX)."""
    if request.method == "POST":
        return_reservation(order_id)
        order = get_order_by_id(order_id)
        return render_template(SECTION_CONFIRMED, order=order, returned=True, **CTX)
    order = get_order_by_id(order_id)
    return render_template(SECTION_CONFIRMED, order=order, confirm_return=True, **CTX)


@bp_stock_htmx_reservations.post("/<int:order_id>/confirm")
def confirm_reservation(order_id: int):
    """Confirme une réservation (draft → sended) (HTMX)."""
    confirm_supplier_order(order_id)
    order = get_order_by_id(order_id)
    return render_template(SECTION_CONFIRMED, order=order, **CTX)
