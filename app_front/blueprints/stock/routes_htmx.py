"""Blueprint API HTMX pour le module stock."""

from flask import Blueprint, render_template
from app_front.blueprints.stock.forms import (
    OrderInCreateForm,
    OrderInLineForm,
)
from app_front.blueprints.stock.utils import (
    get_supplier_orders,
    get_supplier_returns,
    get_order_by_id,
    get_return_by_id,
    cancel_supplier_order,
    create_order_in_db,
    create_order_in_line_db,
)

bp_stock_htmx = Blueprint(
    "stock_htmx",
    __name__,
    url_prefix="/stock/htmx",
    template_folder="htmx_templates/stock",
)

NEW_TABLE = "htmx_templates/stock/orders/fragments/new_table.html"
NEW_LINE = "htmx_templates/stock/orders/fragments/new_line.html"
SECTION_NEW = "htmx_templates/stock/orders/sections/new.html"
SECTION_HOME = "htmx_templates/stock/orders/sections/home.html"


@bp_stock_htmx.get("/cleared")
def cleared():
    """ Retourne une section vide pour réinitialiser l'affichage (HTMX). """
    return ""


@bp_stock_htmx.get("/orders")
def orders():
    """Retourne la section complète de gestion des commandes fournisseurs (HTMX)."""
    orders_list = get_supplier_orders()
    return render_template(SECTION_HOME, orders=orders_list)


@bp_stock_htmx.get("/returns")
def returns():
    """Retourne la section complète de gestion des retours fournisseurs (HTMX)."""
    returns_list = get_supplier_returns()
    return render_template(SECTION_HOME, returns=returns_list)


@bp_stock_htmx.route("/orders/section/create", methods=["GET", "POST"])
def new_order_section():
    """Retourne la section complète pour la création d'une nouvelle commande fournisseur (HTMX)."""
    form = OrderInCreateForm()
    if form.validate_on_submit():
        id_order = create_order_in_db(form)
        if not id_order:
            raise ValueError("Failed to create order in database")
        supplier_name = form.supplier_name.data
        return render_template(NEW_TABLE, id_order=id_order, supplier_name=supplier_name)
    return render_template(SECTION_NEW, form=form)


@bp_stock_htmx.post("/orders/<int:order_id>/section/create")
def order_section(order_id: int):
    """Retourne la section complète d'une commande fournisseur existante (HTMX)."""
    order = get_order_by_id(order_id)
    supplier_name = order.supplier.name
    order_lines = order.lines
    return render_template(
        NEW_TABLE,
        id_order=order_id,
        supplier_name=supplier_name,
        order_lines=order_lines
        )


@bp_stock_htmx.route("/orders/<int:order_id>/line/create", methods=["GET", "POST"])
def new_order_line_form(order_id: int):
    """Retourne le formulaire de création d'une ligne de commande fournisseur (HTMX)."""
    form = OrderInLineForm()
    form.order_id.data = str(order_id)
    if form.validate_on_submit():
        id_line = create_order_in_line_db(form)
        if not id_line:
            raise ValueError("Failed to create order line in database")
        order = get_order_by_id(order_id)
        supplier_name = order.supplier.name
        order_lines = order.lines
        return render_template(
            NEW_TABLE,
            id_order=order_id,
            supplier_name=supplier_name,
            order_lines=order_lines,
            form=form
            )
    return render_template(NEW_LINE, form=form)


@bp_stock_htmx.get("/orders/view/<int:order_id>")
def view_order(order_id: int):
    """Retourne la vue détaillée d'une commande fournisseur (HTMX)."""
    # Récupérer les détails de la commande à partir de l'ID
    order = get_order_by_id(order_id)
    return render_template("htmx_templates/stock/orders/sections/view.html", order=order)


@bp_stock_htmx.post("/orders/cancel/<int:order_id>")
def cancel_order(order_id: int):
    """Annule une commande fournisseur (HTMX)."""
    cancel_supplier_order(order_id)
    return render_template("htmx_templates/stock/orders/fragments/canceled.html")


@bp_stock_htmx.get("/returns/section/create")
def new_return_section():
    """Retourne la section complète pour la création d'un nouveau retour fournisseur (HTMX)."""
    form = OrderInCreateForm()
    template_path = "htmx_templates/stock/returns/sections/new.html"
    return render_template(template_path, form=form)


@bp_stock_htmx.get("/returns/view/<int:return_id>")
def view_return(return_id: int):
    """Retourne la vue détaillée d'un retour fournisseur (HTMX)."""
    # Récupérer les détails du retour à partir de l'ID
    return_info = get_return_by_id(return_id)
    return render_template("htmx_templates/stock/returns/sections/view.html",
                           return_info=return_info)


@bp_stock_htmx.post("/returns/table/create")
def new_return_table():
    """Retourne une ligne de tableau pour une nouvelle ligne de retour fournisseur (HTMX)."""
    return render_template("htmx_templates/stock/returns/fragments/new_table.html")


@bp_stock_htmx.route("/returns/line/create", methods=["GET", "POST"])
def new_return_line_form():
    """Retourne le formulaire de création d'une ligne de retour fournisseur (HTMX)."""
    return render_template("htmx_templates/stock/returns/fragments/new_line.html")
