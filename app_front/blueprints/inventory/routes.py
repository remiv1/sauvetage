"""Blueprint pour les fonctionnalités de l'inventaire"""

from flask import Blueprint, render_template_string

bp_inventory = Blueprint("inventory", __name__, url_prefix="/inventory")

@bp_inventory.route("/")
def index():
    """Page d'accueil du module inventaire"""
    return render_template_string("""
    <h1>Inventaire</h1>
    <p>Module en développement</p>
    """)
