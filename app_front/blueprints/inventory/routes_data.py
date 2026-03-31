"""Blueprint API JSON pour le workflow d'inventaire.

Opérations légères (CRUD) : accès direct à la base de données via
les repositories (db_models) – produits, fournisseurs.
Opérations lourdes : déléguées au micro-service FastAPI (app-back)
via utils.py – parse, prepare, validate, commit, status.

Endpoints :
    POST /inventory/data/parse           → Normalise les EAN13          (→ FastAPI)
    POST /inventory/data/unknown         → Liste les produits inconnus  (→ FastAPI)
    POST /inventory/data/products        → Crée un produit              (DB direct)
    POST /inventory/data/prepare         → Calcule conciliation         (→ FastAPI)
    POST /inventory/data/validate        → Valide les écarts            (→ FastAPI)
    POST /inventory/data/commit          → Lance le commit asynchrone   (→ FastAPI)
    GET  /inventory/data/status          → État de la tâche             (→ FastAPI)
    GET  /inventory/data/suppliers/search → Recherche fournisseurs      (DB direct)
    POST /inventory/data/suppliers       → Crée un fournisseur          (DB direct)
"""

from flask import Blueprint, jsonify, request
from app_front.blueprints.inventory.utils import (
    parse_ean13,
    get_unknown_products,
    create_product,
    prepare_inventory,
    validate_inventory,
    commit_inventory,
    get_inventory_status,
    search_objects_info,
)
from app_front.utils.decorators import (
    permission_required, DIRECTION, LOGISTIQUE, SUPPORT, ADMIN
)

bp_inventory_data = Blueprint("inventory_data", __name__, url_prefix="/inventory/data")


@bp_inventory_data.get("/objects/info/search")
@permission_required([DIRECTION, LOGISTIQUE, SUPPORT, ADMIN], _and=False)
def api_search_objects_info():
    """Recherche d'informations sur les paramètres des objets."""
    quest = request.args.to_dict(flat=False)
    search_key = list(quest.keys())[0] if quest else None
    search_value = quest[search_key][0] if search_key else ""
    try:
        result = search_objects_info({search_key: search_value} if search_key else {})
    except (ValueError, RuntimeError) as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify({search_key: result})


@bp_inventory_data.post("/parse")
@permission_required([DIRECTION, LOGISTIQUE, SUPPORT, ADMIN], _and=False)
def api_parse():
    """Normalise et classifie les EAN13 saisis."""
    data = request.get_json(silent=True) or {}
    try:
        result = parse_ean13(
            raw=data.get("raw", ""),
            inventory_type=data.get("inventory_type", "complete"),
            category=data.get("category"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify(result)


@bp_inventory_data.post("/unknown")
@permission_required([DIRECTION, LOGISTIQUE, SUPPORT, ADMIN], _and=False)
def api_unknown():
    """Renvoie les EAN13 qui n'existent pas en base."""
    data = request.get_json(silent=True) or {}
    result = get_unknown_products(data.get("ean13", []))
    if "error" in result:
        return jsonify(result), 502
    return jsonify(result)


@bp_inventory_data.post("/products")
@permission_required([DIRECTION, LOGISTIQUE, SUPPORT, ADMIN], _and=False)
def api_create_product():
    """Crée un nouveau produit (accès DB direct)."""
    data = request.get_json(silent=True) or {}
    try:
        result = create_product(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result), 201


@bp_inventory_data.post("/prepare")
@permission_required([DIRECTION, LOGISTIQUE, SUPPORT, ADMIN], _and=False)
def api_prepare():
    """Calcule le stock théorique vs réel pour la conciliation."""
    data = request.get_json(silent=True) or {}
    result = prepare_inventory(
        data.get("ean13", []), data.get("inventory_type", "partial")
    )
    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 502
    return jsonify(result)


@bp_inventory_data.post("/validate")
@permission_required([DIRECTION, LOGISTIQUE, SUPPORT, ADMIN], _and=False)
def api_validate():
    """Valide les écarts et prépare les mouvements de stock."""
    data = request.get_json(silent=True) or {}
    lines = data.get("lines", [])
    inventory_type = data.get("inventory_type", "partial")
    result = validate_inventory(lines, inventory_type)
    if "error" in result:
        return jsonify(result), 502
    return jsonify(result)


@bp_inventory_data.post("/commit")
@permission_required([DIRECTION, LOGISTIQUE, SUPPORT, ADMIN], _and=False)
def api_commit():
    """Lance l'application asynchrone des mouvements."""
    data = request.get_json(silent=True) or {}
    result = commit_inventory(
        data.get("planned", []), data.get("inventory_type", "partial")
    )
    if "error" in result:
        return jsonify(result), 502
    return jsonify(result)


@bp_inventory_data.get("/status")
@permission_required([DIRECTION, LOGISTIQUE, SUPPORT, ADMIN], _and=False)
def api_status():
    """Retourne l'état de la tâche de commit en cours."""
    result = get_inventory_status()
    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 502
    return jsonify(result)
