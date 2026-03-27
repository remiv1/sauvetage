"""Blueprint HTMX pour la conciliation des articles à prix zéro."""

from flask import Blueprint, render_template, request

from app_front.blueprints.stock.utils import (
    get_zero_price_items,
    update_movement_price,
)

bp_stock_htmx_council = Blueprint(
    "stock_htmx_council",
    __name__,
    url_prefix="/stock/htmx/council",
)

SECTION_HOME = "htmx_templates/stock/council/sections/home.html"
FRAGMENT_ROW = "htmx_templates/stock/council/fragments/row.html"
FRAGMENT_SUCCESS = "htmx_templates/stock/council/fragments/success_row.html"
FRAGMENT_ERROR = "htmx_templates/stock/council/fragments/error.html"


@bp_stock_htmx_council.get("/table")
def council_table():
    """Retourne le tableau des articles à concilier (HTMX)."""
    items = get_zero_price_items()
    return render_template(SECTION_HOME, items_to_council=items)


@bp_stock_htmx_council.post("/validate/<int:movement_id>")
def validate_price(movement_id: int):
    """Valide le prix d'un article et duplique le mouvement d'inventaire (HTMX)."""
    raw_price = request.form.get("price", "").strip()

    if not raw_price:
        return render_template(FRAGMENT_ERROR, message="Veuillez saisir un prix.")

    try:
        price = float(raw_price)
    except ValueError:
        return render_template(FRAGMENT_ERROR, message="Le prix saisi n'est pas valide.")

    if price < 0:
        return render_template(FRAGMENT_ERROR, message="Le prix ne peut pas être négatif.")

    try:
        update_movement_price(movement_id, price)
    except ValueError as e:
        return render_template(FRAGMENT_ERROR, message=str(e))

    return render_template(FRAGMENT_SUCCESS, price=price)
