"""Blueprint API HTMX pour le module stock."""

from flask import Blueprint, render_template
from app_front.blueprints.stock.forms import OrderInCreateForm
from app_front.blueprints.stock.utils import (
    get_supplier_orders,
    get_supplier_returns,
    get_order_by_id,
    get_return_by_id,
)

bp_stock_htmx = Blueprint(
    "stock_htmx",
    __name__,
    url_prefix="/stock/htmx",
    template_folder="htmx_templates/stock",
)


@bp_stock_htmx.get("/orders")
def orders():
    """Retourne la section complète de gestion des commandes fournisseurs (HTMX)."""
    orders_list = get_supplier_orders()
    return render_template("htmx_templates/stock/orders/sections/home.html",
                           orders=orders_list)


@bp_stock_htmx.get("/returns")
def returns():
    """Retourne la section complète de gestion des retours fournisseurs (HTMX)."""
    returns_list = get_supplier_returns()
    return render_template("htmx_templates/stock/returns/sections/home.html",
                           returns=returns_list)


@bp_stock_htmx.get("/orders/section/create")
def new_order_section():
    """Retourne la section complète pour la création d'une nouvelle commande fournisseur (HTMX)."""
    form = OrderInCreateForm()
    template_path = "htmx_templates/stock/orders/sections/new.html"
    return render_template(template_path, form=form)


@bp_stock_htmx.get("/orders/view/<int:order_id>")
def view_order(order_id: int):
    """Retourne la vue détaillée d'une commande fournisseur (HTMX)."""
    # Récupérer les détails de la commande à partir de l'ID
    order = get_order_by_id(order_id)
    return render_template("htmx_templates/stock/orders/sections/view.html", order=order)


@bp_stock_htmx.get("/orders/create")
def new_order_form():
    """Retourne le formulaire de création d'une nouvelle commande fournisseur (HTMX)."""
    form = OrderInCreateForm()
    template_path = "htmx_templates/stock/orders/fragments/new_order.html"
    return render_template(template_path, form=form)


@bp_stock_htmx.get("/orders/table/create")
def new_order_table():
    """Retourne une ligne de tableau pour une nouvelle ligne de commande fournisseur (HTMX)."""
    return render_template("htmx_templates/stock/orders/fragments/new_table.html")


@bp_stock_htmx.get("/orders/line/create")
def new_order_line_form():
    """Retourne le formulaire de création d'une ligne de commande fournisseur (HTMX)."""
    return render_template("htmx_templates/stock/orders/fragments/new_line.html")


@bp_stock_htmx.get("/returns/view/<int:return_id>")
def view_return(return_id: int):
    """Retourne la vue détaillée d'un retour fournisseur (HTMX)."""
    # Récupérer les détails du retour à partir de l'ID
    return_info = get_return_by_id(return_id)
    return render_template("htmx_templates/stock/returns/sections/view.html",
                           return_info=return_info)


@bp_stock_htmx.get("/returns/section")
def new_return_section():
    """Retourne la section complète pour la création d'un nouveau retour fournisseur (HTMX)."""
    form = OrderInCreateForm()
    template_path = "htmx_templates/stock/returns/sections/new.html"
    return render_template(template_path, form=form)


@bp_stock_htmx.get("/returns/create")
def new_return_form():
    """Retourne le formulaire de création d'un nouveau retour fournisseur (HTMX)."""
    return render_template("htmx_templates/stock/returns/fragments/new_return.html")


@bp_stock_htmx.get("/returns/table/create")
def new_return_table():
    """Retourne une ligne de tableau pour une nouvelle ligne de retour fournisseur (HTMX)."""
    return render_template("htmx_templates/stock/returns/fragments/new_table.html")


@bp_stock_htmx.get("/returns/line/create")
def new_return_line_form():
    """Retourne le formulaire de création d'une ligne de retour fournisseur (HTMX)."""
    return render_template("htmx_templates/stock/returns/fragments/new_line.html")
