"""Blueprint pour les fonctionnalités de gestion des stocks"""

from flask import Blueprint, redirect, url_for, flash
from app_front.utils.pages import render_page
from app_front.blueprints.stock.utils import (
    is_zero_price_items,
    get_zero_price_items,
    get_supplier_orders,
    cancel_supplier_order,
    create_order_in_db,
)
from app_front.blueprints.stock.forms import OrderInCreateForm

bp_stock = Blueprint("stock", __name__, url_prefix="/stock")


@bp_stock.route("/", methods=["GET"])
def index():
    """Page d'accueil du module stocks"""
    has_zero_price_items = is_zero_price_items()
    return render_page("stock_index", has_zero_price_items=has_zero_price_items)


@bp_stock.route("/council", methods=["GET", "POST"])
def council():
    """Page de gestion de réconciliation des prix de stocks"""
    items_to_council = get_zero_price_items()
    # TODO: implémenter le formulaire de mise à jour des prix et le traitement associé
    return render_page("stock_council", items_to_council=items_to_council)


@bp_stock.route("/orders", methods=["GET", "POST"])
def orders():
    """Page de gestion des commandes fournisseurs (entrantes)"""
    orders_list = get_supplier_orders()
    return render_page("stock_order", orders=orders_list)


@bp_stock.route("/orders/new", methods=["GET", "POST"])
def create_order():
    """Création d'une nouvelle commande fournisseur"""
    # TODO: implémenter le formulaire de création de commande et le traitement associé
    return render_page("stock_order")


@bp_stock.route("/returns/new", methods=["GET", "POST"])
def create_return():
    """Création d'un retour fournisseur"""
    # TODO: implémenter le formulaire de retour
    return render_page("stock_order")


@bp_stock.route("/reservations", methods=["GET"])
def reservations():
    """Page de gestion des réservations de stocks"""
    return render_page("stock_reservations")


@bp_stock.route("/search", methods=["GET"])
def search():
    """Page de recherche de stocks"""
    return render_page("stock_search")
