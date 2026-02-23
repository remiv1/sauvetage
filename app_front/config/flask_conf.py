"""
Configuration du projet Flask.
Ce module charge les variables d'environnement et définit les constantes de configuration
utilisées par l'application Flask.
"""

from typing import List
from os import getenv
from flask import Blueprint
from app_front.blueprints import (bp_customer, bp_dashboard, bp_dashboard_data,
                                  bp_inventory, bp_order, bp_stock, bp_supplier,
                                  bp_admin, bp_user)
from logs.logger import get_logger

# Configuration
DEBUG = getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = getenv("LOG_LEVEL", "info").upper()

FLASK_SECRET_KEY = getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
BLUEPRINTS: List[Blueprint] = [
    bp_customer,
    bp_dashboard,
    bp_dashboard_data,
    bp_inventory,
    bp_order,
    bp_stock,
    bp_supplier,
    bp_admin,
    bp_user
]
sauv_logger = get_logger()
