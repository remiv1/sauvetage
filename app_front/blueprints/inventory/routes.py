"""Blueprint pour les fonctionnalités de l'inventaire (pages HTML).

Routes :
    GET /inventory/  → Page principale du workflow d'inventaire.
"""

from flask import Blueprint
from app_front.blueprints.inventory.forms import EanInputForm, ProductCreateForm, SupplierCreateForm
from app_front.utils.pages import render_page

bp_inventory = Blueprint("inventory", __name__, url_prefix="/inventory")


@bp_inventory.route("/")
def index():
    """Page principale du workflow d'inventaire."""
    ean_form = EanInputForm()
    product_form = ProductCreateForm()
    supplier_form = SupplierCreateForm()
    return render_page("inventory",
                       ean_form=ean_form,
                       product_form=product_form,
                       supplier_form=supplier_form)
