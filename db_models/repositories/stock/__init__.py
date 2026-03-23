"""Module stock — regroupe les dépôts liés au stock, commandes fournisseurs et Dilicom.

Utilisation :
    from db_models.repositories.stock import StockRepository, DilicomReferencialRepository
"""

from db_models.repositories.stock.inventory import InventoryRepository
from db_models.repositories.stock.orders import OrderRepository
from db_models.repositories.stock.dilicom import DilicomReferencialRepository


class StockRepository(OrderRepository, InventoryRepository):
    """Façade regroupant les fonctionnalités stock : commandes et inventaire.

    Hérite de OrderRepository et InventoryRepository pour maintenir la
    rétrocompatibilité avec le code existant qui utilise StockRepository.
    """

    pass    # pylint: disable=unnecessary-pass


__all__ = [
    "StockRepository",
    "InventoryRepository",
    "OrderRepository",
    "DilicomReferencialRepository",
]
