"""Module stock — regroupe les dépôts liés au stock, commandes fournisseurs et Dilicom.

Utilisation :
    from db_models.repositories.stock import StockRepository, DilicomReferencialRepository
"""

from db_models.repositories.stocks.inventory import InventoryRepository
from db_models.repositories.stocks.orders import OrderRepository
from db_models.repositories.stocks.dilicom import DilicomReferencialRepository
from db_models.repositories.stocks.stock import StockRepository as BaseStockRepository


class StockRepository(OrderRepository, InventoryRepository, BaseStockRepository):
    """Façade regroupant les fonctionnalités stock : commandes, inventaire et réservation.

    Les méthodes de commande/inventaire restent prioritaires pour préserver le
    contrat métier attendu par les routes, tandis que le dépôt de base apporte les
    calculs spécifiques de stock et de prix d'inventaire.
    """
    pass    # pylint: disable=unnecessary-pass


__all__ = [
    "StockRepository",
    "InventoryRepository",
    "OrderRepository",
    "DilicomReferencialRepository",
]
