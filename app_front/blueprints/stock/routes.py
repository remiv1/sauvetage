"""Blueprint pour les fonctionnalités de gestion des stocks"""

from flask import Blueprint
from app_front.utils.pages import render_page

bp_stock = Blueprint("stock", __name__, url_prefix="/stock")

@bp_stock.route("/")
def index():
    """Page d'accueil du module stocks"""
    has_zero_price_items = False
    return render_page("stock_index", has_zero_price_items=has_zero_price_items)

@bp_stock.route("/council")
def council():
    """Page de gestion du conseil de stock"""
    return render_page("stock_council")

@bp_stock.route("/orders")
def orders():
    """Page de gestion des commandes entrantes"""
    return render_page("stock_order")

@bp_stock.route("/reservations")
def reservations():
    """Page de gestion des réservations de stocks"""
    return render_page("stock_reservations")

@bp_stock.route("/search")
def search():
    """Page de recherche de stocks"""
    return render_page("stock_search")
