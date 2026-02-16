"""Blueprint pour les fonctionnalités du tableau de bord"""

from flask import Blueprint

bp_dashboard = Blueprint("dashboard", __name__, url_prefix="/dashboard")
