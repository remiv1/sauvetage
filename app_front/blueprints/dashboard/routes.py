"""Blueprint pour les fonctionnalités du tableau de bord"""

from flask import Blueprint
from app_front.utils.pages import render_page

bp_dashboard = Blueprint("dashboard", __name__, url_prefix="/dashboard")

@bp_dashboard.route("/")
def index():
    """Affiche la page d'accueil du tableau de bord"""
    return render_page("dashboard")
