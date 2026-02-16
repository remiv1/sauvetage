"""Blueprint pour les fonctionnalités de gestion des stocks"""

from flask import Blueprint

bp_stock = Blueprint("stock", __name__, url_prefix="/stock")
