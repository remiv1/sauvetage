"""Blueprint pour les fonctionnalités des fournisseurs"""

from flask import Blueprint, render_template_string

bp_supplier = Blueprint("supplier", __name__, url_prefix="/supplier")


@bp_supplier.route("/")
def index():
    """Page d'accueil du module fournisseurs"""
    return render_template_string("""
    <h1>Fournisseurs</h1>
    <p>Module en développement</p>
    """)
