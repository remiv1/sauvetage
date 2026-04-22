"""
Configuration du projet Flask.
Ce module charge les variables d'environnement et définit les constantes de configuration
utilisées par l'application Flask.
"""

from typing import List
from os import getenv
from flask import Blueprint
from app_front.blueprints import (
    bp_customer,
    bp_customer_data,
    bp_dashboard,
    bp_dashboard_data,
    bp_inventory,
    bp_inventory_data,
    bp_inventory_htmx,
    bp_order,
    bp_order_htmx_list,
    bp_order_htmx_create,
    bp_stock,
    bp_stock_data,
    bp_stock_htmx_council,
    bp_stock_htmx_orders,
    bp_stock_htmx_reservations,
    bp_stock_htmx_return,
    bp_stock_htmx_search,
    bp_supplier,
    bp_supplier_htmx,
    bp_supplier_htmx_list,
    bp_admin,
    bp_admin_vat,
    bp_admin_users,
    bp_admin_logs,
    bp_user,
)
from logs.logger import MongoForwardHandler, logging, LOG_LEVEL, get_logger

# Configuration
DEBUG = getenv("DEBUG", "false").lower() == "true"

FLASK_SECRET_KEY = getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
BLUEPRINTS: List[Blueprint] = [
    bp_customer,
    bp_customer_data,
    bp_dashboard,
    bp_dashboard_data,
    bp_inventory,
    bp_inventory_data,
    bp_inventory_htmx,
    bp_order,
    bp_order_htmx_list,
    bp_order_htmx_create,
    bp_stock,
    bp_stock_data,
    bp_stock_htmx_council,
    bp_stock_htmx_orders,
    bp_stock_htmx_reservations,
    bp_stock_htmx_return,
    bp_stock_htmx_search,
    bp_supplier,
    bp_supplier_htmx,
    bp_supplier_htmx_list,
    bp_admin,
    bp_admin_vat,
    bp_admin_users,
    bp_admin_logs,
    bp_user,
]
def setup_logging():
    """Configure le logging pour l'application Flask."""
    mongo_logger = get_logger()
    mongo_handler = MongoForwardHandler(mongo_logger)
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    root_logger.addHandler(mongo_handler)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("pymongo.topology").setLevel(logging.WARNING)
    logging.getLogger("pymongo.connection").setLevel(logging.WARNING)
    logging.getLogger("pymongo.command").setLevel(logging.WARNING)
