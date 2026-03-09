"""Utilitaires pour le module client --> Adresses uniquement."""

from typing import Dict, Any, List
from db_models.repositories.customers import (
    CustomersRepository,
    CustomerAddressesRepository,
)
from app_front.config.db_conf import get_main_session


def get_addresses(customer_id: int) -> List[Dict[str, Any]] | None:
    """
    Récupère les adresses d'un client à partir de son ID et retourne ses données sous
    forme de dictionnaire.
    Args:
        customer_id (int): L'ID du client à récupérer.
    Returns:
        List[Dict[str, Any]] | None: Les données des adresses du client ou None s'il n'existe pas.
    """
    repo = CustomersRepository(get_main_session())
    customer = repo.get_by_id(customer_id, complete=True)
    if not customer:
        return None
    return [addr.to_dict() for addr in customer.addresses]


def add_address(
    customer_id: int, address_data: Dict[str, Any]
) -> Dict[str, Any] | None:
    """
    Ajoute une adresse à un client.
    Args:
        customer_id (int): L'ID du client auquel ajouter l'adresse.
        address_data (Dict[str, Any]): Dictionnaire des champs de l'adresse à ajouter.
    Returns:
        Dict[str, Any] | None: Les données des adresses du client mis à jour ou None si introuvable.
    """
    repo = CustomerAddressesRepository(get_main_session())
    address_data["customer_id"] = customer_id
    address = repo.add_address(address_data)
    if not address:
        return None

    return address.to_dict()


def update_address(
    customer_id: int, address_id: int, address_data: Dict[str, Any]
) -> Dict[str, Any] | None:
    """
    Met à jour une adresse d'un client.
    Args:
        customer_id (int): L'ID du client auquel appartient l'adresse.
        address_id (int): L'ID de l'adresse à modifier.
        address_data (Dict[str, Any]): Dictionnaire des champs de l'adresse à modifier.
    Returns:
        Dict[str, Any] | None: Les données des adresses du client mis à jour ou None si introuvable.
    """
    repo = CustomerAddressesRepository(get_main_session())
    address = repo.update_address(customer_id, address_id, address_data)
    if not address:
        return None

    return {"addresses": [addr.to_dict() for addr in address.customer.addresses]}


def delete_address(address_id: int) -> bool:
    """
    Supprime une adresse d'un client en la marquant comme inactive.
    Args:
        address_id (int): L'ID de l'adresse à supprimer.
    Returns:
        bool: True si la suppression a réussi, False sinon.
    """
    repo = CustomerAddressesRepository(get_main_session())
    try:
        repo.delete_address(address_id)
    except ValueError:
        return False
    return True
