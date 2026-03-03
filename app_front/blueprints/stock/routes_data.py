"""Blueprint API JSON pour le module stock.

Endpoints :
    POST /stock/data/council  → Met à jour le prix de revient d'un mouvement.
"""

from flask import Blueprint, jsonify, request
from app_front.blueprints.stock.utils import update_movement_price

bp_stock_data = Blueprint("stock_data", __name__, url_prefix="/stock/data")

@bp_stock_data.route("/council", methods=["POST"])
def api_update_price():
    """Met à jour le prix de revient d'un mouvement d'inventaire."""
    data = request.get_json(silent=True) or {}
    movement_id = data.get("movement_id")
    price = data.get("price")

    if movement_id is None or price is None:
        return jsonify({"error": "movement_id et price sont requis"}), 400

    try:
        price = float(price)
    except (TypeError, ValueError):
        return jsonify({"error": "price doit être un nombre"}), 400

    try:
        new_id = update_movement_price(int(movement_id), price)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({"ok": True, "new_movement_id": new_id}), 200
