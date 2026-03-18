"""Blueprint API HTMX pour le module stock."""

from flask import Blueprint, render_template
from app_front.blueprints.stock.forms import (
    OrderInCreateForm,
)
from app_front.blueprints.stock.utils import (
    get_supplier_returns,
    get_return_by_id,
)

bp_stock_htmx_return = Blueprint(
    "stock_htmx_return",
    __name__,
    url_prefix="/stock/htmx/returns",
    template_folder="htmx_templates/stock",
)

NEW_LINE = "htmx_templates/stock/orders/fragments/new_line.html"
SECTION_HOME = "htmx_templates/stock/orders/sections/home.html"


@bp_stock_htmx_return.get("/cleared")
def cleared():
    """Retourne une section vide pour réinitialiser l'affichage (HTMX)."""
    return ""


@bp_stock_htmx_return.get("/")
def returns():
    """Retourne la section complète de gestion des retours fournisseurs (HTMX)."""
    returns_list = get_supplier_returns()
    return render_template(SECTION_HOME, returns=returns_list)


@bp_stock_htmx_return.get("/returns/section/create")
def new_return_section():
    """Retourne la section complète pour la création d'un nouveau retour fournisseur (HTMX)."""
    form = OrderInCreateForm()
    template_path = "htmx_templates/stock/returns/sections/new.html"
    return render_template(template_path, form=form)


@bp_stock_htmx_return.get("/returns/view/<int:return_id>")
def view_return(return_id: int):
    """Retourne la vue détaillée d'un retour fournisseur (HTMX)."""
    # Récupérer les détails du retour à partir de l'ID
    return_info = get_return_by_id(return_id)
    return render_template(
        "htmx_templates/stock/returns/sections/view.html", return_info=return_info
    )


@bp_stock_htmx_return.post("/returns/table/create")
def new_return_table():
    """Retourne une ligne de tableau pour une nouvelle ligne de retour fournisseur (HTMX)."""
    return render_template("htmx_templates/stock/returns/fragments/new_table.html")


@bp_stock_htmx_return.route("/returns/line/create", methods=["GET", "POST"])
def new_return_line_form():
    """Retourne le formulaire de création d'une ligne de retour fournisseur (HTMX)."""
    return render_template(NEW_LINE)
