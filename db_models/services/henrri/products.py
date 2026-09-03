"""
Module de gestion des produits pour les échanges avec Henrri.

Ce module fournit la classe de service pour la gestion des produits dans l'intégration
avec Henrri.

Classes:
- ``HenrriProductsService``: Service de gestion des produits pour Henrri.
"""

import json
import logging
from typing import Any, Sequence

from henrri_connect.models import Item, ItemsQuery

from .base import HenrriService

logger = logging.getLogger(__name__)

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
    @staticmethod
    def _as_item(product: Item | Any) -> Item:
        """Convertit un objet local ou un modèle SDK Henri en Item."""
        if isinstance(product, Item):
            return product
        if hasattr(product, "to_dict_henrri"):
            return Item(**product.to_dict_henrri())
        raise TypeError("Le produit fourni n'est ni un Item Henri ni un objet local sérialisable.")

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

    @staticmethod
    def _serialize_payload(item: Item) -> str:
        """Convertit le payload produit en JSON lisible pour le log de debug."""
        try:
            payload = item.model_dump(exclude_none=True, by_alias=True)
        except AttributeError:
            payload = item.dict(exclude_none=True, by_alias=True)
        return json.dumps(payload, default=str, ensure_ascii=False)

    def create_product(self, product: Item | Any) -> int:
        """
        Crée un nouveau produit sur Henrri.
        
        Arguments:
        - product (Item | Any): Le produit local ou le modèle SDK Henri à créer.

        Returns:
        - int: L'identifiant du produit créé au format de la bibliothèque henrri-connect.
        """
        item = self._as_item(product)
        logger.debug("Henri product payload create: %s", self._serialize_payload(item))
        response = self.client.items.add(item)
        if response.id is None:
            raise ValueError("Le produit n'a pas pu étre créé.")
        return response.id

    def upsert_product(
        self,
        product: Item | Any,
        henrri_id: str | int | None = None,
    ) -> Item:
        """Crée (POST) ou met à jour (PUT) un produit sur Henrri.

        Arguments:
            product: Le produit local ou le modèle SDK Henrri.
            henrri_id: L'identifiant Henrri connu, ou None pour une création.

        Returns:
            Item: Le produit créé ou mis à jour, tel que retourné par Henrri.

        Raises:
            ValueError: Si Henrri ne retourne pas d'identifiant.
        """
        remote_product = self._as_item(product)
        action = "create" if henrri_id is None else "update"
        logger.warning(
            "Henri product payload %s: %s",
            action,
            self._serialize_payload(remote_product),
        )
        if henrri_id is None:
            response = self.client.items.add(remote_product)
        else:
            response = self.client.items.modify(int(henrri_id), remote_product)
        if response.id is None:
            raise ValueError("Le produit Henrri n'a pas d'identifiant après synchronisation.")
        return response

    def create_products_batch(self, products: Sequence[Item | Any]) -> Sequence[Item]:
        """
        Crée plusieurs produits en une seule requête sur Henrri.
        
        Arguments:
        - products (Sequence[Item | Any]): La liste des produits à créer.

        Returns:
        - Sequence[Item]: La liste des produits créés au format de la bibliothèque henrri-connect.
        """

        responses = []
        for product in products:
            item = self._as_item(product)
            logger.warning("Henri product payload batch create: %s", self._serialize_payload(item))
            response = self.client.items.add(item)
            responses.append(response)
        return responses

    def update_product(self, product_id: str, updated_product: Item | Any) -> Item:
        """
        Met à jour un produit existant sur Henrri.
        
        Arguments:
        - product_id (str): L'identifiant du produit à mettre à jour.
        - updated_product (Item | Any): Le produit local ou le modèle SDK Henri mis à jour.

        Returns:
        - Item: Le produit mis à jour au format de la bibliothèque henrri-connect.
        """
        try:
            p_id = int(product_id)
        except ValueError as e:
            raise ValueError(
                f"Identifiant produit invalide: {product_id}. Il doit être une chaîne d'entier."
            ) from e
        remote_product = self._as_item(updated_product)
        logger.warning("Henri product payload update: %s", self._serialize_payload(remote_product))
        response = self.client.items.modify(p_id, remote_product)
        return response
