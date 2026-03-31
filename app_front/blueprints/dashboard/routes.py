"""Blueprint pour les fonctionnalités du tableau de bord"""

from flask import Blueprint
from app_front.utils.pages import render_page
from app_front.utils.decorators import (
    permission_required, DIRECTION, ADMIN, COMMERCIAL, COMPTA, LOGISTIQUE
)


bp_dashboard = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp_dashboard.get("/")
@permission_required([DIRECTION, ADMIN, COMMERCIAL, COMPTA, LOGISTIQUE], _and=False)
def index():
    """Page principale du tableau de bord."""
    return render_page("dashboard")
