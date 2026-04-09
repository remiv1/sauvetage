"""Blueprint API HTMX pour le module stock."""

from flask import Blueprint, render_template, request
from app_front.blueprints.stock.forms import (
    OrderInCreateForm,
    OrderInLineForm,
    ReceiveLineForm,
    ExternalRefForm,
)
from app_front.blueprints.stock.utils import (
    get_supplier_orders,
    get_order_by_id,
    cancel_supplier_order,
    create_order_in_db,
    edit_order_in_line_db,
    confirm_supplier_order,
    receive_order_line,
    update_order_external_ref,
)

bp_stock_htmx_orders = Blueprint(
    "stock_htmx_orders",
    __name__,
    url_prefix="/stock/htmx/orders",
    template_folder="htmx_templates/stock",
)

EDIT_TABLE = "htmx_templates/stock/orders/sections/view.html"
NEW_LINE = "htmx_templates/stock/orders/fragments/new_line.html"
RECEIVE_LINE = "htmx_templates/stock/orders/fragments/receive_line.html"
SECTION_NEW = "htmx_templates/stock/orders/sections/new.html"
SECTION_HOME = "htmx_templates/stock/orders/sections/home.html"
SECTION_CANCELED = "htmx_templates/stock/orders/sections/canceled.html"
SECTION_CONFIRMED = "htmx_templates/stock/orders/sections/confirmed.html"
UNKNOWN_OBJECT = "<p>Objet introuvable.</p>"


@bp_stock_htmx_orders.get("/cleared")
def cleared():
    """Retourne une section vide pour réinitialiser l'affichage (HTMX)."""
    return ""


@bp_stock_htmx_orders.get("/")
def orders():
    """Retourne la section complète de gestion des commandes fournisseurs (HTMX)."""
    orders_list = get_supplier_orders()
    return render_template(SECTION_HOME, orders=orders_list)


@bp_stock_htmx_orders.route("/section/create", methods=["GET", "POST"])
def new_order_section():
    """Retourne la section complète pour la création d'une nouvelle commande fournisseur (HTMX)."""
    form = OrderInCreateForm()
    if form.validate_on_submit():
        id_order = create_order_in_db(form)
        if not id_order:
            raise ValueError("Failed to create order in database")
        order = get_order_by_id(id_order)
        return render_template(
            EDIT_TABLE, view_state="new", order=order, ext_ref_form=ExternalRefForm()
            )
    return render_template(SECTION_NEW, form=form)


@bp_stock_htmx_orders.get("/<int:order_id>/section/edit")
def edit_order(order_id: int):
    """Retourne la section complète d'une commande fournisseur existante (HTMX)."""
    order = get_order_by_id(order_id)
    return render_template(
        EDIT_TABLE, id_order=order_id, order=order,
        view_state="edit"
    )


@bp_stock_htmx_orders.get("/view/<int:order_id>")
def view_order(order_id: int):
    """Retourne la vue détaillée d'une commande fournisseur (HTMX)."""
    # Récupérer les détails de la commande à partir de l'ID
    order = get_order_by_id(order_id)
    modal = request.args.get("modal", "")
    return render_template(EDIT_TABLE, order=order, view_state="view", modal=modal)


@bp_stock_htmx_orders.route("/cancel/<int:order_id>", methods=["GET", "POST"])
def cancel_order(order_id: int):
    """Annule une commande fournisseur (HTMX)."""
    if request.method == "POST":
        cancel_supplier_order(order_id)
        return render_template(SECTION_CANCELED, order_id=order_id, deleted=True, mod="order")
    return render_template(SECTION_CANCELED, order_id=order_id, deleted=False, mod="order")


@bp_stock_htmx_orders.route("/<int:order_id>/line/create", methods=["GET", "POST"])
def new_order_line(order_id: int):
    """Retourne le formulaire de création d'une ligne de commande fournisseur (HTMX)."""
    form = OrderInLineForm()
    form.order_id.data = str(order_id)
    if form.validate_on_submit():
        id_line = edit_order_in_line_db(form, action="create", order_id=order_id)
        if not id_line:
            raise ValueError("Failed to create order line in database")
        order = get_order_by_id(order_id)
        return render_template(
            EDIT_TABLE, order=order, form=form,
            view_state="new"
            )
    return render_template(NEW_LINE, form=form, view_state="create")


