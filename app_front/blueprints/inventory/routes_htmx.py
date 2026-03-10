"""Blueprint HTMX pour le workflow d'inventaire."""

from flask import Blueprint, render_template


bp_inventory_htmx = Blueprint("inventory_htmx", __name__, url_prefix="/inventory/htmx")


@bp_inventory_htmx.get("/objects/get")
def get_items_search():
    """Retourne la section de recherche d'informations sur les objets (HTMX)."""
    page_path = "htmx_templates/inventory/objects/fragments/dropdown.html"
    return render_template(page_path)
