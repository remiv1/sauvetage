"""Blueprint pour les fonctionnalités des fournisseurs"""

from flask import Blueprint
from app_front.utils.pages import render_page

bp_supplier = Blueprint("supplier", __name__, url_prefix="/supplier")


@bp_supplier.get("/")
def index():
    """Page de gestion des fournisseurs avec liste paginée et filtres."""
    return render_page("supplier")