@bp_stock_htmx_orders.route(
    "/<int:order_id>/line/<int:line_id>/<action>", methods=["GET", "POST"]
)
def edit_order_line(order_id: int, line_id: int, action: str):
    """Retourne le formulaire d'édition d'une ligne de commande fournisseur (HTMX)."""
    # Récupération du formulaire
    form = OrderInLineForm()

    # Gestion de la méthode POST pour les actions d'édition ou de suppression
    if request.method == "POST":

        # If deletion was requested, return the canceled fragment indicating success
        if action == "delete":
            line_id = edit_order_in_line_db(form, action=action, line_id=line_id, order_id=order_id)
            return render_template(SECTION_CANCELED, deleted=True, line_id=line_id)

        # Gestion de l'action d'édition
        edit_order_in_line_db(form, action=action, line_id=line_id, order_id=order_id)

        # For create/edit, show the updated order section
        order = get_order_by_id(order_id)
        line = next((l for l in order.orderin_lines if l.id == line_id), None)
        if not line:
            raise ValueError(f"Line with ID {line_id} not found in order {order_id}")
        return render_template(
            EDIT_TABLE, order=order, line=line, form=form,
            view_state="edit"
        )

    # Gestion de la méthode GET pour l'action de suppression
    if action == "delete":
        return render_template(SECTION_CANCELED, line_id=line_id)

    # Gestion de la méthode GET pour l'action d'édition
    order = get_order_by_id(order_id)
    line = next((l for l in order.orderin_lines if l.id == line_id), None)
    if not line:
        raise ValueError(f"Line with ID {line_id} not found in order {order_id}")

    # Remplissage du formulaire avec les données de la ligne existante
    form.line_to_form(line)

    return render_template(NEW_LINE, form=form, line=line, view_state="edit")


@bp_stock_htmx_orders.post("/<int:order_id>/confirm")
def confirm_order(order_id: int):
    """Confirme une commande fournisseur (draft → sended) et affiche la modale de succès (HTMX)."""
    confirm_supplier_order(order_id)
    order = get_order_by_id(order_id)
    return render_template(SECTION_CONFIRMED, order=order)


@bp_stock_htmx_orders.get("/<int:order_id>/receipt")
def receipt_order(order_id: int):
    """Retourne la vue de réception d'une commande fournisseur (HTMX)."""
    order = get_order_by_id(order_id)
    ext_ref_form = ExternalRefForm()
    return render_template(EDIT_TABLE, order=order, view_state="receipt", ext_ref_form=ext_ref_form)


@bp_stock_htmx_orders.route(
    "/<int:order_id>/line/<int:line_id>/receive", methods=["GET", "POST"]
)
def receive_order_line_route(order_id: int, line_id: int):
    """Affiche et traite le formulaire de réception d'une ligne de commande (HTMX)."""
    form = ReceiveLineForm()
    order = get_order_by_id(order_id)
    line = next((ln for ln in order.orderin_lines if ln.id == line_id), None)
    if not line:
        raise ValueError(f"Ligne {line_id} introuvable dans la commande {order_id}")

    if request.method == "POST" and form.validate_on_submit():
        qty_r, qty_c = form.validate_receive_data(line.qty_ordered)
        receive_order_line(line_id, qty_r, qty_c)
        # Recharger la commande après réception pour afficher l'état à jour
        order = get_order_by_id(order_id)
        return render_template(EDIT_TABLE, order=order, view_state="receipt")

    # Pré-remplir le formulaire
    form.line_id.data = str(line_id)
    form.order_id.data = str(order_id)
    form.qty_received.data = str(line.qty_ordered)
    form.qty_cancelled.data = "0"
    return render_template(RECEIVE_LINE, form=form, line=line, order=order)


@bp_stock_htmx_orders.route("/<int:order_id>/external-ref", methods=["POST"])
def update_external_ref(order_id: int):
    """Met à jour la référence externe d'une commande fournisseur (HTMX)."""
    form = ExternalRefForm()
    if form.validate_on_submit():
        update_order_external_ref(order_id, form.external_ref.data or "")
    order = get_order_by_id(order_id)
    return render_template(
        EDIT_TABLE, order=order, view_state="receipt", ext_ref_form=ExternalRefForm()
        )
