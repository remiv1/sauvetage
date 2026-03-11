"""Blueprint HTMX pour le workflow d'inventaire."""

from flask import Blueprint, render_template, request
from app_front.blueprints.inventory.utils import search_object_by_name

bp_inventory_htmx = Blueprint("inventory_htmx", __name__, url_prefix="/inventory/htmx")


DROPDOWN_TEMPLATE = "htmx_templates/inventory/objects/fragments/dropdown.html"
SELECTED_OBJECT_TEMPLATE = "htmx_templates/inventory/objects/fragments/selected_object.html"


@bp_inventory_htmx.get("/objects/get")
def get_items_search():
    """Retourne la section de recherche d'informations sur les objets (HTMX)."""
    name = request.form.get("object-wrapper", "")
    object_list = search_object_by_name(name)
    return render_template(DROPDOWN_TEMPLATE, items=object_list)


@bp_inventory_htmx.post("objects/select")
def select_object():
    """Retourne les informations d'un objet sélectionné (HTMX)."""
    object_id = request.form.get("object_id")
    object_name = request.form.get("object_name")
    return render_template(
        SELECTED_OBJECT_TEMPLATE,
        object_id=object_id,
        object_name=object_name,
    )
