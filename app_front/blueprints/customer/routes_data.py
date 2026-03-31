"""Blueprint pour les données client (API JSON).

Endpoints :
    - GET    /customer/data/search/fast       : Recherche rapide par nom (autocomplete).
    - GET    /customer/data/search/long       : Recherche avancée multi-critères.
    - GET    /customer/data/<id>              : Récupérer les données complètes d'un client.
    - GET    /customer/data/<id>/addresses    : Récupérer les adresses d'un client.
    - POST   /customer/data/<id>/address      : Ajouter une adresse.
    - PATCH  /customer/data/<id>/address/<addr_id>          : Modifier une adresse.
    - GET    /customer/data/<id>/emails       : Récupérer les emails d'un client.
    - POST   /customer/data/<id>/email        : Ajouter un email.
    - PATCH  /customer/data/<id>/email/<email_id>           : Modifier un email.
    - GET    /customer/data/<id>/phones       : Récupérer les téléphones d'un client.
    - POST   /customer/data/<id>/phone        : Ajouter un téléphone.
    - PATCH  /customer/data/<id>/phone/<phone_id>           : Modifier un téléphone.
    - POST   /customer/data/<id>/activate     : Activer un client.
    - POST   /customer/data/<id>/deactivate   : Désactiver un client.
"""

from flask import Blueprint, jsonify, request
from app_front.blueprints.customer.utils.users import (
    get_customers_by_name,
    multi_search_filter,
    get_customer as util_get_customer,
    update_customer_info,
)
from app_front.blueprints.customer.utils.addresses import (
    get_addresses as util_get_addresses,
    update_address as util_update_address,
    add_address as util_add_address,
)
from app_front.blueprints.customer.utils.emails import (
    get_emails as util_get_emails,
    update_email as util_update_email,
    add_email as util_add_email,
)
from app_front.blueprints.customer.utils.phones import (
    get_phones as util_get_phones,
    update_phone as util_update_phone,
    add_phone as util_add_phone,
)
from app_front.utils.decorators import permission_required, COMMERCIAL, COMPTA, DIRECTION

bp_customer_data = Blueprint("customer_data", __name__, url_prefix="/customer/data")

_NO_DATA_ERROR = "Aucune donnée reçue."
_NO_CUSTOMER_ERROR = "Client non trouvé."


@bp_customer_data.get("/search/fast")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def search_fast():
    """Recherche rapide par nom / raison sociale (autocomplete).

    Query params:
        q (str): Texte libre (min 2 caractères).

    Retourne une liste d'objets :
        {id, display_name, location, customer_type}
    """
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify([])

    customers = get_customers_by_name(query)
    if not customers:
        return jsonify([])

    return jsonify(customers)


@bp_customer_data.get("/search/long")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def search_long():
    """Recherche avancée multi-critères.

    Query params (tous optionnels):
        name          (str): Nom, prénom ou raison sociale.
        customer_type (str): 'part' | 'pro'.
        city          (str): Ville.
        postal_code   (str): Code postal.
        email         (str): Adresse email.
        phone         (str): Numéro de téléphone.

    Retourne une liste d'objets :
        {id, display_name, customer_type, location, email, phone, is_active}
    """
    # Collecte des critères
    name = request.args.get("name", "").strip()
    customer_type = request.args.get("customer_type", "").strip()
    city = request.args.get("city", "").strip()
    postal_code = request.args.get("postal_code", "").strip()
    email = request.args.get("email", "").strip()
    phone = request.args.get("phone", "").strip()

    return jsonify(
        multi_search_filter(name, email, phone, postal_code, city, customer_type)
    )


@bp_customer_data.get("/<int:customer_id>")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def get_customer(customer_id: int):
    """Retourne les données complètes d'un client."""
    customer = util_get_customer(customer_id)
    if not customer:
        raise ValueError(_NO_CUSTOMER_ERROR)
    return jsonify(customer)


@bp_customer_data.patch("/<int:customer_id>/info")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def update_info(customer_id: int):
    """Met à jour les informations principales d'un client (part ou pro).

    Body JSON attendu :
        Pour un particulier : {civil_title, first_name, last_name, date_of_birth}
        Pour un professionnel : {civil_title, company_name, siret_number, vat_number}

    Retourne le client complet mis à jour.
    """
    data = request.get_json()
    if not data:
        raise ValueError(_NO_DATA_ERROR)

    try:
        updated = update_customer_info(customer_id, data)
        if not updated:
            raise ValueError(_NO_CUSTOMER_ERROR)
        return jsonify(updated)
    except ValueError as e:
        raise ValueError(str(e)) from e
    except (KeyError, TypeError, AttributeError) as e:
        raise ValueError("Données invalides ou incomplètes.") from e


@bp_customer_data.get("/<int:customer_id>/addresses")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def get_addresses(customer_id: int):
    """Retourne la liste des adresses d'un client."""
    addresses = util_get_addresses(customer_id)
    if not addresses:
        raise ValueError(_NO_CUSTOMER_ERROR)
    return jsonify(addresses)


