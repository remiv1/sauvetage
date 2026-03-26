"""Blueprint pour les fonctionnalités des clients.

Routes (templates) :
    - /customer/create : Formulaire de création d'un client.
    - /customer/<int:customer_id> : Affichage de la fiche client.
"""

from flask import Blueprint, redirect, url_for, flash, request
from app_front.blueprints.customer.forms import CustomerMainForm
from app_front.utils.pages import render_page
from app_front.blueprints.customer.utils.users import (
    form_to_dict,
    create_from_dict,
    get_customer,
)
from app_front.utils.decorators import permission_required, COMMERCIAL, COMPTA, DIRECTION

bp_customer = Blueprint("customer", __name__, url_prefix="/customer")


@bp_customer.get("/")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def index():
    """Page d'accueil du module client."""
    return render_page("customer_index")


@bp_customer.get("/search")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def search():
    """Affiche le formulaire de recherche de clients."""
    return render_page("customer_search")


@bp_customer.route("/create", methods=["GET", "POST"])
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def create():
    """Affiche et traite le formulaire de création de client."""
    form = CustomerMainForm()
    if form.validate_on_submit():
        customer_id = create_from_dict(form_to_dict(form))
        flash(f"Client n°{customer_id} créé avec succès.", "success")
        return redirect(url_for("customer.view", customer_id=customer_id))

    if request.method == "POST":
        flash("Formulaire invalide : vérifiez les champs.", "error")
    return render_page("customer_create", form=form)


@bp_customer.get("/<int:customer_id>")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def view(customer_id: int):
    """Affiche la fiche détaillée d'un client."""
    customer = get_customer(customer_id)
    if not customer:
        flash(f"Client n°{customer_id} introuvable.", "error")
        return redirect(url_for("customer.index"))

    return render_page("customer_view", customer=customer)
