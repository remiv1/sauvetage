"""Blueprint pour les fonctionnalités des fournisseurs pour la partie données."""

from flask import Blueprint, jsonify

bp_supplier_data = Blueprint("supplier_data", __name__, url_prefix="/supplier/data")

@bp_supplier_data.get("/get/suppliers")
def get_suppliers(data=None):   # pylint: disable=unused-argument
    """Retourne la liste des fournisseurs"""

    return jsonify({"suppliers": [
        {"id": 1, "name": "Fournisseur A"},
        {"id": 2, "name": "Fournisseur B"},
        {"id": 3, "name": "Fournisseur C"},
    ]})
