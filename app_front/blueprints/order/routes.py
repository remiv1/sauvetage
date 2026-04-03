"""Blueprint pour les fonctionnalités des commandes clients"""

from flask import Blueprint
from app_front.utils.pages import render_page

bp_order = Blueprint("order", __name__, url_prefix="/order")


@bp_order.get("/")
def index():
    """Page de gestion des commandes avec liste paginée et filtres."""
    return render_page("order_index")
