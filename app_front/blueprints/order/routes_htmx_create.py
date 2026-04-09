"""Blueprint HTMX pour la création de commandes et gestion des lignes."""

from flask import Blueprint, make_response, render_template, request, url_for
from app_front.blueprints.order.forms import OrderCreateForm, OrderLineForm, QuickCustomerForm
from app_front.blueprints.order.utils import (
    create_order,
    add_order_line,
    remove_order_line,
    get_order_by_id,
    get_customer_order_addresses,
    update_order_delivery_address,
    search_customers_for_dropdown,
    invoice_order,
    ship_order,
    get_objects_by_name,
)
from app_front.blueprints.customer.utils.users import create_from_dict
from app_front.utils.pages import render_page

bp_order_htmx_create = Blueprint(
    "order_htmx_create",
    __name__,
    url_prefix="/order/htmx/create",
)

CUSTOMER_DROPDOWN = "htmx_templates/order/create/customer_dropdown.html"
QUICK_CUSTOMER_MODAL = "htmx_templates/order/create/quick_customer_modal.html"
ORDER_LINES_TABLE = "htmx_templates/order/create/lines_table.html"
ARTICLE_DROPDOWN = "htmx_templates/order/create/article_dropdown.html"
ADDRESS_SELECTOR = "htmx_templates/order/create/address_selector.html"
_EDIT_ORDER_ROUTE = "order_htmx_create.edit_order"
_VIEW_ORDER_ROUTE = "order.order_view"


# ── Page de création ─────────────────────────────────────────────────────

@bp_order_htmx_create.get("/")
def create_page():
    """Page de création d'une commande."""
    form = OrderCreateForm()
    line_form = OrderLineForm()
    return render_page("order_create", create_form=form, line_form=line_form)


@bp_order_htmx_create.post("/submit")
def create_submit():
    """Crée la commande à partir du client sélectionné."""
    form = OrderCreateForm()
    if form.validate_on_submit():
        customer_id = int(form.customer_id.data)  # type: ignore[arg-type]
        delivery_address_id = int(form.delivery_address_id.data)  # type: ignore[arg-type]
        result = create_order(customer_id, delivery_address_id)
        order_id = result.get("id")
        if order_id is None:
            return "<p>Erreur lors de la création de la commande.</p>", 500
        response = make_response("", 200)
        response.headers["HX-Redirect"] = url_for(
            _EDIT_ORDER_ROUTE, order_id=order_id
        )
        return response
    return "<p>Veuillez sélectionner un client et une adresse de livraison.</p>", 422


@bp_order_htmx_create.get("/customer-addresses/<int:customer_id>")
def customer_addresses(customer_id: int):
    """Retourne les adresses utilisables pour créer une commande client."""
    try:
        addresses = get_customer_order_addresses(customer_id)
    except ValueError as exc:
        return f"<p class='error'>{exc}</p>", 422

    return render_template(ADDRESS_SELECTOR, addresses=addresses)


# ── Édition d'une commande (ajout de lignes) ─────────────────────────────

@bp_order_htmx_create.get("/edit/<int:order_id>")
def edit_order(order_id: int):
    """Page d'édition d'une commande (ajout de lignes, récapitulatif)."""
    order = get_order_by_id(order_id)
    if order is None:
        return "<p>Commande introuvable.</p>", 404
    line_form = OrderLineForm()
    return render_page("order_edit", order=order, line_form=line_form)


@bp_order_htmx_create.post("/edit/<int:order_id>/delivery-address")
def update_delivery_address(order_id: int):
    """Met à jour l'adresse de livraison tant que la commande est en brouillon."""
    delivery_address_id = request.form.get("delivery_address_id", type=int)
    if not delivery_address_id:
        return "<p class='error'>Adresse de livraison manquante.</p>", 422

    try:
        update_order_delivery_address(order_id, delivery_address_id)
        refreshed_order = get_order_by_id(order_id)
        if refreshed_order is None:
            return "<p class='error'>Commande introuvable.</p>", 404
    except ValueError as exc:
        return f"<p class='error'>{exc}</p>", 422

    return render_template(
        "htmx_templates/order/create/delivery_address_info.html",
        order=refreshed_order,
    )


# ── Gestion des lignes (HTMX) ───────────────────────────────────────────

@bp_order_htmx_create.post("/line/<int:order_id>")
def add_line(order_id: int):
    """Ajoute une ligne de commande (HTMX)."""
    form = OrderLineForm()
    if form.validate_on_submit():
        try:
            add_order_line(
                order_id,
                general_object_id=int(form.general_object_id.data),  # type: ignore[arg-type]
                quantity=form.quantity.data or 1,
                unit_price=float(form.unit_price.data or 0),
                vat_rate=float(form.vat_rate.data or 0),
                discount=float(form.discount.data or 0),
            )
        except ValueError as exc:
            return f"<p class='error'>{exc}</p>", 422

        response = make_response("", 200)
        response.headers["HX-Trigger"] = "refreshOrderLines"
        return response
    return "<p>Formulaire invalide.</p>", 422


@bp_order_htmx_create.delete("/line/<int:order_id>/<int:line_id>")
def delete_line(order_id: int, line_id: int):
    """Supprime une ligne de commande (HTMX)."""
    try:
        remove_order_line(order_id, line_id)
    except ValueError as exc:
        return f"<p class='error'>{exc}</p>", 422

    response = make_response("", 200)
    response.headers["HX-Trigger"] = "refreshOrderLines"
    return response


