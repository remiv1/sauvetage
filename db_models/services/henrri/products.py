"""Module de gestion des produits pour les échanges avec Henrri."""

from typing import Any, Sequence
from henrri_connect.models import Item
from .base import HenrriService

class HenrriProductsService(HenrriService):
    """Service de gestion des produits pour Henrri."""

    def get_products(self) -> Sequence[Item]:
        """Récupère la liste des produits depuis Henrri."""

        response = self.client.items.list_items()
        return response.elements or []

    def create_product(self, product: Item) -> dict[str, Any]:
        """Crée un nouveau produit sur Henrri."""

        response = self.client.items.add(product)
        return response.model_dump()

    def create_products_batch(self, products: Sequence[Item]) -> Sequence[dict[str, Any]]:
        """Crée plusieurs produits en une seule requête sur Henrri."""

        responses = []
        for product in products:
            response = self.client.items.add(product)
            responses.append(response.model_dump())
        return responses

    def update_product(self, product_id: str, updated_product: Item) -> Item:
        """Met à jour un produit existant sur Henrri."""
        try:
            p_id = int(product_id)
        except ValueError as e:
            raise ValueError(
                f"Identifiant produit invalide: {product_id}. Il doit être une chaîne d'entier."
            ) from e
        response = self.client.items.modify(p_id, updated_product)
        return response
