"""Blueprint pour les fonctionnalités de gestion des stocks"""

from flask import Blueprint, render_template_string

bp_stock = Blueprint("stock", __name__, url_prefix="/stock")

@bp_stock.route("/")
def index():
    """Page d'accueil du module stocks"""
    return render_template_string("""
    <h1>Stocks</h1>
    <p>Module en développement</p>
    """)