@bp_order_htmx_create.post("/invoice/<int:order_id>")
def invoice_order_route(order_id: int):
    """Crée une facture pour les lignes sélectionnées avec quantités (HTMX)."""
    line_ids = request.form.getlist("line_ids", type=int)
    quantities = request.form.getlist("quantities", type=int)

    if not line_ids:
        return "<p class='error'>Aucune ligne sélectionnée.</p>", 422

    line_items = []
    for i, lid in enumerate(line_ids):
        qty = quantities[i] if i < len(quantities) else 0
        if qty > 0:
            line_items.append({"order_line_id": lid, "quantity": qty})

    if not line_items:
        return "<p class='error'>Aucune quantité valide.</p>", 422

    try:
        invoice_order(order_id, line_items=line_items)
    except ValueError as exc:
        return f"<p class='error'>{exc}</p>", 422
    response = make_response("", 200)
    response.headers["HX-Redirect"] = url_for(
        _VIEW_ORDER_ROUTE, order_id=order_id
    )
    return response


@bp_order_htmx_create.post("/ship/<int:order_id>")
def ship_order_route(order_id: int):
    """Crée un envoi pour les lignes sélectionnées avec quantités (HTMX)."""
    line_ids = request.form.getlist("line_ids", type=int)
    quantities = request.form.getlist("quantities", type=int)
    carrier = request.form.get("carrier", "").strip()
    tracking_number = request.form.get("tracking_number", "").strip() or None

    if not line_ids:
        return "<p class='error'>Aucune ligne sélectionnée.</p>", 422
    if not carrier:
        return "<p class='error'>Le transporteur est obligatoire.</p>", 422

    line_items = []
    for i, lid in enumerate(line_ids):
        qty = quantities[i] if i < len(quantities) else 0
        if qty > 0:
            line_items.append({"order_line_id": lid, "quantity": qty})

    if not line_items:
        return "<p class='error'>Aucune quantité valide.</p>", 422

    try:
        ship_order(
            order_id,
            line_items=line_items,
            carrier=carrier,
            tracking_number=tracking_number,
        )
    except ValueError as exc:
        return f"<p class='error'>{exc}</p>", 422
    response = make_response("", 200)
    response.headers["HX-Redirect"] = url_for(
        _VIEW_ORDER_ROUTE, order_id=order_id
    )
    return response


@bp_order_htmx_create.get("/lines/<int:order_id>")
def order_lines(order_id: int):
    """Retourne le fragment des lignes de commande (HTMX)."""
    order = get_order_by_id(order_id)
    if order is None:
        return "<p>Commande introuvable.</p>", 404
    return render_template(ORDER_LINES_TABLE, order=order)


# ── Recherche clients (dropdown HTMX) ───────────────────────────────────

@bp_order_htmx_create.get("/customers")
def search_customers():
    """Recherche de clients pour le dropdown (HTMX)."""
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return ""
    customers = search_customers_for_dropdown(query)
    return render_template(CUSTOMER_DROPDOWN, customers=customers, query=query)


# ── Création rapide client (modale) ──────────────────────────────────────

@bp_order_htmx_create.get("/quick-customer")
def quick_customer_form():
    """Affiche la modale de création rapide de client (HTMX)."""
    form = QuickCustomerForm()
    return render_template(QUICK_CUSTOMER_MODAL, form=form)


@bp_order_htmx_create.post("/quick-customer")
def quick_customer_submit():
    """Crée un client rapidement depuis la commande (HTMX)."""
    form = QuickCustomerForm()
    if form.validate_on_submit():
        customer_data = {"customer_type": form.customer_type.data}
        if form.customer_type.data == "part":
            customer_data["part"] = {
                "civil_title": form.civil_title.data,
                "first_name": form.first_name.data,
                "last_name": form.last_name.data,
            }
        else:
            customer_data["pro"] = {
                "company_name": form.company_name.data,
            }

        try:
            customer_id = create_from_dict(customer_data)
        except (ValueError, TypeError) as exc:
            return f"<p class='error'>Erreur : {exc}</p>", 422

        response = make_response("", 200)
        response.headers["HX-Trigger"] = "customerCreated"
        response.headers["HX-Trigger-After-Settle"] = (
            f'{{"selectCustomer": {{"id": {customer_id}}}}}'
        )
        return response

    return render_template(QUICK_CUSTOMER_MODAL, form=form), 422


# ── Recherche articles (dropdown HTMX) ───────────────────────────────────

@bp_order_htmx_create.get("/articles")
def search_articles():
    """Recherche d'articles pour le dropdown (HTMX)."""
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return ""
    try:
        results = get_objects_by_name(query)
        if results is None:
            results = []
        articles = []
        for a in results:
            articles.append({
                "id": a.id,
                "name": a.name,
                "ean13": a.ean13 or "",
                "price": float(a.price) if a.price else 0,
                "vat_rate_id": a.vat_rate_id,
            })
        return render_template(ARTICLE_DROPDOWN, articles=articles, query=query)
    except ValueError as exc:
        return f"<p class='error'>Erreur : {exc}</p>", 422
