"""
Module pour les connections vers les opérateurs externes.
Ce module contient les classes de configuration pour :
    - Dilicom
    - WooCommerce
    - Henrri
"""

from .dilicom import DilicomConfig, load_dilicom_config
from .henrri import HenrriConfig, load_henrri_config
from .woocommerce import WooCommerceConfig, load_woocommerce_config