@bp_customer_data.post("/<int:customer_id>/address")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def add_address(customer_id: int):
    """
    Ajoute une adresse à un client.
    Body JSON attendu :
    {
        "address_name": "Domicile",
        "address_line1": "123 Rue de Test",
        "address_line2": "Appartement 4B",  # optionnel
        "city": "Testville",
        "state": "Test State",
        "postal_code": "12345",
        "country": "Test Country",
        "is_billing": true,
        "is_shipping": false
    }
    """
    data = request.get_json()
    if not data:
        raise ValueError(_NO_DATA_ERROR)
    new_address = util_add_address(customer_id, data)
    if not new_address:
        raise ValueError(_NO_CUSTOMER_ERROR)
    return jsonify(new_address), 201


@bp_customer_data.patch("/<int:customer_id>/address/<int:address_id>")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def update_address(customer_id: int, address_id: int):
    """
    Met à jour une adresse d'un client.
    Body JSON attendu :
    {
        "address_name": "Domicile",
        "address_line1": "123 Rue de Test",
        "address_line2": "Appartement 4B",  # optionnel
        "city": "Testville",
        "state": "Test State",
        "postal_code": "12345",
        "country": "Test Country",
        "is_billing": true,
        "is_shipping": false
    }
    """
    data = request.get_json()
    if not data:
        raise ValueError(_NO_DATA_ERROR)
    updated = util_update_address(customer_id, address_id, data)
    if not updated:
        raise ValueError("Adresse ou client non trouvé.")
    return jsonify(updated)


@bp_customer_data.get("/<int:customer_id>/emails")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def get_emails(customer_id: int):
    """Retourne la liste des emails d'un client."""
    emails = util_get_emails(customer_id)
    if emails is None:
        raise ValueError(_NO_CUSTOMER_ERROR)
    return jsonify(emails)


@bp_customer_data.post("/<int:customer_id>/email")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def add_email(customer_id: int):
    """
    Ajoute un email à un client.
    Body JSON attendu :
    {
        "email": "test@example.com",
        "is_primary": true
    }
    """
    data = request.get_json()
    if not data:
        raise ValueError(_NO_DATA_ERROR)
    new_email = util_add_email(customer_id, data)
    if not new_email:
        raise ValueError(_NO_CUSTOMER_ERROR)
    return jsonify(new_email), 201


@bp_customer_data.patch("/<int:customer_id>/email/<int:email_id>")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def update_email(customer_id: int, email_id: int):
    """Met à jour un email d'un client."""
    data = request.get_json()
    if not data:
        raise ValueError(_NO_DATA_ERROR)
    updated = util_update_email(customer_id, email_id, data)
    if not updated:
        raise ValueError("Email ou client non trouvé.")
    return jsonify(updated)


@bp_customer_data.get("/<int:customer_id>/phones")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def get_phones(customer_id: int):
    """Retourne la liste des téléphones d'un client."""
    phones = util_get_phones(customer_id)
    if not phones:
        raise ValueError(_NO_CUSTOMER_ERROR)
    return jsonify(phones)


@bp_customer_data.post("/<int:customer_id>/phone")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def add_phone(customer_id: int):
    """Ajoute un téléphone à un client."""
    data = request.get_json()
    if not data:
        raise ValueError(_NO_DATA_ERROR)
    new_phone = util_add_phone(customer_id, data)
    if not new_phone:
        raise ValueError(_NO_CUSTOMER_ERROR)
    return jsonify(new_phone), 201


@bp_customer_data.patch("/<int:customer_id>/phone/<int:phone_id>")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def update_phone(customer_id: int, phone_id: int):
    """Met à jour un téléphone d'un client."""
    data = request.get_json()
    if not data:
        raise ValueError(_NO_DATA_ERROR)
    updated = util_update_phone(customer_id, phone_id, data)
    if not updated:
        raise ValueError("Téléphone ou client non trouvé.")
    return jsonify(updated)


@bp_customer_data.post("/<int:customer_id>/activate")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def activate(customer_id: int):
    """Active un client."""
    customer = util_get_customer(customer_id)
    if not customer:
        raise ValueError(_NO_CUSTOMER_ERROR)
    customer["is_active"] = True
    updated = update_customer_info(customer_id, {"is_active": True})
    return jsonify(updated)


@bp_customer_data.post("/<int:customer_id>/deactivate")
@permission_required([COMMERCIAL, COMPTA, DIRECTION], _and=False)
def deactivate(customer_id: int):
    """Désactive un client."""
    customer = util_get_customer(customer_id)
    if not customer:
        raise ValueError(_NO_CUSTOMER_ERROR)
    customer["is_active"] = False
    updated = update_customer_info(customer_id, {"is_active": False})
    return jsonify(updated)
