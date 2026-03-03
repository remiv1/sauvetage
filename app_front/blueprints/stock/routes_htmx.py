"""Blueprint API HTMX pour le module stock."""

from flask import Blueprint, render_template

bp_stock_htmx = Blueprint("stock_htmx",
                          __name__,
                          url_prefix="/stock/htmx",
                          template_folder="htmx_templates/stock")

@bp_stock_htmx.get("/orders/create")
def new_order_form():
    """Retourne le formulaire de création d'une nouvelle commande fournisseur (HTMX)."""
    return render_template("htmx_templates/stock/new_order.html")

@bp_stock_htmx.get("/orders/table/create")
def new_order_table():
    """Retourne une ligne de tableau pour une nouvelle ligne de commande fournisseur (HTMX)."""
    return render_template("htmx_templates/stock/new_order_table.html")

@bp_stock_htmx.get("/orders/line/create")
def new_order_line_form():
    """Retourne le formulaire de création d'une ligne de commande fournisseur (HTMX)."""
    return render_template("htmx_templates/stock/new_order_line.html")

@bp_stock_htmx.get("/returns/create")
def new_return_form():
    """Retourne le formulaire de création d'un nouveau retour fournisseur (HTMX)."""
    return render_template("htmx_templates/stock/new_return.html")

@bp_stock_htmx.get("/returns/table/create")
def new_return_table():
    """Retourne une ligne de tableau pour une nouvelle ligne de retour fournisseur (HTMX)."""
    return render_template("htmx_templates/stock/new_return_table.html")

@bp_stock_htmx.get("/returns/line/create")
def new_return_line_form():
    """Retourne le formulaire de création d'une ligne de retour fournisseur (HTMX)."""
    return render_template("htmx_templates/stock/new_return_line.html")
