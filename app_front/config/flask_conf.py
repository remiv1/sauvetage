"""
Configuration du projet Flask.
Ce module charge les variables d'environnement et définit les constantes de configuration
utilisées par l'application Flask.
"""

from typing import List
from os import getenv
from flask import Blueprint
from app_front.blueprints import (bp_customer, bp_dashboard, bp_inventory, bp_order,
                                  bp_stock, bp_supplier, bp_admin)
from logs.logger import MongoDBLogger

# Configuration
DEBUG = getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = getenv("LOG_LEVEL", "info").upper()
DATABASE_URL = getenv(
    "DATABASE_URL",
    "postgresql://app:pwd@db-main:5432/sauvetage_main"
)
MONGODB_URL = getenv(
    "MONGODB_URL",
    "mongodb://app:pwd@db-logs:27017/sauvetage_logs"
)
FLASK_SECRET_KEY = getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
BLUEPRINTS: List[Blueprint] = [
    bp_customer,
    bp_dashboard,
    bp_inventory,
    bp_order,
    bp_stock,
    bp_supplier,
    bp_admin
]
sauv_logger = MongoDBLogger()
