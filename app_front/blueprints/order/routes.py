"""Blueprint pour les fonctionnalités des commandes clients"""

from flask import Blueprint
from app_front.utils.pages import render_page
from app_front.blueprints.order.utils import get_order_by_id

bp_order = Blueprint("order", __name__, url_prefix="/order")
ORDER_NOT_FOUND = "<p>Commande introuvable.</p>"


@bp_order.get("/")
def index():
    """Page de gestion des commandes avec liste paginée et filtres."""
    return render_page("order_index")

@bp_order.get("/view/<int:order_id>")
def order_view(order_id: int):
    """Page complète de consultation d'une commande."""
    order = get_order_by_id(order_id)
    if order is None:
        return ORDER_NOT_FOUND, 404
    # Redirection vers la page complète (pas une modale)
    return render_page("order_view", order=order)
