"""Blueprint pour les fonctionnalités des commandes"""

from flask import Blueprint

bp_order = Blueprint("order", __name__, url_prefix="/order")
