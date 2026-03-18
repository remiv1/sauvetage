"""Blueprint pour les fonctionnalités des fournisseurs pour la partie données."""

from flask import Blueprint, jsonify, request
from app_front.blueprints.supplier.utils import search_suppliers, create_supplier

bp_supplier_data = Blueprint("supplier_data", __name__, url_prefix="/supplier/data")


@bp_supplier_data.route("/search", methods=["GET"])
def api_search_suppliers():
    """Recherche de fournisseurs par nom (autocomplete, accès DB direct)."""
    q = request.args.get("q", "")
    type_of_data = request.args.get("type_of_data", "name")
    try:
        result = search_suppliers(q, data_returned=type_of_data)
    except (ValueError, RuntimeError) as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify(result)


@bp_supplier_data.route("/suppliers", methods=["POST"])
def api_create_supplier():
    """Crée un nouveau fournisseur (création rapide, accès DB direct)."""
    data = request.get_json(silent=True) or {}
    try:
        result = create_supplier(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result), 201
