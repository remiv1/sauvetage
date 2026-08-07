"""Module regroupant les modèles de données pour l'intégration avec WooCommerce.
Ce module contient les modèles de données utilisés pour interagir avec l'API WooCommerce,
notamment pour la gestion des clients et des commandes.
Les modèles sont organisés en sous-modules pour chaque type de ressource (client, commande, etc.).
"""

from .woo import WCCustomerGet, WCCustomerPut, WCOrderGet, WCOrderPut

__all__ = [
    "WCCustomerGet",
    "WCCustomerPut",
    "WCOrderGet",
    "WCOrderPut",
]
