"""Blueprint pour les fonctionnalités des fournisseurs"""

from flask import Blueprint

bp_supplier = Blueprint("supplier", __name__, url_prefix="/supplier")
