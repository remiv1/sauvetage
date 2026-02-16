"""Blueprint pour les fonctionnalités de l'inventaire"""

from flask import Blueprint

bp_inventory = Blueprint("inventory", __name__, url_prefix="/inventory")
