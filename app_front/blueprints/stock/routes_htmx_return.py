"""Blueprint API HTMX pour les retours fournisseurs.

Les retours fournisseurs réutilisent le modèle OrderIn avec le préfixe RET-.
Ils suivent le même cycle de vie que les commandes fournisseurs :
draft → sended → received (via réception ligne par ligne).
"""

from flask import Blueprint, render_template, request
from app_front.blueprints.stock.forms import (
    OrderInCreateForm,
    OrderInLineForm,
    ReceiveReturnLineForm,
)
from app_front.blueprints.stock.utils import (
    get_supplier_orders,
    get_order_by_id,
    create_order_in_db,
    edit_return_order_in_line_db,
    cancel_supplier_order,
    confirm_supplier_order,
    receive_return_order_line,
)
from db_models.objects import OrderInLinePrice

bp_stock_htmx_return = Blueprint(
    "stock_htmx_return",
    __name__,
    url_prefix="/stock/htmx/returns",
    template_folder="htmx_templates/stock",
)

EDIT_TABLE = "htmx_templates/stock/orders/sections/view.html"
NEW_LINE = "htmx_templates/stock/returns/fragments/new_line.html"
RECEIVE_LINE = "htmx_templates/stock/returns/fragments/receive_line.html"
SECTION_NEW = "htmx_templates/stock/returns/sections/new.html"
SECTION_HOME = "htmx_templates/stock/returns/sections/home.html"
SECTION_CANCELLED = "htmx_templates/stock/orders/sections/cancelled.html"
SECTION_CONFIRMED = "htmx_templates/stock/orders/sections/confirmed.html"

CTX = {"is_return": True}


@bp_stock_htmx_return.get("/cleared")
def cleared():
    """Retourne une section vide pour réinitialiser l'affichage (HTMX)."""
    return ""


@bp_stock_htmx_return.get("/")
def returns():
    """Retourne la section complète de gestion des retours fournisseurs (HTMX)."""
    returns_list = get_supplier_orders(out=True)
    return render_template(SECTION_HOME, returns=returns_list)


@bp_stock_htmx_return.route("/section/create", methods=["GET", "POST"])
def new_return_section():
    """Formulaire de création d'un nouveau retour fournisseur (HTMX)."""
    form = OrderInCreateForm()
    if form.validate_on_submit():
        return_id = create_order_in_db(form, out=True)
        if not return_id:
            raise ValueError("Échec de la création du retour fournisseur")
        order = get_order_by_id(return_id)
        return render_template(EDIT_TABLE, view_state="new", order=order, **CTX)
    if request.method == "POST":
        raise ValueError("Formulaire de création de retour invalide")
    return render_template(SECTION_NEW, form=form, **CTX)


@bp_stock_htmx_return.get("/<int:order_id>/section/edit")
def edit_return(order_id: int):
    """Retourne la section complète d'un retour fournisseur existant (HTMX)."""
    order = get_order_by_id(order_id)
    return render_template(EDIT_TABLE, id_order=order_id, order=order, view_state="edit", **CTX)


@bp_stock_htmx_return.get("/view/<int:order_id>")
def view_return(order_id: int):
    """Retourne la vue détaillée d'un retour fournisseur (HTMX)."""
    order = get_order_by_id(order_id)
    modal = request.args.get("modal", "")
    return render_template(EDIT_TABLE, order=order, view_state="view", modal=modal, **CTX)


@bp_stock_htmx_return.route("/cancel/<int:order_id>", methods=["GET", "POST"])
def cancel_return(order_id: int):
    """Annule un retour fournisseur (HTMX)."""
    if request.method == "POST":
        cancel_supplier_order(order_id, out=True)
        return render_template(
            SECTION_CANCELLED,
            order_id=order_id,
            deleted=True,
            mod="return",
            **CTX,
        )
    return render_template(
        SECTION_CANCELLED,
        order_id=order_id,
        deleted=False,
        mod="return",
        **CTX,
    )


