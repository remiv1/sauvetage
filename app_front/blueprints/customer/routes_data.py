"""Blueprint pour les données client (API JSON).

Endpoints :
    - GET  /customer/data/<id>              : Récupérer les données complètes d'un client.
    - GET  /customer/data/<id>/addresses    : Récupérer les adresses d'un client.
    - POST /customer/data/<id>/address      : Ajouter une adresse.
    - DELETE /customer/data/<id>/address/<addr_id> : Supprimer une adresse.
    - GET  /customer/data/<id>/emails       : Récupérer les emails d'un client.
    - POST /customer/data/<id>/email        : Ajouter un email.
    - DELETE /customer/data/<id>/email/<email_id>  : Supprimer un email.
    - GET  /customer/data/<id>/phones       : Récupérer les téléphones d'un client.
    - POST /customer/data/<id>/phone        : Ajouter un téléphone.
    - DELETE /customer/data/<id>/phone/<phone_id>  : Supprimer un téléphone.
    - POST /customer/data/<id>/activate     : Activer un client.
    - POST /customer/data/<id>/deactivate   : Désactiver un client.
"""

from flask import Blueprint, jsonify, request

bp_customer_data = Blueprint("customer_data", __name__, url_prefix="/customer/data")

_NO_DATA_ERROR = "Aucune donnée reçue."


# ──────────────────────────────────────── Client complet ─────────────────────
@bp_customer_data.route("/<int:customer_id>", methods=["GET"])
def get_customer(customer_id: int):
    """Retourne les données complètes d'un client."""
    # TODO: Appeler le backend API
    return jsonify({
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
    })


# ──────────────────────────────────────── Adresses ───────────────────────────
@bp_customer_data.route("/<int:customer_id>/addresses", methods=["GET"])
def get_addresses(customer_id: int):
    """Retourne la liste des adresses d'un client."""
    # TODO: Appeler le backend API
    return jsonify([
        {
            "id": 1,
            "customer_id": customer_id,
            "address_name": "Domicile",
            "address_line1": "12 rue des Lilas",
            "address_line2": "Bâtiment A",
            "city": "Paris",
            "state": "Île-de-France",
            "postal_code": "75012",
            "country": "France",
            "is_billing": True,
            "is_shipping": True,
        },
        {
            "id": 2,
            "customer_id": customer_id,
            "address_name": "Bureau",
            "address_line1": "5 avenue de la République",
            "address_line2": "",
            "city": "Lyon",
            "state": "Auvergne-Rhône-Alpes",
            "postal_code": "69001",
            "country": "France",
            "is_billing": False,
            "is_shipping": True,
        }
    ])


@bp_customer_data.route("/<int:customer_id>/address", methods=["POST"])
def add_address(customer_id: int):
    """Ajoute une adresse à un client."""
    data = request.get_json()
    if not data:
        return jsonify({"error": _NO_DATA_ERROR}), 400

    # TODO: Envoyer au backend API, valider les champs
    new_address = {
        "id": 99,  # TODO: ID réel
        "customer_id": customer_id,
        "address_name": data.get("address_name", ""),
        "address_line1": data.get("address_line_1", ""),
        "address_line2": data.get("address_line_2", ""),
        "city": data.get("city", ""),
        "state": data.get("state", ""),
        "postal_code": data.get("postal_code", ""),
        "country": data.get("country", "France"),
        "is_billing": True,
        "is_shipping": False,
    }
    return jsonify(new_address), 201


@bp_customer_data.route("/<int:customer_id>/address/<int:address_id>", methods=["DELETE"])
def delete_address(customer_id: int, address_id: int):
    """Supprime une adresse d'un client."""
    # TODO: Appeler le backend API
    return jsonify({"message": f"Adresse {address_id} supprimée.", "success": True})


# ──────────────────────────────────────── Emails ─────────────────────────────
@bp_customer_data.route("/<int:customer_id>/emails", methods=["GET"])
def get_emails(customer_id: int):
    """Retourne la liste des emails d'un client."""
    # TODO: Appeler le backend API
    return jsonify([
        {
            "id": 1,
            "customer_id": customer_id,
            "email_name": "Personnel",
            "email": "jean.dupont@email.com",
            "is_active": True,
        },
        {
            "id": 2,
            "customer_id": customer_id,
            "email_name": "Professionnel",
            "email": "j.dupont@entreprise.fr",
            "is_active": True,
        }
    ])


@bp_customer_data.route("/<int:customer_id>/email", methods=["POST"])
def add_email(customer_id: int):
    """Ajoute un email à un client."""
    data = request.get_json()
    if not data:
        return jsonify({"error": _NO_DATA_ERROR}), 400

    # TODO: Envoyer au backend API
    new_email = {
        "id": 99,  # TODO: ID réel
        "customer_id": customer_id,
        "email_name": data.get("email_name", ""),
        "email": data.get("email", ""),
        "is_active": True,
    }
    return jsonify(new_email), 201


@bp_customer_data.route("/<int:customer_id>/email/<int:email_id>", methods=["DELETE"])
def delete_email(customer_id: int, email_id: int):
    """Supprime un email d'un client."""
    # TODO: Appeler le backend API
    return jsonify({"message": f"Email {email_id} supprimé.", "success": True})


# ──────────────────────────────────────── Téléphones ─────────────────────────
@bp_customer_data.route("/<int:customer_id>/phones", methods=["GET"])
def get_phones(customer_id: int):
    """Retourne la liste des téléphones d'un client."""
    # TODO: Appeler le backend API
    return jsonify([
        {
            "id": 1,
            "customer_id": customer_id,
            "phone_name": "Mobile",
            "phone_number": "06 12 34 56 78",
            "is_active": True,
        }
    ])


@bp_customer_data.route("/<int:customer_id>/phone", methods=["POST"])
def add_phone(customer_id: int):
    """Ajoute un téléphone à un client."""
    data = request.get_json()
    if not data:
        return jsonify({"error": _NO_DATA_ERROR}), 400

    # TODO: Envoyer au backend API
    new_phone = {
        "id": 99,  # TODO: ID réel
        "customer_id": customer_id,
        "phone_name": data.get("phone_name", ""),
        "phone_number": data.get("phone_number", ""),
        "is_active": True,
    }
    return jsonify(new_phone), 201


@bp_customer_data.route("/<int:customer_id>/phone/<int:phone_id>", methods=["DELETE"])
def delete_phone(customer_id: int, phone_id: int):
    """Supprime un téléphone d'un client."""
    # TODO: Appeler le backend API
    return jsonify({"message": f"Téléphone {phone_id} supprimé.", "success": True})


# ──────────────────────────────────────── Activation ─────────────────────────
@bp_customer_data.route("/<int:customer_id>/activate", methods=["POST"])
def activate(customer_id: int):
    """Active un client."""
    # TODO: Appeler le backend API
    return jsonify({"message": "Client activé.", "is_active": True, "success": True})


@bp_customer_data.route("/<int:customer_id>/deactivate", methods=["POST"])
def deactivate(customer_id: int):
    """Désactive un client."""
    # TODO: Appeler le backend API
    return jsonify({"message": "Client désactivé.", "is_active": False, "success": True})
