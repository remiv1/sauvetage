"""Blueprint pour les fonctionnalités des clients.

Routes (templates) :
    - /customer/create : Formulaire de création d'un client.
    - /customer/<int:customer_id> : Affichage de la fiche client.
"""

from flask import Blueprint, redirect, url_for, flash, request, make_response, session
from app_front.blueprints.customer.forms import CustomerMainForm
from app_front.utils.pages import render_page
from app_front.blueprints.customer.utils.users import (
    form_to_dict,
    create_from_dict,
    get_customer,
    push_customer_partners,
)
from app_front.utils.decorators import permission_required, COMMERCIAL, COMPTA, DIRECTION
from app_front.utils.request_meta import get_client_ip, get_request_log_metadata
from logs.log_actions import log_client_event

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
        log_client_event(
            client_id=str(customer_id),
            event="create",
            user_id=session.get("username"),
            ip_address=get_client_ip(request),
            status_code=200,
            obj_metadata=get_request_log_metadata(request),
        )
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


@bp_customer.post("/<int:customer_id>/partners-push")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def customer_partners_push(customer_id: int):
    """Pousse un client vers WooCommerce et Henrri dans la même opération."""
    success, error_message = push_customer_partners(customer_id)
    status_code = 204 if success else 500
    log_payload = get_request_log_metadata(request) or {}
    if error_message:
        log_payload["error"] = error_message
    log_client_event(
        client_id=str(customer_id),
        event="partners_push",
        user_id=session.get("username"),
        ip_address=get_client_ip(request),
        status_code=status_code,
        obj_metadata=log_payload,
    )
    if not success:
        return make_response(
            error_message or "Erreur de synchronisation vers les partenaires",
            status_code
        )
    response = make_response("", status_code)
    response.headers["HX-Redirect"] = url_for("customer.view", customer_id=customer_id)
    return response
