"""Blueprint pour les fonctionnalités de gestion des stocks"""

from flask import Blueprint, render_template_string
from app_front.utils.pages import render_page
from app_front.blueprints.stock.utils import (
    is_zero_price_items, get_zero_price_items
)

bp_stock = Blueprint("stock", __name__, url_prefix="/stock")

@bp_stock.route("/", methods=["GET"])
def index():
    """Page d'accueil du module stocks"""
    has_zero_price_items = is_zero_price_items()
    return render_page("stock_index",
                       has_zero_price_items=has_zero_price_items)

@bp_stock.route("/council", methods=["GET"])
def council():
    """Page de gestion de réconciliation des prix de stocks"""
    items_to_council = get_zero_price_items()
    return render_page("stock_council", items_to_council=items_to_council)

@bp_stock.route("/orders", methods=["GET"])
def orders():
    """Page de gestion des commandes entrantes"""
    return render_template_string("""
    <h1>Commandes entrantes</h1>
    <p>Module en développement</p>
    """)

@bp_stock.route("/reservations", methods=["GET"])
def reservations():
    """Page de gestion des réservations de stocks"""
    return render_template_string("""
    <h1>Réservations de stocks</h1>
    <p>Module en développement</p>
    """)

@bp_stock.route("/search", methods=["GET"])
def search():
    """Page de recherche de stocks"""
    return render_template_string("""
    <h1>Recherche de stocks</h1>
    <p>Module en développement</p>
    """)