@bp_stock_htmx_return.route("/<int:order_id>/line/create", methods=["GET", "POST"])
def new_return_line(order_id: int):
    """Formulaire d'ajout d'une ligne de retour fournisseur (HTMX)."""
    form = OrderInLineForm()
    form.order_id.data = str(order_id)
    if form.validate_on_submit():
        edit_return_order_in_line_db(form, action="create", order_id=order_id)
        order = get_order_by_id(order_id)
        return render_template(EDIT_TABLE, order=order, form=form, view_state="new", **CTX)
    order = get_order_by_id(order_id)
    return render_template(NEW_LINE, form=form, order=order, view_state="create", **CTX)


@bp_stock_htmx_return.route(
    "/<int:order_id>/line/<int:line_id>/<action>", methods=["GET", "POST"]
)
def edit_return_line(order_id: int, line_id: int, action: str):
    """Retourne le formulaire d'édition d'une ligne de retour fournisseur (HTMX)."""
    form = OrderInLineForm()

    if request.method == "POST":
        if action == "delete":
            edit_return_order_in_line_db(
                form, action=action, line_id=line_id, order_id=order_id
            )
            return render_template(SECTION_CANCELLED, deleted=True, line_id=line_id, **CTX)

        edit_return_order_in_line_db(form, action=action, line_id=line_id, order_id=order_id)
        order = get_order_by_id(order_id)
        line = next((l for l in order.orderin_lines if l.id == line_id), None)
        if not line:
            raise ValueError(
                f"Ligne {line_id} introuvable dans le retour {order_id}"
            )
        return render_template(
            EDIT_TABLE,
            order=order,
            line=line,
            form=form,
            view_state="edit",
            **CTX,
        )

    if action == "delete":
        return render_template(SECTION_CANCELLED, line_id=line_id, **CTX)

    order = get_order_by_id(order_id)
    line = next((l for l in order.orderin_lines if l.id == line_id), None)
    if not line:
        raise ValueError(f"Ligne {line_id} introuvable dans le retour {order_id}")

    form.line_to_form(line)
    return render_template(NEW_LINE, form=form, line=line, view_state="edit", **CTX)


@bp_stock_htmx_return.post("/<int:order_id>/confirm")
def confirm_return(order_id: int):
    """Confirme un retour fournisseur (draft → sended) (HTMX)."""
    confirm_supplier_order(order_id)
    order = get_order_by_id(order_id)
    return render_template(SECTION_CONFIRMED, order=order, **CTX)


@bp_stock_htmx_return.get("/<int:order_id>/receipt")
def receipt_return(order_id: int):
    """Retourne la vue de réception d'un retour fournisseur (HTMX)."""
    order = get_order_by_id(order_id)
    return render_template(EDIT_TABLE, order=order, view_state="receipt", **CTX)


@bp_stock_htmx_return.route(
    "/<int:order_id>/line/<int:line_id>/receive", methods=["GET", "POST"]
)
def receive_return_line_route(order_id: int, line_id: int):
    """Affiche et traite le formulaire de réception d'une ligne de retour (HTMX)."""
    form = ReceiveReturnLineForm()
    order = get_order_by_id(order_id)
    line = next((ln for ln in order.orderin_lines if ln.id == line_id), None)
    if not line:
        raise ValueError(f"Ligne {line_id} introuvable dans le retour {order_id}")

    if request.method == "POST" and form.validate_on_submit():
        qty_r, qty_c = form.validate_receive_data(line.qty_ordered)
        prices = [
            OrderInLinePrice(
                unit_price=entry.form.unit_price.data,
                vat_rate=entry.form.vat_rate.data,
                position=position,
            )
            for position, entry in enumerate(form.prices)
        ]
        receive_return_order_line(line_id, qty_r, qty_c, prices)
        order = get_order_by_id(order_id)
        return render_template(EDIT_TABLE, order=order, view_state="receipt", **CTX)

    form.line_id.data = str(line_id)
    form.order_id.data = str(order_id)
    form.qty_received.data = str(line.qty_ordered)
    form.qty_cancelled.data = "0"
    # Pré-remplir les prix avec ceux de la ligne
    while len(form.prices) > 0:
        form.prices.pop_entry()
    for position, price in enumerate(line.prices):
        form.prices.append_entry({
            "unit_price": float(price.unit_price),
            "vat_rate": float(price.vat_rate),
        })
    return render_template(RECEIVE_LINE, form=form, line=line, order=order, **CTX)
