"""Blueprint pour les fonctionnalités des clients.

Routes (templates) :
    - /customer/create : Formulaire de création d'un client.
    - /customer/<int:customer_id> : Affichage de la fiche client.
"""

from flask import Blueprint, redirect, url_for, flash
from app_front.blueprints.customer.forms import CustomerMainForm
from app_front.utils.pages import render_page

bp_customer = Blueprint("customer", __name__, url_prefix="/customer")


@bp_customer.route("/create", methods=["GET", "POST"])
def create():
    """Affiche et traite le formulaire de création de client."""
    form = CustomerMainForm()
    if form.validate_on_submit():
        customer_type = form.customer_type.data

        customer_data = {"customer_type": customer_type}

        if customer_type == "part":
            customer_data["part"] = {
                "civil_title": form.civil_title.data,
                "first_name": form.first_name.data,
                "last_name": form.last_name.data,
                "date_of_birth": form.date_of_birth.data,
            }
        else:
            customer_data["pro"] = {
                "company_name": form.company_name.data,
                "siret_number": form.siret_number.data,
                "vat_number": form.vat_number.data,
            }

        # TODO: Envoyer les données au backend API
        # customer_id = create_customer_api(customer_data)
        flash("Client créé avec succès.", "success")
        # TODO: Rediriger vers la fiche client réelle
        # return redirect(url_for("customer.view", customer_id=customer_id))
        return redirect(url_for("customer.view", customer_id=1))

    return render_page("customer_create", form=form)


@bp_customer.route("/<int:customer_id>", methods=["GET"])
def view(customer_id: int):
    """Affiche la fiche détaillée d'un client."""
    # TODO: Récupérer le client depuis le backend API
    # customer = get_customer_api(customer_id)
    customer = {
        "id": customer_id,
        "customer_type": "part",
        "is_active": True,
        "created_at": "2026-02-24T10:00:00",
        "updated_at": "2026-02-24T10:00:00",
        "part": {
            "civil_title": "M.",
            "first_name": "Jean",
            "last_name": "Dupont",
            "date_of_birth": "1990-01-15",
        },
        "pro": None,
        "addresses": [],
        "emails": [],
        "phones": [],
    }

    return render_page("customer_view", customer=customer)
