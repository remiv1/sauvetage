"""Blueprint pour les fonctionnalités des commandes"""

from flask import Blueprint, render_template_string

bp_order = Blueprint("order", __name__, url_prefix="/order")


@bp_order.route("/")
def index():
    """Page d'accueil du module commandes"""
    return render_template_string("""
    <h1>Commandes</h1>
    <p>Module en développement</p>
    """)
