"""Module de gestion des produits pour les échanges avec Henrri."""

from typing import Any
from .base import HenrriService

class HenrriProductsService(HenrriService):
    """Service de gestion des produits pour Henrri."""

    def get_products(self) -> list[dict[str, Any]]:
        """Récupère la liste des produits depuis Henrri."""
        response = self.client.items.list_items()
        return [item.model_dump() for item in response.elements or []]
