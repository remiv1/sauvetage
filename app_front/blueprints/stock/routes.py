"""Blueprint pour les fonctionnalités de gestion des stocks"""

from flask import Blueprint, render_template_string
from app_front.utils.pages import render_page

bp_stock = Blueprint("stock", __name__, url_prefix="/stock")

@bp_stock.route("/")
def index():
    """Page d'accueil du module stocks"""
    # TODO: remplacer par un appel réel pour détecter les articles à prix zéro
    has_zero_price_items = False
    return render_page("stock_index", has_zero_price_items=has_zero_price_items)

@bp_stock.route("/council")
def council():
    """Page de gestion du conseil de stock"""
    return render_template_string("""
    <h1>Conseil de stock</h1>
    <p>Module en développement</p>
    """)

@bp_stock.route("/orders")
def orders():
    """Page de gestion des commandes entrantes"""
    return render_template_string("""
    <h1>Commandes entrantes</h1>
    <p>Module en développement</p>
    """)

@bp_stock.route("/reservations")
def reservations():
    """Page de gestion des réservations de stocks"""
    return render_template_string("""
    <h1>Réservations de stocks</h1>
    <p>Module en développement</p>
    """)

@bp_stock.route("/search")
def search():
    """Page de recherche de stocks"""
    return render_template_string("""
    <h1>Recherche de stocks</h1>
    <p>Module en développement</p>
    """)
