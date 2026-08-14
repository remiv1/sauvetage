"""
Module de gestion des clients pour les échanges avec Henrri.

Ce module fournit la classe de service pour la gestion des clients dans l'intégration
avec Henrri.

Classes:
- ``HenrriCustomersService``: Service de gestion des clients pour Henrri.
"""

from typing import Any, Sequence
from henrri_connect.models import Customer, CustomerRequest
from .base import HenrriService

class HenrriCustomersService(HenrriService):
    """
    Service de gestion des clients pour Henrri.
    
    Arguments:
    - None

    Methodes:
    - get_customers(from_date, to_date, search): Récupère la liste des clients depuis Henrri.
    - create_customer(customer: Customer): Crée un nouveau client sur Henrri.
    - create_customers_batch(customers): Crée plusieurs clients en une seule requête sur Henrri.
    - update_customer(customer_id, updated_customer): Met à jour un client existant sur Henrri.
    """
    @staticmethod
    def _as_customer(customer: Customer | Any) -> Customer:
        """Convertit un objet local ou un modèle SDK Henri en Customer."""
        if isinstance(customer, Customer):
            return customer
        if hasattr(customer, "to_dict_henrri"):
            return Customer(**customer.to_dict_henrri())
        raise TypeError(
            "Le client fourni n'est ni un Customer Henri ni un objet local sérialisable."
        )

    def get_customers(self, from_date, to_date, search) -> Sequence[Customer]:
        """
        Récupère la liste des clients depuis Henrri.
        
        Arguments:
        - from_date: Date de commencement de la recherche.
        - to_date: Date de fin de la recherche.
        - search: Chaine de recherche.

        Returns:
        - List[Customer]: La liste des clients au format de la bibliothèque henrri-connect.
        """
        request: CustomerRequest = CustomerRequest(
            min_id=1,
            search=search,
            from_date=from_date,
            to_date=to_date
        )
        response = self.client.customers.list_customers(request=request)
        return response.elements or []

    def create_customer(self, customer: Customer | Any) -> int:
        """
        Crée un nouveau client sur Henrri.
        
        Arguments:
        - customer (Customer | Any): Le client local ou le modèle SDK Henri à créer.

        Returns:
        - int: L'identifiant du client créé au format de la bibliothèque henrri-connect.
        """
        remote_customer = self._as_customer(customer)
        response = self.client.customers.add(remote_customer)
        if response.id is None:
            raise ValueError("Le client n'a pas pu étre créé.")
        return response.id

    def create_customers_batch(self, customers: Sequence[Customer | Any]) -> Sequence[Customer]:
        """
        Crée plusieurs clients en une seule requête sur Henrri.
        
        Arguments:
        - customers (Sequence[Customer | Any]): La liste des clients à créer.

        Returns:
        - Sequence[Customer]: La liste des clients créés au format de la bibliothèque henrri-connect
        """

        responses = []
        for customer in customers:
            response = self.client.customers.add(self._as_customer(customer))
            responses.append(response)
        return responses

    def update_customer(self, customer_id: str, updated_customer: Customer | Any) -> Customer:
        """
        Met à jour un client existant sur Henrri.
        
        Arguments:
        - customer_id (str): L'identifiant du client à mettre à jour.
        - updated_customer (Customer | Any): Le client local ou le modèle SDK Henri mis à jour.

        Returns:
        - Customer: Le client mis à jour au format de la bibliothèque henrri-connect.
        """
        try:
            p_id = int(customer_id)
        except ValueError as e:
            raise ValueError(
                f"Identifiant client invalide: {customer_id}. Il doit être une chaîne d'entier."
            ) from e
        remote_customer = self._as_customer(updated_customer)
        response = self.client.customers.modify(p_id, remote_customer)
        return response
