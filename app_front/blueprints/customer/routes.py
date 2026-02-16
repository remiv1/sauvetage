"""Blueprint pour les fonctionnalités des clients"""

from flask import Blueprint

bp_customer = Blueprint("customer", __name__, url_prefix="/customer")
