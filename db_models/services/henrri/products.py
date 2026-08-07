"""
Module de gestion des produits pour les échanges avec Henrri.

Ce module fournit la classe de service pour la gestion des produits dans l'intégration
avec Henrri.

Classes:
- ``HenrriProductsService``: Service de gestion des produits pour Henrri.
"""

from typing import Sequence
from henrri_connect.models import Item, ItemsQuery
from .base import HenrriService

class HenrriProductsService(HenrriService):
    """
    Service de gestion des produits pour Henrri.
    
    Arguments:
    - None

    Methodes:
    - get_products(from_date, to_date, search): Récupère la liste des produits depuis Henrri.
    - create_product(product): Crée un nouveau produit sur Henrri.
    - create_products_batch(products): Crée plusieurs produits en une seule requête sur Henrri.
    - update_product(product_id, updated_product): Met à jour un produit existant sur Henrri.
    """

    def get_products(self, from_date: str, to_date: str, search: str) -> Sequence[Item]:
        """
        Récupère la liste des produits depuis Henrri.
        
        Arguments:
        - from_date: Date de commencement de la recherche.
        - to_date: Date de fin de la recherche.
        - search: Chaine de recherche.

        Returns:
        - List[Item]: La liste des produits au format de la bibliothèque henrri-connect.
        """
        request: ItemsQuery = ItemsQuery(
            min_id=1,
            search=search,
            from_date=from_date,
            to_date=to_date
        )
        response = self.client.items.list_items(request=request)
        return response.elements or []

    def create_product(self, product: Item) -> int:
        """
        Crée un nouveau produit sur Henrri.
        
        Arguments:
        - product (Item): Le produit à créer.

        Returns:
        - int: L'identifiant du produit cré au format de la bibliothèque henrri-connect.
        """
        response = self.client.items.add(product)
        if response.id is None:
            raise ValueError("Le produit n'a pas pu étre créé.")
        return response.id

    def create_products_batch(self, products: Sequence[Item]) -> Sequence[Item]:
        """
        Crée plusieurs produits en une seule requête sur Henrri.
        
        Arguments:
        - products (Sequence[Item]): La liste des produits à créer.

        Returns:
        - Sequence[Item]: La liste des produits crées au format de la bibliothèque henrri-connect.
        """

        responses = []
        for product in products:
            response = self.client.items.add(product)
            responses.append(response)
        return responses

    def update_product(self, product_id: str, updated_product: Item) -> Item:
        """
        Met à jour un produit existant sur Henrri.
        
        Arguments:
        - product_id (str): L'identifiant du produit à mettre à jour.
        - updated_product (Item): Le produit mis à jour.

        Returns:
        - Item: Le produit mis à jour au format de la bibliothèque henrri-connect.
        """
        try:
            p_id = int(product_id)
        except ValueError as e:
            raise ValueError(
                f"Identifiant produit invalide: {product_id}. Il doit être une chaîne d'entier."
            ) from e
        response = self.client.items.modify(p_id, updated_product)
        return response
